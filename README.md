# MiniShop

상품 검색의 SQL 바인딩과 PostgreSQL 최소 권한을 비교하는 웹 보안 실습.

연구 질문: SQL Injection이 남아 있어도 DB 최소 권한으로 고객·거래정보 노출을 제한할 수 있는가?
E1~E4의 실행 환경과 방어 예제 코드를 제공하며, 조건별 실험·측정·결과 분석은 팀원이 직접 수행한다.

과제 시연의 목표는 합성 고객·거래정보의 노출 여부와 방어 조건별 차이를 실제 응답·로그·측정값으로 설명하는 것이다.
담당 팀원은 [실험 진행과 제출물 안내](docs/experiment_plan.md)를 따라 입력 목록 작성부터 결과표·영상까지 직접 준비한다.
아래 정상 검색 예시는 접속 확인용이며, 노출 사고 재현은 아직 실측하지 않았다.

```text
Kali Desktop / Windows: Burp Suite + 내장 브라우저
  → Ubuntu Host-only HTTP :18080
    → Nginx → Catalog / Orders → PostgreSQL
```

## 서버 실행 · Ubuntu

조건: Ubuntu 24.04 LTS amd64, Python 3, Bash, Host-only 네트워크.
최초 설치에는 패키지·이미지 다운로드를 위한 인터넷 연결과 sudo 권한도 필요하다.
저장소를 처음 받는 경우 Ubuntu에서 GitHub 접근 권한과 인증을 준비한 뒤 실행한다.

```sh
sudo apt-get update
sudo apt-get install -y git
git clone https://github.com/yeoncheol525/WebSecurity.git minishop
cd minishop
```

이후 명령 실행 위치는 `docker-compose.yml`이 있는 프로젝트 루트다.
이미 소스를 받았다면 해당 폴더에서 시작한다. Windows 작업 폴더에서는 `minishop/project/`에 해당한다.

```sh
bash scripts/setup-ubuntu.sh
```

- 최초 실행 조건: E4.
- 이후 실행 조건: 마지막 선택 유지.
- 설치 범위: Docker 도구, 로컬 설정, 합성 데이터, 서비스 시작, healthcheck.
- 기존 DB와 비밀번호 유지.
- 기본 HTTP 포트: `18080`.

설치는 서비스 기동 확인에서 끝난다. 회귀 검사는 [별도 명령](docs/development_checks.md)으로 실행한다.

Host-only 주소 지정:

```sh
bash scripts/setup-ubuntu.sh --bind 192.168.67.20
```

IP는 Ubuntu의 실제 Host-only 주소로 지정한다.
주소를 생략하면 기존 설정을 유지하고, 첫 설치에서는 전용 사설 NIC를 자동 선택한다.
후보가 없으면 loopback을 사용하고, 여럿이면 `--bind`로 지정해야 한다.
웹 로그인 계정 확인:

```sh
python3 scripts/demo_credentials.py
```

## 실행 조건

동시에 한 조건만 실행한다. 모든 조건은 같은 DB·주소·포트를 사용한다.
네 조건은 같은 사이트의 실행 설정이며, 조건별로 독립된 사이트 네 개를 동시에 실행하지 않는다.

| 조건 | 검색 바인딩 D1 | DB 최소 권한 D2 | Catalog DB 역할 | 설정 |
|---|---|---|---|---|
| E1 | OFF | OFF | `catalog_reader_wide` | [기준선](experiments/E1/README.md) |
| E2 | ON | OFF | `catalog_reader_wide` | [바인딩](experiments/E2/README.md) |
| E3 | OFF | ON | `catalog_reader` | [최소 권한](experiments/E3/README.md) |
| E4 | ON | ON | `catalog_reader` | [바인딩 + 최소 권한](experiments/E4/README.md) |

Ubuntu 프로젝트 루트에서 조건 선택:

```sh
bash scripts/setup-ubuntu.sh --experiment E1
```

`--experiment` 허용값: `E1`, `E2`, `E3`, `E4`.
E1·E3은 검색 문자열 삽입 모드, E2·E4는 파라미터 바인딩 모드다.
E1·E2는 wide 역할의 로그인을 활성화하고, E3·E4는 해당 역할과 기존 연결을 비활성화한다.
주문 소유자 검사는 모든 조건에서 유지한다.
전환 후 `/health/catalog`의 `database_role`과 `query_mode`로 실제 실행 조건을 확인한다.
DB·비밀번호·기존 결과는 전환 시 초기화하지 않는다.

## 실제로 무엇을 입력하나

**네 조건 모두 같은 검색값을 넣는다. 조건마다 바꾸는 것은 서버의 방어 설정이다.**
먼저 아래 정상 검색 네 가지로 사용 순서와 기능을 확인한다.

| 상품 검색창에 넣을 값 | E1 예상 | E2 예상 | E3 예상 | E4 예상 |
|---|---|---|---|---|
| `Notebook` | 상품 1개 | 상품 1개 | 상품 1개 | 상품 1개 |
| `NoSuchProduct` | 상품 0개 | 상품 0개 | 상품 0개 | 상품 0개 |
| 검색창을 비운 상태 | 공개 상품 12개 | 공개 상품 12개 | 공개 상품 12개 | 공개 상품 12개 |
| `O'Reilly` | 검색 오류 예상 | 상품 1개 | 검색 오류 예상 | 상품 1개 |

위 표는 현재 코드와 초기 시드를 기준으로 한 예상값이다. `Notebook`과 `O'Reilly`의 대상 상품명은
`O'Reilly Notebook`이다. `O'Reilly`는 작은따옴표가 들어간 정상 상품명 검색이며,
E1·E3의 문자열 처리 경로에서는 오류가 예상된다. 실제 관측값은 직접 기록한다.

진행 순서:

1. Ubuntu에서 `bash scripts/setup-ubuntu.sh --experiment E1`을 실행한다.
2. Kali 또는 Windows의 Burp 내장 브라우저에서 `/shop`을 열고 위 네 검색값을 하나씩 입력한다.
3. 각 검색 후 **Proxy → HTTP history**에서 `/products` 요청의 상태 코드·응답 본문·`X-Request-ID`를 기록한다.
   상품이 0개인 응답과 오류 응답을 구분한다.
4. Ubuntu 명령의 `E1`을 `E2`로 바꿔 실행하고, 같은 주소에서 같은 네 입력을 반복한다. E3·E4도 같은 순서다.
5. [정상 검색 기록표](docs/experiment_plan.md#정상-검색-기록)에 조건별 관측값을 적는다.

즉, **E1에서 네 입력 기록 → E2에서 같은 네 입력 기록 → E3 → E4** 순서다.
조건을 바꾸는 명령은 앞 조건의 기록을 마친 뒤 실행한다.

이 입력들은 정상 기능 확인용이다. 공개 상품 검색만으로는 DB 최소 권한의 효과를 확인할 수 없다.
DB 권한 비교에는 실제 역할·GRANT와 접근 허용/거부의 별도 근거가 필요하다.
공격 실험에 사용할 공통 입력 목록은 아직 이 README에 정의돼 있지 않다.
따라서 위 확인을 공격 성공률·비공개 데이터 노출량의 측정으로 기록하지 않는다.

## 과제 실험은 누가 무엇을 하나

| 담당 | 직접 할 일 | 완료 근거 |
|---|---|---|
| 환경 | 서버 실행, E1~E4 선택, 웹 계정 전달 | 실행 commit·주소·실제 DB 역할·query_mode |
| 실험 | 공통 실험 입력과 판정 기준 작성, 각 조건에서 관측·측정 | 입력 목록·요청별 응답·캡처·request_id |
| 방어 | 코드와 DB 권한 확인, 정상 기능과 방어 원인 분석 | 코드·권한·동일 request_id 로그를 연결한 설명 |
| 통합·발표 | 네 조건 비교, 한계 정리, 제출 영상과 결과표 작성 | 실측 결과표·근거 파일·영상 |

입력 목록은 [담당자 작성 양식](docs/experiment_plan.md#시작-전에-담당자가-작성할-것)에 먼저 채운다.
그다음 정상 기능 확인, 조건별 실험 기록, 방어 원인 분석, 제출물 정리 순서로 진행한다.
예상 결과와 실측값을 구분하며, 관측되지 않은 항목은 `미측정`으로 남긴다.
현재 비교 범위는 상품 검색이다. 로그인·주문 소유자 검사는 항상 적용되고,
고객정보·배송지 변경 기능과 인가 OFF/ON 비교는 현재 버전에 포함돼 있지 않다.

## 제공 코드와 검증 범위

정상 웹 기능·합성 시드·E1~E4 설정과 검색 바인딩·DB 권한·주문 소유자 검사 코드를 제공한다.
팀원은 실제로 검토·수정·검증한 내용을 기여로 기록한다.
설치 성공과 개발 회귀 검사 통과는 조건별 공격 성공률·방어 효과의 실측 결과를 대신하지 않는다.
조건별 결과표는 `미측정` 상태이며, [기존 VM 검증 기록](docs/validation.md)은 이전 버전의 환경 검사 이력이다.

## 브라우저 사용 · Kali Desktop / Windows

접속 조건: 브라우저에서 Ubuntu의 Host-only 주소에 접근 가능.
사용 도구: **Burp Suite Community Edition과 내장 브라우저**.

| 도구 | 용도 |
|---|---|
| Burp 내장 브라우저 | 웹 화면 조작과 Burp Proxy 연결 |
| Proxy → HTTP history | 요청·응답·상태 코드·헤더 기록 |
| Repeater | 선택한 정상 요청 재전송과 응답 확인 |
| 브라우저 F12 | 화면과 네트워크 보조 확인 |

### 1. Burp 실행

1. Kali의 앱 목록 또는 Windows 시작 메뉴에서 **Burp Suite**를 실행한다.
2. 미설치 상태라면 [공식 설치 안내](https://portswigger.net/burp/documentation/desktop/getting-started/download-and-install)의 Community Edition 설치 파일을 사용한다.
3. 시작 마법사가 표시되면 기본 프로젝트·설정으로 **Next → Start Burp**를 선택한다.
4. **Proxy → Intercept**에서 **Intercept off**로 설정한다.
5. 같은 화면의 **Open browser**를 누른다.

내장 브라우저는 Burp Proxy 연결이 미리 설정돼 있다.
**Intercept off**에서도 HTTP history에 요청과 응답이 기록된다.
관련 설정은 [내장 브라우저](https://portswigger.net/burp/documentation/desktop/tools/burps-browser)와
[HTTP history](https://portswigger.net/burp/documentation/desktop/tools/proxy/http-history)를 따른다.

### 2. 정상 검색 요청 기록

1. Burp가 연 브라우저에서 `http://192.168.67.20:18080/shop`에 접속한다. IP는 실제 Ubuntu 주소로 바꾼다.
2. **어떤 상품을 찾으세요?** 검색창에 `Notebook`을 입력하고 **검색**을 누른다.
3. Burp의 **Proxy → HTTP history**로 돌아간다.
4. Host가 Ubuntu 서버이고 URL이 `/products?q=Notebook`인 요청을 선택한다.
5. **Request**에서 요청 메서드·주소·검색값을 확인한다.
6. **Response**에서 상태 코드, `products` JSON, 응답 헤더의 `X-Request-ID`를 확인한다.
7. 조건·입력값·요청·응답·상태 코드·X-Request-ID·화면 캡처를 [결과표](docs/experiment_plan.md)에 기록한다.

화면 주소는 `/shop?q=...`, 상품 API는 `/products?q=...`다.
상품 데이터는 HTTP history의 `/products` 요청에서 확인한다.

### 3. 정상 요청 재전송 · Repeater

1. HTTP history의 정상 `/products?q=Notebook` 요청을 우클릭하고 **Send to Repeater**를 선택한다.
2. **Repeater** 탭에서 전달된 요청을 선택한다.
3. 요청 내용을 그대로 둔 채 **Send**를 누른다.
4. 새 응답의 상태 코드·본문·`X-Request-ID`를 확인한다. 재전송별 응답 ID를 별도로 기록한다.

메뉴 동작은 [공식 Repeater 안내](https://portswigger.net/burp/documentation/desktop/getting-started/reissuing-http-requests)를 따른다.

### 4. 로그인과 본인 주문

Burp 내장 브라우저에서 **로그인**에 웹 계정을 입력한 뒤 **내 주문 → 상세 보기**를 연다.
요청과 응답은 같은 HTTP history에서 확인한다.

Burp 실행과 위 화면 조작에는 터미널 명령이 필요하지 않다.
조건 전환은 Ubuntu에서 실행하고 브라우저를 새로고침한다.
Kali·Windows의 `localhost`는 Ubuntu 서버 주소가 아니다.

## 화면과 API

| 기능 | 화면 | API |
|---|---|---|
| 상품 검색 | `/shop` | `GET /products?q=...` |
| 로그인 | `/login` | `POST /login` |
| 본인 주문 | `/account/orders` | `GET /orders`, `GET /orders/{id}` |
| Catalog 상태 | — | `GET /health/catalog` |
| Orders 상태 | — | `GET /health/orders` |

데이터는 합성 고객 100명·주문 300건·결제 메타 300건이다.
user1 주문은 1001~1003, user2 주문은 2001~2003이다.
검색 응답은 최대 100행이다.
자동 탐지 규칙은 미구현이며 탐지율·오탐률은 `N/A`로 기록한다.

## 서버 관리 · Ubuntu

```sh
sudo docker compose ps
sudo docker compose logs --tail 30 catalog-service order-service
bash scripts/setup-ubuntu.sh
sudo docker compose down
```

재실행은 선택한 조건으로 서비스를 재빌드한다. 종료 시 DB 볼륨은 유지한다.
시작·재시작과 조건 전환에는 `setup-ubuntu.sh`를 사용한다.
`docker compose up`만 실행하면 `.env`의 `LAB_EXPERIMENT`에 해당하는 조건별 설정이 적용되지 않는다.
실습 종료 후 E4로 전환:

```sh
bash scripts/setup-ubuntu.sh --experiment E4
```

`.env`, DB, 세션 쿠키, VM, 설치 이미지, 원본 결과는 Git에서 제외한다.

## 소스 위치

- `services/catalog/`: 상품 API.
- `services/orders/`: 로그인·주문 API와 웹 화면.
- `services/common/`: DB 실행·감사 로그.
- `database/`: 역할·스키마·합성 시드.
- `experiments/E*/compose.yml`: 조건별 설정.
- `scripts/`: 설치·기동·검증.
- `tests/`: 회귀 검사.
- `results/`: 로컬 실행 기록.

[설치](docs/TEAM_SETUP.md) · [검증](docs/development_checks.md) · [결과 기록](docs/experiment_plan.md) · [구조](docs/architecture.md) · [Git](docs/GIT_COLLAB.md) · [기존 버전 갱신](docs/MIGRATION.md)
