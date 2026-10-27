# Team 4 · MiniShop 개발 환경

프로젝트 소스와 Docker 실행 설정을 Git으로 공유합니다. 웹사이트는 홈, 로그인·로그아웃, 상품 검색, 본인 주문 조회와 샘플 SQLite DB를 제공합니다.

## 팀원이 GitHub에서 받아 실행하기

Windows에서는 [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/)을 최초 한 번 설치하고 **Linux 컨테이너 모드로 실행**합니다. Git도 준비합니다. Linux에서는 Docker Engine과 Compose를 준비합니다. 프로젝트용 Python·Flask·DB는 아래 명령이 준비합니다.

프로젝트를 받아 실행합니다.

```powershell
git clone https://github.com/yeoncheol525/WebSecurity.git Team4_WebSecurity_Lab
cd Team4_WebSecurity_Lab
docker compose up --build
```

웹서버가 시작되면 **http://localhost:5000** 을 엽니다. 기본 실행에는 `.env` 작성, Python 설치, DB 파일 전달이나 VMware VM 준비가 필요하지 않습니다. 최초 빌드에는 Python 이미지·패키지를 받을 인터넷 연결이 필요합니다. Linux에서 Docker 접근 권한을 요구하면 `sudo docker compose up --build`를 사용합니다.

명령을 실행한 터미널에 서버 로그가 표시됩니다. **종료는 `Ctrl+C`** 입니다. DB는 프로젝트의 `instance/`에 남아 다음 실행에도 유지됩니다.

## Docker가 준비하는 것

| 파일 | 역할 |
|---|---|
| `Dockerfile` | 프로젝트 코드·Python 3.12·필요 패키지로 실행 이미지 생성 |
| `compose.yaml` | 웹 컨테이너 실행, 5000번 포트 연결, DB 폴더 보존 |
| `.dockerignore` | VM·개인 설정·기존 DB 등을 이미지 빌드에서 제외 |
| `requirements.txt` | Python 패키지 버전 지정 |

첫 실행에 앱이 테이블·샘플 사용자·상품·주문과 세션 키를 자동 생성합니다. SQLite를 사용하므로 별도 DB 서버 설치는 필요하지 않습니다. 생성되는 `instance/`와 `.env`는 Git에서 제외됩니다.

## 샘플 웹 계정

| 사용자 | 비밀번호 | 본인 주문 |
|---|---|---|
| user1 | `User1-Lab!2026` | #1001 · Keyboard |
| user2 | `User2-Lab!2026` | #2002 · Laptop |

모든 데이터는 프로젝트용 합성 자료입니다. DB 파일 대신 `minishop/schema.sql`과 `minishop/db.py`를 공유해 각자 같은 샘플 데이터를 만듭니다.

## 코드를 수정하거나 최신 코드를 받을 때

실행 중이면 `Ctrl+C`로 종료하고 프로젝트 폴더에서 실행합니다.

```powershell
git pull --ff-only
docker compose up --build
```

컨테이너에는 빌드 시점의 코드가 들어갑니다. 직접 수정한 코드도 같은 명령으로 다시 빌드해 반영합니다. 기존 DB는 보존됩니다.

5000번 포트를 이미 사용 중이면 `.env.example`을 `.env`로 복사하고 `WEB_PORT=5001`로 바꿉니다. 이후 같은 명령으로 실행하고 `http://localhost:5001`에 접속합니다. 기본 실행에는 이 설정이 필요하지 않습니다.

## DB를 샘플 상태로 되돌릴 때

기존 DB를 샘플 데이터로 교체할 때만 프로젝트 폴더에서 실행합니다.

```powershell
docker compose down
docker compose run --rm web python -m scripts.init_db --reset
docker compose up --build
```

일반 실행은 기존 데이터를 보존합니다. 스키마 변경을 기존 DB에 자동 적용하는 마이그레이션 기능은 아직 없습니다.

## 구현할 파일

| 파일 | 담당 내용 |
|---|---|
| `minishop/auth.py` | 로그인·로그아웃·현재 사용자 |
| `minishop/shop.py` | 상품 검색·주문 조회 |
| `minishop/db.py`, `schema.sql` | DB 연결·테이블·샘플 데이터 |
| `minishop/templates/` | HTML 화면 |
| `minishop/static/style.css` | 화면 디자인 |
| `run.py`, `minishop/__init__.py` | 웹서버 실행·앱 설정 |

Git 업로드·브랜치·병합 절차는 [GIT_COLLAB.md](docs/GIT_COLLAB.md), 웹 요청과 DB 구조는 [STRUCTURE.md](docs/STRUCTURE.md)에 있습니다.

## 보안 실험에서 Ubuntu·Kali VM을 사용할 때

실험은 **Kali → Ubuntu Docker** 흐름이며, VM은 VMware에서 직접 엽니다. 소스를 Ubuntu로 복사한 뒤 VM의 `.env`에 `BIND_ADDRESS`를 Host-only 주소로 지정하고 `sudo docker compose up --build`로 실행하며, `vm/` 전체는 Git과 Docker 이미지에서 제외합니다.
