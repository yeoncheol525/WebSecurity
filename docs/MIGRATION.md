# 기존 SQLite 버전에서 업데이트

이전 소스와 Git 이력은 `archive/sqlite-v1` 브랜치에 보존합니다.
새 main은 기존 MiniShop HTML/CSS 화면을 PostgreSQL 기반 서비스에 연결한 버전입니다.

| 항목 | 이전 버전 | 새 버전 |
|---|---|---|
| DB | SQLite, `instance/` | PostgreSQL 전용 Docker 볼륨 |
| 실행 | Flask 단일 앱 | Nginx + Catalog + Orders + PostgreSQL |
| Docker 프로젝트 | `team4-websecurity` | `minishop` |
| 웹 포트 | 5000 | 18080 |
| 설정 | `WEB_PORT`가 있는 `.env` | `HTTP_PORT`와 DB별 비밀번호가 있는 `.env` |
| 웹 계정 | 공통 고정 비밀번호 | 각 설치마다 새로 생성된 비밀번호 |

## 이미 clone한 팀원

Ubuntu VM의 기존 저장소에서 작업합니다. 수정한 파일이 있다면 먼저 개인 브랜치에 보존합니다.

```sh
git status
git switch main
git pull --ff-only
bash scripts/setup-ubuntu.sh
python3 scripts/demo_credentials.py
```

설치 스크립트는 이전 SQLite `.env`를 `.env.sqlite-backup`으로 옮긴 뒤 새 비밀값을 생성합니다.
같은 이름의 백업 파일이 이미 있으면 덮어쓰지 않고 중단합니다.
`instance/`와 이전 컨테이너/볼륨을 삭제하지 않습니다. 새 PostgreSQL에는 합성 시드를 넣으며,
기존 SQLite의 고객·주문 데이터를 자동 이관하지 않습니다.
이미 새 PostgreSQL 구성을 사용 중이었다면 기존 `.env`와 PostgreSQL 볼륨을 그대로 사용합니다.

기존 5000번 컨테이너는 자동으로 종료하지 않습니다. 이전 실험이 끝났다면 해당 컨테이너를 확인한 뒤
직접 정지할 수 있습니다. 새 구성은 다른 프로젝트 이름과 포트를 사용합니다.

## 이전 소스가 필요할 때

현재 실행 폴더에서 브랜치를 바꾸기보다는 별도 폴더에 이전 버전을 받습니다.

```sh
git clone --branch archive/sqlite-v1 --single-branch https://github.com/yeoncheol525/WebSecurity.git minishop-sqlite-v1
```

새 `.env`를 이전 버전에 복사하지 않습니다. 이전 버전의 실행 방법은 해당 브랜치 README에 있습니다.

## 공유하지 않는 파일

`.env`, `.env.sqlite-backup`, `instance/`, `results/`, VM 디스크, 설치 이미지는 로컬 전용입니다.
Git에는 `docker-compose.yml`·서비스 소스·DB 초기화/시드·설치 스크립트·문서만 공유합니다.
상위 `minishop/` 안의 `project/`가 저장소 루트이며 `vms/`나 `downloads/` 전체를 올리지 않습니다.
