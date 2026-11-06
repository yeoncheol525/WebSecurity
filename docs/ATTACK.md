# 공격·방어 실험 절차

격리망·합성 데이터 전용. 대상은 `http://192.168.67.20:18080`(실제 Ubuntu Host-only 주소로 바꾼다).
각 조건은 `bash scripts/setup-ubuntu.sh --experiment <조건>`으로 전환하고, 전환 뒤 `/health`로 적용 조건을 확인한다.
검색은 `id, name, description, price` 4열을 반환하므로 UNION 입력도 4열로 맞춘다.

## E1 — 기준선 (바인딩 OFF · 권한 과다)

- 구동: `--experiment E1` (`/health/catalog` → `query_mode=interpolated`, `catalog_reader_wide`)
- 입력(상품 검색창):
  ```
  x%' UNION ALL SELECT id,email,name,0 FROM private.customers -- 
  ```
- Burp: HTTP history의 `/products` 요청 → Send to Repeater → Send.
- 측정: 200 OK, 응답 `products[]`에 합성 이메일(`customerNNN@example.invalid`)과 고유 `customer_id` 포함.
- 판정: **공격 성공**. 비로그인 응답에 합성 고객정보가 1건 이상 → 유출 고유 `customer_id` 수 기록(최대 100).
- 확장: 테이블을 `private.orders`, `private.payment_meta`로 바꾸면 주문·결제도 유출된다.
  ```
  x%' UNION ALL SELECT id,customer_id::text,total_amount::text,0 FROM private.orders -- 
  x%' UNION ALL SELECT id,order_id::text,method,0 FROM private.payment_meta -- 
  ```

## E2 — 바인딩 (ON · 권한 과다)

- 구동: `--experiment E2`
- 입력: E1과 동일.
- 측정: 200 OK, `"products": []`(0건).
- 판정: **웹 방어(D1) 성공**. 입력이 검색어 문자열로 바인딩돼 구문 변조가 차단됨. 노출 0.

## E3 — 최소권한 (OFF · 제한)

- 구동: `--experiment E3` (`/health/catalog` → `interpolated`, `catalog_reader`)
- 입력: E1과 동일.
- 측정: HTTP 503. 서버 로그에서 권한 거부 확인:
  ```sh
  sudo docker compose logs catalog-service | grep 42501
  ```
  `SQLSTATE 42501 permission denied for schema private`가 찍힌다.
- 판정: **DB 방어(D2) 성공**. SQLi 구문 변조는 성립했지만 `catalog_reader`에 `private` 권한이 없어 민감 테이블 접근이 거부됨. 노출 0.
- 참고: `'; DROP TABLE ...; --` 같은 스택 쿼리는 이 환경에서 실행되지 않으며(단일 문장만 허용), 권한도 없어 추가로 차단된다.

## E4 — 이중 (ON · 제한)

- 구동: `--experiment E4`
- 입력: E1과 동일.
- 측정: 200 OK, `"products": []`, 오류 없음.
- 판정: **이중 방어(D1+D2)**. 웹에서 1차(바인딩), DB에서 2차(권한) 차단. 노출 0.

## A — 로그인 SQL Injection (인증 우회)

- 구동: `--experiment A` (`/health/orders` → `login_sql_mode=interpolated`)
- 입력: `POST /login`(JSON). Burp Repeater 또는 curl.
  ```
  {"username":"' OR '1'='1' -- ","password":"anything"}
  ```
- 측정: 200 + `Set-Cookie: minishop_session` + `csrf_token`. 받은 쿠키로 `GET /session`·`GET /orders`가 200이면 인증 우회 성립.
- 판정: **인증 우회(CWE-89)**. 비밀번호 없이 세션 발급. 기본(`login_sql_mode=bound`)에서 같은 입력은 401.

## C2 — IDOR (객체 인가 누락)

- 구동: `--experiment C2` (`/health/orders` → `ownership_enforced=false`)
- 준비: user1로 정상 로그인(계정은 `scripts/demo_credentials.py`).
- 입력(user1 세션):
  ```
  GET /orders/2002      # user2 주문
  GET /orders           # 전체 주문
  ```
- 측정: C2 → `GET /orders/2002`가 200 + user2 주문 본문, `GET /orders`가 300건. E4/기본 → 404 / 본인 3건.
- 판정: **인가 결함(CWE-639/862)**. 쿼리는 모두 바인딩된 상태이므로 SQLi가 아닌 접근권한 문제. 로그에 `binding=parameters`, `authorization_result=ownership_disabled`로 기록됨.

## 증거 기록 (test_results.csv)

| 열 | 설명 |
|---|---|
| Sequence_ID | 실험 일련번호 |
| Experiment_Condition | E1 / E2 / E3 / E4 / A / C2 |
| Input_ID | 입력 식별자(P_CUSTOMER, A-login, C2-2002 등) |
| X_Request_ID | 응답 헤더 `X-Request-ID`(서버 로그 대조용) |
| HTTP_Status | 200 / 401 / 404 / 503 |
| Exposed_Customer_Count | 유출 고유 `customer_id` 수(E1은 1 이상, 방어 조건은 0) |
| DB_Error_Code | E3의 SQLSTATE(42501) |
| Normal_Function_OK | 정상 검색·로그인·본인 주문 유지 여부 |

반복: 입력 3종 × 10회 × 4조건 = 120 시퀀스. 응답과 같은 `X-Request-ID`의 서버 로그를 함께 보관하고, 공유 시 비밀번호·쿠키·토큰은 제거한다.
