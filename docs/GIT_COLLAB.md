# Git 작업

저장소: https://github.com/yeoncheol525/WebSecurity

작업 위치: `docker-compose.yml`이 있는 프로젝트 루트.
Windows 작업 폴더 기준: `minishop/project/`.

## 기능 브랜치

커밋하지 않은 변경이 없는 상태에서 실행한다.

```sh
git switch main
git pull --ff-only
git switch -c feature/작업이름
```

수정과 검증 후 필요한 파일만 선택한다.

```sh
git add 수정한_파일
git commit -m "변경 내용"
git push -u origin feature/작업이름
```

GitHub에서 Pull Request를 열고 변경 목적·검증 결과·DB 적용 절차를 기록한다.
리뷰 후 `main`에 병합하고, 병합이 확인된 작업 브랜치를 정리한다.

## 갱신 · Ubuntu

```sh
git pull --ff-only
bash scripts/setup-ubuntu.sh
```

## 제외 파일

`.env`, VM, DB, 설치 이미지, 로그, 원본 결과.
DB 스키마 변경 시 기존 볼륨에 적용할 마이그레이션 절차를 포함한다.

[설치](TEAM_SETUP.md) · [기존 버전 갱신](MIGRATION.md)
