# Team 4 · MiniShop

웹보안 실습을 위한 Flask 기반 쇼핑 웹 애플리케이션입니다. 로그인·로그아웃, 상품 검색, 본인 주문 조회와 샘플 SQLite DB를 제공합니다. 현재 구현 범위는 기본 웹 기능과 실행 환경이며, 공격 시나리오와 방어 비교 기능은 포함하지 않습니다.

## 실행 구조

```text
VMware
├─ Ubuntu VM
│  └─ Docker 컨테이너: Python 3.12 · Flask 웹서버 · SQLite 라이브러리
└─ Kali VM: 브라우저 · 보안 실습 도구
```

Docker Engine과 Compose는 **Ubuntu VM 안에 설치**합니다. 호스트 Windows의 Docker Desktop은 필요하지 않습니다. 웹서버는 컨테이너 안에서 실행하고, DB 파일은 Ubuntu의 프로젝트 폴더에 보존합니다.

## 요구 사항

- Ubuntu 24.04 LTS VM과 `sudo` 권한
- 설치 패키지·소스·컨테이너 이미지를 다운로드할 인터넷 연결
- Kali에서 접속할 경우 두 VM 사이의 Host-only 네트워크

VM 생성·가져오기, 운영체제 이미지, Kali 도구 설치는 저장소의 자동 구성 범위에 포함하지 않습니다. Host-only 네트워크만 연결된 VM은 외부 다운로드가 불가능하므로 최초 설치 전에 인터넷 연결을 준비해야 합니다.

## 빠른 시작

다음 명령은 **Ubuntu 터미널에서** 실행합니다.

```bash
sudo apt update
sudo apt install -y git
git clone https://github.com/yeoncheol525/WebSecurity.git Team4_WebSecurity_Lab
cd Team4_WebSecurity_Lab
bash scripts/setup-ubuntu.sh
```

설정 스크립트는 Docker Engine·Compose 설치 상태를 확인하고, 필요한 구성 요소를 설치한 뒤 `docker compose up --build`를 실행합니다. 기존 Docker는 재사용하며 Python·Flask·SQLite를 Ubuntu에 별도로 설치할 필요가 없습니다. 설치에 필요한 경우 `sudo` 비밀번호를 입력합니다.

서버 로그는 실행한 터미널에 표시되며 `Ctrl+C`로 웹서버를 중지합니다. 기본 접속 주소는 **Ubuntu 내부의 `http://127.0.0.1:5000`**입니다. 별도 Ubuntu 터미널에서 상태를 확인할 수 있습니다.

```bash
curl http://127.0.0.1:5000/health
```

웹서버를 실행하지 않고 Docker 설치만 진행하려면 `bash scripts/setup-ubuntu.sh --install-only`를 사용합니다.

## Kali 접속 설정

기본 설정은 Ubuntu 내부 접속만 허용합니다. Kali에서 접속하려면 실행 전 프로젝트의 `.env`에 Ubuntu의 **Host-only 인터페이스 IP**를 지정합니다. `.env`가 없는 경우에만 예제 파일을 복사합니다.

```bash
test -f .env || cp .env.example .env
```

`.env`를 편집합니다. 다음 IP는 예시이며 실제 Ubuntu 주소로 변경해야 합니다.

```dotenv
BIND_ADDRESS=192.168.67.20
WEB_PORT=5000
```

`bash scripts/setup-ubuntu.sh`로 실행한 뒤 Kali 브라우저에서 `http://192.168.67.20:5000`에 접속합니다. Ubuntu에서 상태를 확인할 때도 `curl http://192.168.67.20:5000/health`처럼 설정한 IP와 포트를 사용합니다. `.env`는 Git에 포함하지 않습니다.

## 코드 업데이트

실행 중인 서버를 `Ctrl+C`로 중지한 뒤 프로젝트 폴더에서 실행합니다.

```bash
git pull --ff-only
bash scripts/setup-ubuntu.sh
```

컨테이너에는 빌드 시점의 코드가 포함됩니다. 로컬 코드 수정 후에도 같은 스크립트로 다시 빌드해 반영합니다. 기존 DB와 `.env`는 유지됩니다.

컨테이너와 프로젝트 네트워크를 제거하려면 다음 명령을 사용합니다. DB 파일은 삭제하지 않습니다.

```bash
sudo docker compose down
```

## 데이터베이스

| 항목 | 위치 |
|---|---|
| Ubuntu의 DB 파일 | `<프로젝트 폴더>/instance/minishop.sqlite3` |
| 컨테이너 내부의 동일 DB | `/app/instance/minishop.sqlite3` |
| 테이블 정의 | `minishop/schema.sql` |
| 초기 데이터 생성 | `minishop/db.py` |

최초 실행 시 테이블·샘플 데이터·세션 키를 자동 생성합니다. 이후 실행은 기존 데이터를 유지합니다. SQLite는 웹 프로세스가 파일을 직접 사용하는 방식이므로 별도 DB 서버와 웹서버–DB 서버 간 TCP 연결은 없습니다.

DB 파일과 세션 키는 `instance/`에 저장하며 Git에서 제외합니다. 저장소는 스키마와 초기 데이터 코드를 공유합니다. 기존 DB에 스키마 변경을 자동 적용하는 마이그레이션 기능은 없습니다.

### 샘플 데이터 초기화

다음 작업은 **기존 DB를 샘플 데이터로 교체**합니다. 필요한 데이터를 백업하고 실행합니다.

```bash
sudo docker compose down
sudo docker compose run --rm web python -m scripts.init_db --reset
bash scripts/setup-ubuntu.sh
```

### 샘플 계정

| 사용자 | 비밀번호 | 본인 주문 |
|---|---|---|
| user1 | `User1-Lab!2026` | #1001 · Keyboard |
| user2 | `User2-Lab!2026` | #2002 · Laptop |

계정·상품·주문은 실습용 합성 데이터입니다.

## 프로젝트 구조

| 경로 | 내용 |
|---|---|
| `scripts/setup-ubuntu.sh` | Ubuntu의 Docker 설치 확인·설치·웹서버 실행 |
| `Dockerfile`, `compose.yaml` | 웹 이미지 빌드·포트 연결·DB 저장 경로 |
| `requirements.txt` | Python 패키지 버전 |
| `minishop/auth.py` | 로그인·로그아웃·현재 사용자 |
| `minishop/shop.py` | 상품 검색·주문 조회 |
| `minishop/templates/`, `minishop/static/` | HTML 템플릿·CSS |
| `run.py`, `minishop/__init__.py` | 웹서버 실행·앱 설정 |

VM 디스크·로컬 DB·`.env`·가상환경·로그는 Git과 컨테이너 빌드 대상에서 제외합니다. 브랜치·PR 절차는 [Git 협업](docs/GIT_COLLAB.md), 요청 경로와 테이블 구조는 [웹사이트와 DB 구조](docs/STRUCTURE.md)를 참고합니다.
