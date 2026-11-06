# MiniShop

상품 검색의 SQL 바인딩과 PostgreSQL 최소 권한을 비교하는 웹 보안 실습.

연구 질문: SQL Injection이 남아 있어도 DB 최소 권한으로 고객·거래정보 노출을 제한할 수 있는가?
E1~E4의 실행 환경과 방어 예제 코드를 제공하며, 조건별 실험·측정·결과 분석은 팀원이 직접 수행한다.

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

## 제공 범위와 팀원 작업

| 구분 | 현재 제공된 내용 | 팀원이 직접 수행할 일 |
|---|---|---|
| 환경 | 정상 웹 기능·합성 시드·E1~E4 설정 | 서버 준비, 조건 선택, 웹 계정 전달 |
| 방어 | 검색 바인딩·DB 역할/권한·주문 소유자 검사 구현 | 코드와 권한 검토·보완, 동일 입력의 응답·로그 대조 |
| 실험·분석 | 요청 관찰 방법·측정 기준·빈 결과표 | 입력 집합과 판정 기준 확정, 반복 측정, 조건별 방어 효과 분석·발표 |

방어 코드도 이미 포함돼 있으므로 제공 범위는 환경 설치보다 넓다.
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
