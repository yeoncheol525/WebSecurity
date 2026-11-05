# MiniShop · 웹 보안 실험환경

Kali는 실험 클라이언트, Ubuntu Server는 웹서버입니다. Ubuntu 안의 Docker Compose가
Nginx·상품 서비스·인증/주문 서비스·PostgreSQL을 실행합니다. 기존 MiniShop 화면을 유지하면서
SQLite 단일 앱을 PostgreSQL과 서비스별 DB 권한 구조로 개편했습니다.

연구 질문은 **“SQL Injection이 남아 있어도 DB 최소 권한으로 고객·거래정보 유출을 제한할 수 있는가?”**입니다.
아래에 설치부터 Kali 공격 절차, 방어별 비교 방법, 측정식과 증거 형식을 정리했습니다.

```text
Windows / VMware
  Kali VM ── Host-only ── Ubuntu Server VM
  브라우저·Burp            Docker: Nginx → Catalog / Orders → PostgreSQL
```

## 바로가기

- [처음 설치](#처음-실행) · [기존 저장소 업데이트](#기존-파일을-받았거나-이미-실행-중이라면)
- [네 가지 실험 조건과 구현 상태](#실험-조건과-현재-구현-상태)
- [Kali 공격 절차: Burp·SQLi·로그인·IDOR](#kali에서-공격을-진행하는-순서)
- [방어 효과: 노출량·성공률·정상 기능·지연·탐지](#방어를-적용했을-때-무엇을-측정할까)
- [증거 수집·CSV·발표 결과표·정상 복구](#실험-증거와-결과표를-남기는-방법)
- [운영 명령](#운영-명령) · [소스 구조와 관련 문서](#구조와-검증)

## 처음 실행

먼저 **Ubuntu Server VM과 Kali VM**, 두 VM의 Host-only NIC를 준비합니다.
[팀원 설치 순서](docs/TEAM_SETUP.md)에 VMware 설정부터 적어 두었습니다.
실제 검증 기준은 Ubuntu 24.04 LTS amd64이며 설치 스크립트는 Ubuntu 26.04 LTS도 허용합니다.

**Ubuntu VM 터미널**에서 저장소를 받습니다. Git이 없는 새 Ubuntu에서는 앞의 두 줄부터 실행합니다.

```sh
sudo apt-get update
sudo apt-get install -y git
git clone https://github.com/yeoncheol525/WebSecurity.git minishop
cd minishop
bash scripts/setup-ubuntu.sh
```

비공개 저장소이므로 저장소 접근 권한과 GitHub 인증이 필요합니다.
이미 파일을 받았다면 `docker-compose.yml`이 있는 폴더에서 마지막 명령만 실행합니다.
설치 중 묻는 비밀번호는 **Ubuntu 사용자 sudo 비밀번호**입니다.

이 명령은 다음을 순서대로 처리합니다.

1. 빠진 Git·Python·Docker Engine·Compose·Buildx 설치, Docker 시작.
2. `.env`와 PC별 무작위 DB/테스트 웹 계정 비밀번호 생성.
3. 기본 인터넷 경로가 없는 전용 사설 NIC의 IP 선택. 후보가 없으면 `127.0.0.1` 사용.
4. 이미지 빌드, PostgreSQL 초기화, 합성 고객 100·주문 300·결제 메타 300건 생성.
5. 서비스 시작 후 HTTP·권한·세션·재시작·로그 검증. 결과는 `results/`에 저장.

NAT NIC만 있는 경우에는 Host-only NIC를 추가한 뒤 아래처럼 다시 실행합니다.
사설 NIC 후보가 여러 개일 때도 사용할 주소를 직접 지정합니다.

```sh
bash scripts/setup-ubuntu.sh --bind 192.168.67.20
```

IP는 예시입니다. 실제 접속 주소는 스크립트의 `Safe lab URL` 출력으로 확인합니다.
현재 구성의 홈페이지는 **http://192.168.67.20:18080/** 이며 Kali Firefox에서 접속합니다.

```sh
python3 scripts/demo_credentials.py  # 이 Ubuntu에 생성된 user1/user2 웹 비밀번호 확인
```

로그인 비밀번호는 환경마다 다릅니다. 홈페이지나 Git에는 표시하지 않습니다.
Ubuntu에는 앱용 pip 패키지나 PostgreSQL을 직접 설치하지 않습니다. 이들은 컨테이너 안에 설치됩니다.
호스트의 Git·Python은 소스 관리와 설치/검증 스크립트 실행에 사용합니다.

## 기존 파일을 받았거나 이미 실행 중이라면

```sh
git pull --ff-only
bash scripts/setup-ubuntu.sh
```

같은 명령을 다시 실행해도 현재 PostgreSQL `.env`와 DB 볼륨을 유지합니다.
SQLite 버전의 `.env`는 `.env.sqlite-backup`으로 옮기고 새 환경 설정을 만듭니다.
`instance/`의 기존 SQLite 파일은 유지하며 PostgreSQL로 자동 변환하지 않습니다.
기존 버전은 [`archive/sqlite-v1`](https://github.com/yeoncheol525/WebSecurity/tree/archive/sqlite-v1)에 보존합니다.
기존 5000번 서비스와 새 18080번 서비스는 서로 다른 Docker 프로젝트를 사용합니다.
자세한 변경점은 [업데이트 안내](docs/MIGRATION.md)에 있습니다.

## 화면과 API

| 기능 | 브라우저 화면 | JSON API |
|---|---|---|
| 홈 / 상품 검색 | `/`, `/shop?q=...` | `GET /products?q=...`, `GET /products/{id}` |
| 로그인 / 현재 사용자 | `/login` | `POST /login`, `GET /session` |
| 본인 주문 | `/account/orders`, `/account/orders/{id}` | `GET /orders`, `GET /orders/{id}` |
| 로그아웃 | 화면 상단 버튼 | `POST /logout` + `X-CSRF-Token` |
| 상태 | — | `GET /health/catalog`, `GET /health/orders` |

상품·주문 API는 기본 JSON을 유지하며 기존 브라우저 `/products`·`/orders` 북마크는 화면으로 연결합니다.
user1 주문은 1001~1003, user2 주문은 2001~2003입니다. 타인 주문과 미존재 주문은 같은 404를 반환합니다.
세션 인증 쿠키는 HttpOnly·SameSite=Strict, 로그아웃 시 서버 세션도 폐기합니다.
CSRF 쿠키만 같은 출처 JavaScript에서 읽을 수 있습니다.

## 실험 조건과 현재 구현 상태

| 조건 | 기획서 표기 | 쿼리 바인딩 D1 | Catalog DB 권한 D2 | 현재 실행 가능 여부 |
|---|---|---|---|---|
| E1 | S00 · 기준선 | OFF | 과다: `catalog_reader_wide` | 취약 쿼리 미구현. 아직 실행 불가 |
| E2 | S10 · 바인딩만 | ON | 과다: `catalog_reader_wide` | 수동 역할 전환 준비됨. 기본 실행 상태는 아님 |
| E3 | S01 · 최소 권한만 | OFF | 제한: `catalog_reader` | 취약 쿼리 미구현. 아직 실행 불가 |
| E4 | S11 · 병행 적용 | ON | 제한: `catalog_reader` | 현재 기본 상태. 정상 서비스·권한·인가 검증 완료 |

현재 `SQL_QUERY_MODE`는 `bound`만 허용합니다. `.env`에 OFF라고 쓰는 것으로 E1/E3가 만들어지지 않습니다.
주문 소유자 검증 D3도 항상 켜져 있습니다. 감사 로그 D4는 구현했지만 자동 탐지 규칙·경고 수집기는 없습니다.
따라서 **현재 바로 할 수 있는 것은 E4에 대한 공격 입력 재전송·방어 검증과 IDOR 차단 확인**입니다.
E1~E4의 120회 비교와 탐지율은 후속 구현·실측 항목이며 아래 설명은 그 실험의 실행 계약입니다.

검증 프로그램의 **32/32 통과**는 환경·DB 권한·세션·화면 검사 결과입니다.
공격 120회 성공률, 방어율, 응답 p95 또는 탐지율을 측정한 숫자가 아닙니다.

## Kali에서 공격을 진행하는 순서

### 1. 대상과 기준선을 확인한다

대상은 팀이 만든 Host-only Ubuntu의 MiniShop과 합성 데이터입니다.
이 README의 실제 예시는 Kali `192.168.67.10` → Ubuntu `192.168.67.20:18080`을 사용합니다.
각 PC의 VMnet 주소가 다르면 아래 `LAB_BASE`만 해당 Ubuntu 주소로 바꿉니다.

Ubuntu에서 먼저 서버와 사용 중인 코드를 확인합니다.

```sh
cd ~/minishop
git rev-parse HEAD
sudo docker compose -f docker-compose.yml ps
python3 scripts/demo_credentials.py
```

Kali 터미널에서 다음을 실행합니다. 결과 디렉터리는 Kali 로컬 전용입니다.

```sh
umask 077
LAB_BASE='http://192.168.67.20:18080'
LAB_RUN="$HOME/minishop-results/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$LAB_RUN"
ip route
curl -sS -H 'Accept: application/json' "$LAB_BASE/health/catalog"
curl -sS -H 'Accept: application/json' "$LAB_BASE/health/orders"
curl -sS --get --data-urlencode 'q=Notebook' "$LAB_BASE/products"
curl -sS --get --data-urlencode "q=O'Reilly" "$LAB_BASE/products"
```

E4의 기대값은 Catalog 역할 `catalog_reader`, `query_mode=bound`, Orders의 `ownership_enforced=true`입니다.
두 검색은 각각 상품 1개가 나와야 합니다. `O'Reilly`는 정상 검색어이므로 SQLi로 분류하지 않습니다.
데이터 기준은 공개 상품 12개, 비공개 상품 1개, 합성 고객 100명·주문 300건·결제 메타 300건입니다.
공격 입력을 보낼 때는 로그인 쿠키를 사용하지 않아 비로그인 검색 경로의 피해를 확인합니다.

### 2. Burp Repeater로 요청 하나를 관찰한다

1. Kali에서 Burp Suite를 실행하고 Proxy의 **Open browser**로 MiniShop `/shop`을 엽니다.
2. `Notebook`을 검색한 뒤 HTTP history에서 **`GET /products?q=...`** 요청을 찾아 Repeater로 보냅니다.
   `/shop`은 HTML 화면이고 실제 검색 결과를 가져오는 API가 `/products`입니다.
3. Repeater에서 `Accept: application/json`을 사용하고 `Cookie`·`Authorization` 헤더는 제거합니다.
4. 정상 검색, 작은따옴표 입력, 아래 SQLi 확인 입력을 순서대로 보냅니다.
   쿼리 파라미터는 URL 인코딩하며, curl에서는 `--data-urlencode`를 사용합니다.
5. 상태코드뿐 아니라 JSON 본문, 상품 행 수, 비공개 필드 포함 여부와 응답의 `X-Request-ID`를 저장합니다.

작은따옴표에서 오류가 나거나 결과가 달라지는 현상은 조사 단서입니다.
고객정보 유출의 성공 증거는 실제 비로그인 HTTP 응답에 나타난 합성 비공개 데이터입니다.
일반 테스트 절차는 [OWASP WSTG의 SQLi 시험](https://wstg.owasp.org/v4.2/4-Web_Application_Security_Testing/07-Input_Validation_Testing/05-Testing_for_SQL_Injection/)을 참고합니다.

### 3. SQL 구문 변조가 가능한지 먼저 확인한다

아래 입력은 이 실습의 4열 검색 결과 `id, name, description, price`에 맞춘 확인용입니다.
현재 API의 검색어 길이 제한인 100자 안에서 사용합니다.

```sh
P_MARKER="x%' UNION ALL SELECT 900001,'LAB-SQLI-PROBE','probe',0 -- "
curl -sS --connect-timeout 3 --max-time 10 --get \
  -H 'Accept: application/json' --data-urlencode "q=$P_MARKER" \
  -D "$LAB_RUN/probe.headers" -o "$LAB_RUN/probe.json" \
  -w 'status=%{http_code} total_s=%{time_total}\n' "$LAB_BASE/products"
cat "$LAB_RUN/probe.json"
```

| 조건 | 준비 확인에서 기대하는 관측 |
|---|---|
| E1/E3 · 향후 취약 모드 | `id=900001`, `name=LAB-SQLI-PROBE`가 결과에 포함돼 SQL 구조 변조를 입증 |
| E2/E4 · 바인딩 모드 | 전체 입력을 검색 문자열로 처리. 현재 합성 시드에서는 `products: []`, 마커 없음 |

마커는 공개 데이터만으로 SQL 구조 변조를 확인하는 준비 요청이며 고객정보 유출 성공으로 세지 않습니다.
E3에서 이 마커조차 재현되지 않았다면 “SQLi가 남았지만 최소 권한이 유출을 막았다”고 결론 내릴 수 없습니다.
E1/E3 설명은 취약 모드를 별도로 구현한 뒤 적용합니다. 현재 E4에서는 마커가 나오지 않는 것이 정상입니다.

### 4. 고객·주문·결제 메타 노출을 확인한다

다음 입력들은 이 저장소의 합성 테이블과 응답 구조에 맞춘 실습용 요청입니다.
현재 E4에서도 그대로 보내 방어 동작을 확인할 수 있으며, 시드에 해당 문자열이 없으므로 빈 상품 배열이 기대값입니다.
추후 E1에서는 같은 입력이 실제 비공개 행을 반환하는지 확인한 뒤 반복 실험에 사용합니다.

```sh
P_CUSTOMER="x%' UNION ALL SELECT id,email,name,0 FROM private.customers -- "
P_ORDER="x%' UNION ALL SELECT id,customer_id::text,total_amount::text,0 FROM private.orders -- "
P_PAYMENT="x%' UNION ALL SELECT id,order_id::text,method,0 FROM private.payment_meta -- "

# 고객정보 입력 1건. 주문/결제 입력은 q 값을 P_ORDER / P_PAYMENT로 바꾸고 파일명도 구분한다.
curl -sS --connect-timeout 3 --max-time 10 --get \
  -H 'Accept: application/json' --data-urlencode "q=$P_CUSTOMER" \
  -D "$LAB_RUN/customer.headers" -o "$LAB_RUN/customer.json" \
  -w 'status=%{http_code} total_s=%{time_total}\n' "$LAB_BASE/products"
cat "$LAB_RUN/customer.json"
```

향후 취약 모드의 쿼리·직렬화 구조가 바뀌면 먼저 입력의 열 개수·형식·길이를 다시 맞추고 공격 집합 버전을 고정합니다.
E1에서도 노출이 안 되는 잘못된 입력을 가지고 E2/E3/E4의 방어 성공을 주장하지 않습니다.

HTTP JSON의 필드 이름은 상품 API 형식을 유지하므로 다음 규칙으로 해석합니다.

| 입력 | `products[].id` | `name` | `description` | 피해로 집계할 데이터 |
|---|---|---|---|---|
| `P_CUSTOMER` | `private.customers.id` | 합성 이메일 | 합성 고객명 | 고유 고객 ID, 노출 필드 email/name |
| `P_ORDER` | `private.orders.id` | customer_id 문자열 | 금액 문자열 | 고유 주문 ID·고객 ID, 노출 필드 total_amount |
| `P_PAYMENT` | `private.payment_meta.id` | order_id 문자열 | 합성 결제수단 | 고유 결제 메타 ID·주문 ID, 노출 필드 method |

공개 상품의 숫자 ID와 고객 ID가 겹치므로 `id` 숫자만 보고 고객 유출로 세지 않습니다.
입력 ID에 맞는 응답 구조와 합성 시드의 관계를 검증합니다. 예를 들어 고객 입력은
`customerNNN@example.invalid` 패턴과 그 고객 ID의 일치를 함께 확인합니다.
기획서의 `customer_id`는 실제 테이블에서 `private.customers.id`를 뜻합니다.
DB 관리자가 직접 SELECT한 결과는 권한 증거이며, 외부 HTTP 유출량에 포함하지 않습니다.

검색 API는 결과를 최대 100행으로 제한합니다. 주문·결제 데이터가 300건 있어도 한 응답으로
300건 전부가 나온다고 가정하지 않습니다. 같은 100행을 10번 받아도 고유 노출량은 100입니다.

### 5. 동일한 공격 집합으로 4개 조건을 비교한다

이 README에서는 기획서의 공격 입력 3종을 다음 **데이터 조회 목적별 시퀀스**로 고정합니다.
세 가지 서로 다른 SQLi 기법을 평가했다는 뜻은 아닙니다.

| 유형 | 시퀀스 안에서 보낼 입력 | 시퀀스당 공격 HTTP 수 |
|---|---|---|
| A01 · 고객 | `P_CUSTOMER` | 1 |
| A02 · 고객+주문 | `P_CUSTOMER` → `P_ORDER` | 2 |
| A03 · 고객+주문+결제 메타 | `P_CUSTOMER` → `P_ORDER` → `P_PAYMENT` | 3 |

각 유형을 조건별 10회씩 실행합니다. **3유형 × 10회 × 4조건 = 120개 공격 시퀀스**이며,
공격 HTTP 요청은 조건별 60개, 전체 240개입니다. 준비용 정상 검색과 마커 요청은 별도 기록하고
이 120개에 포함하지 않습니다. 수동 탐색이나 sqlmap 자동 탐색도 고정 집합의 측정 횟수에 섞지 않습니다.

1. 소스 commit, 이미지 digest, 데이터 시드, 공격 입력, 동시성, 클라이언트 timeout을 고정합니다.
   최초 실험은 동시성 1, 공격 요청 사이 1초 간격으로 통일합니다.
2. `pair_id=A01-R01`처럼 같은 유형·반복을 네 조건에 연결하고,
   `sequence_id=E4-A01-R01`처럼 조건을 포함한 고유 ID도 만듭니다.
3. 조건별로 실제 Catalog DB 역할과 바인딩 구현을 확인합니다. `/health` 표기, 코드,
   DB 권한을 함께 확인하며 환경 변수 이름만으로 모드를 판정하지 않습니다.
4. 각 시퀀스 시작 시 동일 시드 상태를 확인합니다. 초기화가 필요하면 증거를 먼저 보존하고
   사전에 정한 스냅샷/DB 복원 절차로 되돌립니다. 컨테이너 재시작은 DB 초기화가 아닙니다.
   현재는 시퀀스별 자동 복원 도구가 없으며, 위 입력은 읽기 요청만 사용합니다.
5. E1에서 유효성을 확인한 입력을 E2/E3/E4에도 동일하게 전송합니다.
   비교 조건에 따라 실패한 입력을 몰래 수정하지 않습니다. 입력 변경 시 집합 버전을 올리고 모두 다시 비교합니다.
6. 시간에 따른 VM 부하 차이를 줄이도록 반복 블록마다 조건 순서를 순환하거나 미리 섞어 기록합니다.
   역할 전환은 진행 중인 요청이 모두 끝난 뒤 수행합니다.
7. 각 응답의 `X-Request-ID`를 클라이언트 기록의 sequence_id와 연결합니다.
   Nginx가 요청 ID를 새로 발급하므로 클라이언트가 보낸 X-Request-ID가 유지된다고 가정하지 않습니다.
8. 측정 중에는 `setup-ubuntu.sh`, `verify_environment.py`, `restore_safe.py`를 동시에 실행하지 않습니다.
   이 도구들은 컨테이너·wide 역할 상태를 변경합니다.

E2의 wide 역할 활성화·서비스 전환·복귀 명령은 [실험 모드 전환 안내](docs/experiment_plan.md#모드-선택-경계)에 있습니다.
현재 wide 로그인 허용 창은 5분입니다. 만료로 인한 접속 실패를 최소 권한 차단으로 기록하지 않습니다.
`VALID UNTIL`은 기존 연결을 끊는 타이머가 아니므로 종료 시 복구가 필요합니다.
E1/E3 전환 스크립트와 120회 실행·집계기는 아직 제공하지 않습니다.

### 6. 로그인 SQLi와 주문 IDOR는 따로 검사한다

**로그인 SQLi:** Burp에서 `POST /login`의 JSON 요청을 Repeater로 보내 `username`을
`' OR '1'='1' -- `로 바꾸고 틀린 비밀번호를 사용합니다. 로그인 쿠키 없이 시작합니다.
현재 구현은 `401 invalid_credentials`와 새 인증 쿠키 미발급이 기대값입니다.
`GET /session`과 보호된 주문 API까지 확인해 실제 로그인 상태가 생기지 않았는지 검사합니다.
로그인 HTML이 200으로 열리는 현상이나 SQL 조회가 성공한 것만으로 인증 우회라 판정하지 않습니다.
추후 취약 로그인 쿼리를 만들더라도 비밀번호 해시 검증을 실제 통과한 서버 세션이 발급되고
보호 API에 접근돼야 우회 성공입니다. 현재 취약 로그인 버전은 없습니다.

**IDOR:** 정상 로그인한 사용자가 숫자 주문 ID만 바꿔 다른 사람의 주문을 얻는지 검사합니다.

| 요청 상태 | 호출 | 현재 기대값 |
|---|---|---|
| 비로그인 | `GET /orders`, `GET /orders/1001` | JSON 401 |
| 정상 user1 세션 | `GET /orders/1001` | 200, user1 본인 주문 |
| 같은 user1 세션 | `GET /orders/2002` | 404, 타인 주문 데이터 없음 |
| 같은 user1 세션 | 존재하지 않는 주문 ID | 타인 주문과 같은 404 본문 |
| 정상 user2 세션 | `GET /orders/2002` | 200, user2 본인 주문 |
| 같은 user2 세션 | `GET /orders/1001` | 404, 타인 주문 데이터 없음 |

Burp에서는 `Accept: application/json`을 사용하고 각 사용자의 Cookie만 유지한 채 URL의 숫자를 바꿉니다.
브라우저용 리다이렉트를 API 판정에 섞지 않습니다. 로그인은 Ubuntu에서 확인한 해당 환경 비밀번호를 씁니다.
현재 소유자 검증 OFF 모드는 없으므로 위 절차는 ON 상태의 차단 검증입니다.
추후 OFF/ON 대조군을 만들 때는 동일 user1 세션과 동일 숫자 2002로 비교합니다.
`/orders/1 OR 1=1`은 현재 정수 라우팅에서 거부되므로 주문 SQLi 재현 증거가 아닙니다.
주문 SQLi(C1)는 주입 가능한 입력과 취약 쿼리를 따로 구현한 뒤 별도로 시험합니다.

## 방어를 적용했을 때 무엇을 측정할까

### 방어 요소별로 입증할 내용

| 방어 | 적용 지점 | 비교 조건 | 확인할 증거 |
|---|---|---|---|
| D1 · 쿼리 바인딩 | Catalog의 검색값을 SQL과 별도 인자로 전달 | E1↔E2, E3↔E4 | SQL 구조 변조 마커가 사라지고 비공개 노출 0. 정상 작은따옴표 검색 유지 |
| D2 · DB 최소 권한 | Catalog를 `catalog_reader`로 연결 | E1↔E3, E2↔E4 | E3 마커는 재현되지만 private SELECT는 SQLSTATE 42501. 외부 노출 0, 공개 검색 유지 |
| D3 · 객체별 인가 | 세션 user_id로 주문 소유자 조건 추가 | 별도 IDOR OFF↔ON | 동일한 타인 주문의 본문이 사라지고 본인 주문은 정상 |
| D4 · 감사/탐지 | 요청 ID와 DB 이벤트 수집, 추후 규칙 판정 | 같은 고정 공격/정상 집합 | 경고율·오탐·탐지 지연. 경고 발생과 응답 전 차단을 따로 기록 |

D1은 [Psycopg 인자 바인딩](https://www.psycopg.org/psycopg3/docs/basic/params.html) 방식으로
`execute(sql_template, params)`를 호출합니다. 현재 검색 구현은 다음 형태입니다.

```python
sql = "SELECT ... FROM catalog.public_products WHERE label ILIKE %s ESCAPE '!'"
cursor.execute(sql, (escaped_search_term,))
```

DB가 출력한 펼쳐진 SQL 문자열에 입력값이 보이는지만으로 바인딩 여부를 판정하지 않습니다.
호출 코드·코드 소유 템플릿·인자 전달을 함께 확인합니다.
D2는 [PostgreSQL 스키마/테이블 권한](https://www.postgresql.org/docs/17/sql-grant.html),
D3는 [OWASP 객체별 접근 제어 원칙](https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html)에 근거합니다.
바인딩과 최소 권한의 역할 구분은 [OWASP SQLi 방어 지침](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)도 참고합니다.

E4의 노출 0만으로 D1과 D2 각각의 효과를 분리할 수 없습니다.
특히 E3에서 **구조 변조 성립 + private 접근 권한 거부 + HTTP 비공개 노출 0**을 함께 제시해야
최소 권한의 독립적 피해 제한 효과를 설명할 수 있습니다. 최소 권한이 남아 있는 SQLi 자체를 제거했다고 쓰지 않습니다.

### 측정 단위와 계산식

| 지표 | 계산·집계 방법 | 해석 기준 |
|---|---|---|
| 고객 노출량 | HTTP로 노출된 customer_id의 고유 개수 | 응답별·시퀀스별·조건 전체의 합집합을 각각 기록. 분모 100명 |
| 주문 노출량 | HTTP로 노출된 order_id의 고유 개수 | 같은 주문 반복 수신은 1건. 분모 300건 |
| 결제 메타 노출량 | HTTP로 노출된 payment_meta.id의 고유 개수 | 분모 300건. 결제수단은 합성 값이며 실제 카드번호가 아님 |
| 노출 필드 | email/name/customer_id/total_amount/method 등 실제 반환된 필드의 집합 | 행 수와 별도 기록. DB에서 읽었지만 응답에 없던 필드는 HTTP 노출에 넣지 않음 |
| 공격 성공률 ASR | 민감 고객 ID가 1개 이상 노출된 유효 공격 시퀀스 / 유효 공격 시퀀스 × 100 | 조건별 예정 분모 30. 여러 HTTP를 보내도 시퀀스는 1시도 |
| 유출 방지율 | 노출 0으로 확인된 유효 공격 시퀀스 / 유효 공격 시퀀스 × 100 | SQL 구문 변조 방지율과 별개. 타임아웃·판정 불능을 차단 성공으로 넣지 않음 |
| 노출량 감소율 | `(E1 고유 노출량 - 비교 조건 고유 노출량) / E1 고유 노출량 × 100` | 고객/주문/결제 각각 계산. E1이 0이면 N/A이며 실험 유효성을 먼저 재검토 |
| 정상 기능 유지율 | 정상 기능의 상태·본문·인가 조건을 모두 만족한 요청 / 예정 정상 요청 × 100 | 정상 요청 실패·오응답·환경 오류도 원인과 함께 남김 |
| 정상 요청 지연 | Kali에서 측정한 요청 전체 소요시간의 median/p95 | 검색·로그인·본인 주문을 따로 집계. 서버/DB 내부 시간과 구분 |
| IDOR 차단율 | 타인 주문 본문을 반환하지 않은 유효 시도 / 유효 타인 주문 시도 × 100 | 본인 주문 정상률도 반드시 함께 보고 |

ASR의 고객 ID 오라클은 위 A01~A03 모두에 포함한 `P_CUSTOMER` 응답으로 판단합니다.
주문·결제만 별도로 노출됐을 때도 해당 유출은 따로 보고하며 고객 오라클이 0이라는 이유로 보안 성공 처리하지 않습니다.
응답 코드 200은 유출 여부와 독립적입니다. 현재 E4의 빈 검색은 200이어도 방어가 정상 동작한 결과입니다.
503도 자동으로 방어 성공이 아닙니다. E3에서는 같은 요청 ID의 `sqlstate=42501`과 정상 서비스 상태를
연결해야 권한에 의한 거부라고 분류할 수 있습니다.
네트워크 단절·역할 로그인 만료·연결 실패·입력 길이 거부·직렬화 오류는 원인을 구분해 기록합니다.
판정 불능은 N/A로 두고 예정/실행/유효/불능 건수를 함께 보고합니다. 대체 실행은 원본 실패 기록과 연결합니다.

### 정상 요청과 성능 측정

기획서의 최소 기준은 조건별 정상 요청 30회 이상입니다. 이 README의 권장 구성은
**조건별 정상 시퀀스 30개**이며 각 시퀀스에서 상품 검색·정상 로그인·본인 주문 조회를 한 번씩 측정합니다.
따라서 기능별 30개, 조건별 측정 요청 90개이며, 로그인 후 로그아웃 같은 정리 요청은 별도 표기합니다.

- 검색 입력은 `Notebook`, `O'Reilly`, 미존재 문자열을 각각 10회 사용합니다.
  기대 행 수는 각각 1·1·0이며 작은따옴표로 인한 정상 검색 실패도 결과에 포함합니다.
- 로그인은 올바른 user1 자격증명과 세션 발급을 확인합니다. 실패 비밀번호는 정상 집합에 넣지 않습니다.
- 본인 주문은 그 세션으로 1001을 조회해 주문 ID·소유 관계를 확인합니다.
- 컨테이너 준비 완료 후 워밍업을 같은 횟수로 수행하고 워밍업 요청은 통계에서 제외합니다.
  동시성·요청 간격·VM CPU/RAM을 동일하게 유지하고 측정 중 재빌드·패키지 설치를 하지 않습니다.
- curl의 `%{time_total}`은 초 단위입니다. 밀리초로 보고하려면 1000을 곱합니다.
  `%{time_starttransfer}`를 추가 수집할 경우 TTFB라고 별도로 이름 붙입니다.
- p95는 시간을 오름차순 정렬한 뒤 **`ceil(0.95 × n)`번째 값**으로 계산합니다.
  n=30이면 29번째 값입니다. 계산 방식을 네 조건에 동일하게 적용합니다.
- 성공 응답 지연과 실패/타임아웃 건수를 함께 보고합니다. 검색·로그인을 한데 합친 p95로
  방어 오버헤드를 설명하지 않습니다. PBKDF2 비용이 있는 로그인은 별도 그래프로 비교합니다.
- 같은 기능의 `p95 증가율 = (방어 조건 p95 - 기준 조건 p95) / 기준 조건 p95 × 100`입니다.
  성공 표본 수가 다르거나 기준값이 없는 경우 수치의 한계와 실패율을 함께 표시합니다.

성능 수집 예시는 다음과 같습니다. 위에서 준비한 Kali `LAB_BASE`·`LAB_RUN`을 사용합니다.

```sh
curl -sS --connect-timeout 3 --max-time 10 --get \
  -H 'Accept: application/json' --data-urlencode 'q=Notebook' \
  -o "$LAB_RUN/normal-search.json" \
  -w 'status=%{http_code},total_s=%{time_total},ttfb_s=%{time_starttransfer}\n' \
  "$LAB_BASE/products"
```

### 탐지율·오탐률과 차단을 구분한다

현재 로그에 오류가 남는 것만으로 자동 탐지가 구현된 것은 아닙니다.
지금의 탐지율·오탐률·탐지 지연은 **N/A(탐지기 미구현)**로 기록합니다.
추후 규칙을 구현하면 먼저 rule_id, 규칙 버전, 공격/정상 정답 집합, 판정 시간 창을 고정합니다.

| 구분 | 실제 공격 시퀀스 | 실제 정상 시퀀스 |
|---|---|---|
| 경고 있음 | TP | FP |
| 경고 없음 | FN | TN |

- 탐지율/Recall = `TP / (TP + FN)`.
- 오탐률/FPR = `FP / (FP + TN)`.
- 정밀도/Precision = `TP / (TP + FP)`; 경고가 하나도 없으면 N/A입니다.
- 경고는 `(sequence_id, rule_id)`로 중복 제거합니다. 전체 탐지율은 규칙이 여러 개 울려도
  한 시퀀스를 한 번만 셉니다. 정상 시퀀스 30개에서 요청 90개를 보냈더라도 FPR의 분모는 30입니다.
- 탐지 시점은 경고 생성 시각으로 기록합니다. 서로 다른 VM의 시각을 비교하면 먼저 시간 오차를 확인하고,
  동기화 근거가 없으면 절대 시각 기반 탐지 지연은 N/A로 둡니다.
- `alerted`·`response_blocked`·`private_data_exposed`를 별도 필드로 둡니다.
  경고가 울려도 데이터가 이미 응답에 포함됐다면 유출 성공이며, 경고 발생만으로 차단됐다고 쓰지 않습니다.

현재 앱 로그는 인자 값을 마스킹합니다. 검색 문자열의 패턴을 판정하는 탐지 규칙을
현재 감사 파일만으로 구현할 수 있다고 가정하지 않습니다. 필요한 입력 특징을 별도로 정의하고,
비밀번호·세션 쿠키·DB 비밀값을 수집하지 않는 방식으로 계측을 설계해야 합니다.

## 실험 증거와 결과표를 남기는 방법

### 수집할 증거

Ubuntu에서는 실험 시작 시각을 정하고 종료 후 같은 시간 범위의 앱 로그를 보관합니다.
아래 명령의 실행 위치는 Ubuntu 저장소 루트입니다.

```sh
LAB_START_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)
LAB_EVIDENCE="results/manual-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$LAB_EVIDENCE"
git rev-parse HEAD > "$LAB_EVIDENCE/commit.txt"
sudo docker compose -f docker-compose.yml images > "$LAB_EVIDENCE/images.txt"

# Kali에서 해당 실험을 끝낸 다음 실행한다.
sudo docker compose -f docker-compose.yml logs --no-color --no-log-prefix \
  --since "$LAB_START_UTC" catalog-service order-service > "$LAB_EVIDENCE/app-events.jsonl"
```

앱 이외의 출력이 섞일 수 있으므로 JSON으로 파싱되는 이벤트만 분석합니다.
`db_query`의 `template_id`, `binding`, `database_role`, `row_count`, `outcome`, `sqlstate`와
`http_request`의 상태·인가결과·처리시간을 **응답의 request_id**로 연결합니다.
감사 로그의 행 수는 DB가 읽은 행 수이며 HTTP로 실제 노출된 고객 수와 다를 수 있습니다.

| 파일 | 내용 |
|---|---|
| `manifest.json` | 실행 시각, commit, 이미지 digest, 시드 버전, 조건 순서, VM 자원, 도구 버전, 입력 집합 버전 |
| `requests.csv` | HTTP 1건당 1행: sequence_id, 요청 종류, request_id, 상태, 전체 지연, 오류 분류 |
| `sequences.csv` | 공격/정상 시퀀스 1개당 1행: 조건·유형·반복·유출 ID 집합·성공 판정·경고 여부 |
| `responses/` | 요청 ID로 연결한 응답 헤더와 합성 데이터 본문. 인증 Cookie/Set-Cookie는 마스킹 |
| `app-events.jsonl` | 해당 실행 시간 범위의 구조화된 앱 감사 이벤트 |
| `db-permissions.txt` | 실제 역할, GRANT/REVOKE 근거, 공개 조회 성공과 private SELECT 허용/거부 |
| `summary.csv` | 조건별 표본 수, 노출량, ASR, 정상 기능률, 기능별 median/p95, 탐지 지표 |

위 파일명은 **후속 실험 수집기의 권장 형식**입니다. 현재 검증기가 이 파일을 전부 자동 생성하지는 않습니다.
현재 `verify_environment.py`의 산출물은 `test_results.csv`, `junit.xml`, `host_checks.json`,
`audit_events.jsonl`, `versions.json`, `summary.json`이며 별도의 환경 검사 증거입니다.

공격 시퀀스 CSV의 권장 헤더는 다음과 같습니다. 고객·주문 ID는 중복 제거한 JSON 배열 등
파싱 가능한 형식으로 저장하고, CSV 안에 넣을 때는 CSV 인용 규칙을 적용합니다.

```csv
run_id,condition,pair_id,sequence_id,attack_type,repetition,request_ids,actual_db_role,binding_mode,validity,customer_ids,order_ids,payment_meta_ids,exposed_fields,attack_success,alerted,response_blocked,error_reason
```

증거는 로컬 `results/`에 보관합니다. `.env`, DB 비밀번호, 세션 쿠키·토큰은 Git·PPT에 넣지 않습니다.
결과를 공유할 때는 비밀값을 제거한 요약과 캡처만 사용합니다.

### 발표에 넣을 최종 비교표

아래는 빈 결과표입니다. 실제 측정 전에는 예상값을 실측값처럼 채우지 않습니다.

| 조건 | 유효/예정 공격 seq | 고객/100 | 주문/300 | 결제 메타/300 | ASR | 정상 기능률 | 검색 median/p95 | 탐지율/FPR |
|---|---|---|---|---|---|---|---|---|
| E1 | 미측정/30 | 미측정 | 미측정 | 미측정 | 미측정 | 미측정 | 미측정 | N/A·탐지기 미구현 |
| E2 | 미측정/30 | 미측정 | 미측정 | 미측정 | 미측정 | 미측정 | 미측정 | N/A·탐지기 미구현 |
| E3 | 미측정/30 | 미측정 | 미측정 | 미측정 | 미측정 | 미측정 | 미측정 | N/A·탐지기 미구현 |
| E4 | 미측정/30 | 미측정 | 미측정 | 미측정 | 미측정 | 미측정 | 미측정 | N/A·탐지기 미구현 |

그래프는 조건별 고유 고객/주문 노출량, ASR, 정상 기능 유지율, 기능별 median/p95를 나눠 그립니다.
IDOR 결과도 SQLi 2×2 표와 별도 표로 제출합니다. 반복 10회는 같은 고정 입력의 반복이므로
임의의 SQLi 전체에 대한 성공 확률로 일반화하지 않습니다.

최종 시연은 정상 검색 → E1의 합성 정보 노출 → 같은 입력의 E2/E3 결과와 차단 원인 →
E4 정상 기능 확인 → 별도 IDOR → 실제 측정표 순서로 진행합니다.
현재는 취약 모드와 반복 실험을 아직 구현하지 않았으므로 E1/E3 유출 장면을 이미 재현했다고 발표하지 않습니다.

### 실험을 끝내고 정상 상태로 복귀한다

Ubuntu에서 실행합니다. DB 데이터를 삭제하지 않고 wide 역할과 Catalog 설정을 정상 상태로 돌립니다.

```sh
sudo -v
python3 scripts/restore_safe.py
curl -sS http://192.168.67.20:18080/health/catalog
# database_role=catalog_reader, query_mode=bound 확인
python3 scripts/verify_environment.py --no-build
```

복구 명령은 wide 역할을 NOLOGIN으로 바꾸고 남아 있는 wide DB 연결을 종료합니다.
공개 검색·로그인·본인 주문의 정상 동작을 다시 확인하고 Kali의 다운로드용 NAT도 끕니다.
증거를 남기기 위해 종료 과정에서 `docker compose down -v`로 볼륨을 삭제하지 않습니다.

## 운영 명령

Docker 그룹 권한이 없는 사용자는 Docker 명령 앞에 `sudo`를 붙입니다.
설치 스크립트는 이 경우 sudo를 사용하므로 로그아웃/재로그인 없이 실행할 수 있습니다.

```sh
sudo docker compose -f docker-compose.yml ps
sudo docker compose -f docker-compose.yml logs --tail 30 catalog-service order-service
sudo docker compose -f docker-compose.yml down          # DB 유지하며 종료
bash scripts/setup-ubuntu.sh                            # 시작·갱신·검증
bash scripts/setup-ubuntu.sh --skip-verify              # 시작·갱신만
sudo -v
python3 scripts/verify_environment.py                   # 별도 재검증
python3 scripts/restore_safe.py                         # wide 실험 역할 비활성화·정상 복귀
```

초기화 SQL은 빈 PostgreSQL 볼륨에 최초 실행할 때 적용합니다. 기존 볼륨에 스키마 변경을 적용하려면
별도 마이그레이션이 필요합니다. `.env`의 비밀번호만 수정해도 DB 내부 비밀번호가 바뀌지는 않습니다.
DB 삭제는 `scripts/reset_lab.py --confirm-delete-minishop-data`를 직접 선택할 때만 수행합니다.

## 구조와 검증

```text
docker-compose.yml       # 기본 서비스 4개 + 일시 검증 프로필
services/catalog/        # 공개 상품 API, catalog_reader
services/orders/         # 인증·주문 API와 기존 MiniShop 웹 화면
services/common/         # DB 연결·파라미터 바인딩·오류 처리·감사 로그
database/                # 역할·스키마·초기화·합성 시드
nginx/                   # 단일 HTTP 진입점
scripts/                 # Ubuntu 자동 설치·설정 생성·검증·복구
tests/                   # HTTP·DB 권한·웹 화면·설치 재실행 검사
experiments/             # 명시적으로 활성화하는 과도한 SELECT 권한 실험 설정
docs/                    # 팀원 안내·설계·검증 기록
```

Python·PostgreSQL·Nginx 이미지는 digest, Python 패키지는 버전으로 고정합니다.
Docker Engine/Compose는 기존 정상 설치를 재사용하며, 없을 때 [Docker 공식 apt 저장소](https://docs.docker.com/engine/install/ubuntu/)에서 설치합니다.
실제 버전은 각 검증 실행의 `results/<run_id>/versions.json`에 기록합니다.
DB·앱 포트는 외부에 공개하지 않고 Nginx의 확인된 사설 IP/18080만 공개합니다.

현재 구현 범위는 정상 서비스·최소 권한·사용자별 주문 인가·환경 재현입니다.
SQLi 취약 모드·120시퀀스 자동화·자동 탐지는 후속 작업입니다.
`.env*`(예시 제외), `instance/`, `results/`, VM·설치 이미지는 Git/소스 배포에서 제외합니다.

- [팀원 설치 순서](docs/TEAM_SETUP.md)
- [기존 SQLite 버전에서 업데이트](docs/MIGRATION.md)
- [아키텍처와 권한 경계](docs/architecture.md)
- [VM 설정](docs/vm_setup.md)
- [실제 검증 기록](docs/validation.md)
- [실험 모드 전환과 후속 구현 조건](docs/experiment_plan.md)
