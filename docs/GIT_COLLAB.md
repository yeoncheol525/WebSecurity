# Git 협업

## 저장소와 실행 환경

저장소: [yeoncheol525/WebSecurity](https://github.com/yeoncheol525/WebSecurity)

소스·문서·Docker 실행 구성을 Git으로 관리합니다. 실행 환경은 **Ubuntu VM 안의 Docker**이며, 최초 설치와 실행 절차는 [README](../README.md#빠른-시작)를 참고합니다. Git 명령은 소스를 관리할 Ubuntu의 프로젝트 폴더에서 실행합니다.

VM 디스크·로컬 DB·`.env`·OS 계정·SSH 키는 공유 대상이 아닙니다. `/vm/`, `/instance/`, `.env`, 가상환경, 로그 등은 `.gitignore`에서 제외합니다. 커밋 전에 `git status`와 `git diff --cached`로 실제 포함 파일을 확인합니다.

호스트와 VM에 각각 복제한 저장소는 별개의 작업 폴더입니다. 한쪽 파일의 수정은 다른 쪽에 자동 반영되지 않으며 커밋·푸시·풀 또는 명시적인 파일 복사가 필요합니다.

## 브랜치와 Pull Request

변경 사항이 없는 `main`에서 최신 커밋을 받고 작업 브랜치를 생성합니다.

```bash
git switch main
git pull --ff-only
git switch -c feature/product-page
```

수정 후 필요한 파일을 추가하고 커밋합니다.

```bash
git add minishop/templates/products.html
git diff --cached
git commit -m "Update product page"
git push -u origin feature/product-page
```

GitHub에서 Pull Request를 생성하고 리뷰와 동작 확인 후 `main`에 병합합니다. PR에는 변경 목적, 실행 결과, DB나 환경 설정 변경 여부를 기록합니다. 같은 파일을 동시에 수정할 경우 담당 함수와 병합 순서를 조정합니다.

## 변경 사항 실행

실행 중인 서버를 `Ctrl+C`로 중지한 뒤 프로젝트 폴더에서 실행합니다.

```bash
git switch main
git pull --ff-only
bash scripts/setup-ubuntu.sh
```

설치된 Docker를 재사용하고 최신 코드로 이미지를 빌드합니다. 직접 수정한 코드도 재빌드해야 컨테이너에 반영됩니다. DB와 `.env`는 유지됩니다.

## 데이터베이스 변경

DB 파일 대신 `minishop/schema.sql`과 `minishop/db.py`의 초기 데이터 코드를 공유합니다. 각 실행 환경은 동일한 샘플 계정·상품·주문을 생성하고, 비밀번호 해시의 salt와 세션 키는 개별적으로 생성합니다.

스키마 변경 PR에는 초기 데이터와 기존 DB 적용 방법을 함께 기록합니다. 기존 DB를 자동 마이그레이션하는 기능은 없습니다. 샘플 상태로 초기화해야 하는 경우 [README의 초기화 절차](../README.md#샘플-데이터-초기화)를 사용합니다. `--reset`은 실행 대상 프로젝트의 기존 데이터를 샘플 데이터로 교체합니다.

공식 참고: [GitHub flow](https://docs.github.com/en/get-started/using-github/github-flow), [파일 제외](https://docs.github.com/en/get-started/git-basics/ignoring-files).
