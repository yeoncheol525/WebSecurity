# Git 작업 안내

저장소: https://github.com/yeoncheol525/WebSecurity

VM과 설치 이미지는 각자 준비하며, Ubuntu VM 안에서 소스를 clone합니다.
처음에는 `bash scripts/setup-ubuntu.sh`로 설치와 검증을 수행합니다.
이후에도 `git pull --ff-only` 다음 같은 명령으로 갱신합니다.

기능별 브랜치를 만들고 변경 이유와 검증 결과를 PR에 기록합니다.

```sh
git switch main
git pull --ff-only
git switch -c feature/작업이름
# 코드 수정과 검증
git add 수정한_파일
git commit -m "변경 내용"
git push -u origin feature/작업이름
```

DB 스키마 변경은 기존 볼륨에 자동 적용되지 않으므로 마이그레이션 절차를 함께 작성합니다.
`.env`·VM·DB 파일·로그·검증 결과 원본은 커밋하지 않습니다.
각자의 비밀번호는 `python3 scripts/demo_credentials.py`로 로컬에서 확인합니다.
구축 순서는 [TEAM_SETUP.md](TEAM_SETUP.md), 이전 버전과의 차이는 [MIGRATION.md](MIGRATION.md)를 참고합니다.
