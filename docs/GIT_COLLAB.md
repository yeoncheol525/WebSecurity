# Git 협업

팀원 개발 실행은 **Git clone → Docker Compose → localhost:5000**입니다. Git은 소스·문서·Compose 구성을 공유하며 VM 디스크·로컬 DB·`.env`·OS 계정 정보를 공유하지 않습니다. Ubuntu·Kali VM은 보안 실험에서 사용하는 별도 구성입니다.

## 저장소와 공유 범위

저장소는 [yeoncheol525/WebSecurity](https://github.com/yeoncheol525/WebSecurity)입니다. 팀원은 저장소에 접근할 수 있는 GitHub 계정으로 받습니다.

`git add .`를 사용해도 `/vm/`, `.env`, `.venv/`·`instance/`·로그는 제외됩니다. 커밋 전 변경 목록을 확인합니다.

## 팀원이 소스를 받는 방법

Windows에서는 Git과 Docker Desktop을 설치하고 Docker Desktop을 Linux 컨테이너 모드로 실행합니다. Linux에서는 Docker Engine과 Compose를 준비합니다. Python·Flask·SQLite는 프로젝트 실행 과정에서 준비합니다.

```powershell
git clone https://github.com/yeoncheol525/WebSecurity.git Team4_WebSecurity_Lab
cd Team4_WebSecurity_Lab
docker compose up --build
```

**http://localhost:5000** 에 접속합니다. 기본 실행은 VM·`.env`·기존 DB 없이 가능합니다. 최초 빌드에 인터넷이 필요하며, Linux에서 Docker 권한을 요구하면 `sudo`를 붙입니다. 서버 로그는 터미널에 표시되고 `Ctrl+C`로 종료합니다. 샘플 DB는 자동 생성하며 각자의 `instance/`에 보존합니다.

## 작업하고 합치는 방법

```powershell
git switch main
git pull --ff-only
git switch -c feature/product-page
```

브랜치는 로그인·주문·화면·문서 등 맡은 작업별로 만듭니다. 수정 후에는 변경 파일을 확인해 추가합니다.

```powershell
git add minishop/templates/products.html
git diff --cached
git commit -m "Update product page"
git push -u origin feature/product-page
```

GitHub에서 Pull Request를 만들고 팀원 한 명이 변경 내용과 정상 동작을 확인한 뒤 `main`에 합칩니다. 로그인은 `auth.py`, 상품·주문은 `shop.py`에 있습니다. 같은 파일을 함께 바꿀 때는 담당 함수와 병합 순서를 정합니다.

## 합친 코드를 개발 컨테이너에 반영하기

실행 중인 터미널에서 `Ctrl+C`로 종료하고 프로젝트 폴더에서 실행합니다. DB는 보존합니다.

```powershell
git switch main
git pull --ff-only
docker compose up --build
```

## DB 변경을 공유할 때

DB 파일 대신 `schema.sql`과 샘플 데이터 코드를 공유합니다. 최초 실행은 같은 사용자·상품·주문을 만들며 비밀번호 해시의 salt·세션 키는 환경마다 달라도 됩니다.

스키마를 바꾸면 초기 데이터와 적용 방법도 PR에 적습니다. 기존 DB를 자동 마이그레이션하는 기능은 아직 없습니다. 샘플 DB로 다시 만들 필요가 있으면 필요한 데이터를 보관하고 **초기화할 서버에서** 실행합니다.

DB는 실행한 프로젝트의 `instance/minishop.sqlite3`입니다. 실험용 Ubuntu VM에서는 `/opt/team4-minishop/instance/minishop.sqlite3`입니다. Compose를 중지한 뒤 해당 프로젝트 폴더에서 `sudo docker compose run --rm web python -m scripts.init_db --reset`을 실행합니다. 일반 `scripts.init_db` 실행은 기존 데이터를 보존하고, `--reset`을 명시할 때만 샘플 데이터로 교체합니다. 상세 순서는 [README](../README.md)에 있습니다.

PPT·영상은 별도 팀 공유 위치에서 한 명씩 편집하면 충돌을 줄일 수 있습니다.

공식 참고: [GitHub flow](https://docs.github.com/en/get-started/using-github/github-flow), [파일 제외](https://docs.github.com/en/get-started/git-basics/ignoring-files).
