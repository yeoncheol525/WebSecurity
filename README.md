# MiniShop · 웹 보안 실험환경

Kali는 실험 클라이언트, Ubuntu Server는 웹서버입니다. Ubuntu 안의 Docker Compose가
Nginx·상품 서비스·인증/주문 서비스·PostgreSQL을 실행합니다. 기존 MiniShop 화면을 유지하면서
SQLite 단일 앱을 PostgreSQL과 서비스별 DB 권한 구조로 개편했습니다.

```text
Windows / VMware
  Kali VM ── Host-only ── Ubuntu Server VM
  브라우저·Burp            Docker: Nginx → Catalog / Orders → PostgreSQL
```

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
SQLi 취약 모드와 반복 공격 실험은 후속 작업입니다.
`.env*`(예시 제외), `instance/`, `results/`, VM·설치 이미지는 Git/소스 배포에서 제외합니다.

- [팀원 설치 순서](docs/TEAM_SETUP.md)
- [기존 SQLite 버전에서 업데이트](docs/MIGRATION.md)
- [아키텍처와 권한 경계](docs/architecture.md)
- [VM 설정](docs/vm_setup.md)
- [실제 검증 기록](docs/validation.md)
- [후속 실험 계획](docs/experiment_plan.md)
