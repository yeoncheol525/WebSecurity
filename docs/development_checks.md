# 회귀 검사

실행 조건: Ubuntu 프로젝트 루트, E4.
실행 환경과 제공 코드의 회귀 검사이며, 팀원이 수행할 E1~E4 반복 실험과 방어 효과 분석은 별도로 기록한다.

```sh
bash scripts/setup-ubuntu.sh --experiment E4
sudo -v
python3 scripts/verify_environment.py
```

## 범위

- HTTP·DB 권한·세션·감사 로그.
- 컨테이너 재시작 후 데이터·세션 유지.
- wide 역할 일시 활성화 후 비활성화.
- 산출물: `results/`.

E4 이외의 조건에서는 검사를 시작하지 않는다.
컨테이너 재시작을 포함하므로 측정 중인 요청을 종료한 뒤 실행한다.

## 검사 도구

| 경로 | 용도 |
|---|---|
| `tests/` | 서비스·설치·인가 회귀 검사 |
| `scripts/verify_kali_client.py` | Kali 출발 HTTP·네트워크 검사 |
| `scripts/validate_vm_pair.py` | VM 간 구성 검사 |
| `tests/browser_smoke.py` | Firefox 화면 검사 |

## 2026-11-06 실행 확인

Ubuntu 24.04.5 LTS VMware VM의 별도 Compose 프로젝트와 loopback 포트 `18081`에서
E4 회귀 검사 **42/42**가 통과했다. 컨테이너 pytest 39개와 재시작·포트·감사 로그 검사 3개다.
기존 서버·DB와 분리해 검사했으며, 임시 컨테이너·네트워크·DB 볼륨은 검사 후 제거했다.
Windows에서는 설치 관련 단위 검사 15개, Python·Bash 구문과 네 조건의 Compose 설정을 확인했다.
Ubuntu에서는 E1~E4 전환 후 실제 DB 역할·query_mode·정상 검색을 확인했다.
각 전환에서 비밀번호와 시드 건수가 유지됐고, 설치가 새 결과 파일을 생성하지 않았다.
이 검사는 E1~E4 공격 성공률·노출량·지연의 반복 측정 결과를 제공하지 않는다.

실행 ID: `20261106T184611_KST`. 로컬 증거: `results/readme-final-review/`의
`summary.json`, `test_results.csv`, `junit.xml`, `host_checks.json`, `versions.json`.
정상 기동·전환 확인은 같은 폴더의 `condition-startup.json`에 기록했다.
원본 검사 결과는 Git에서 제외한다.

[기존 VM 검증 기록](validation.md) · [조건별 결과표](experiment_plan.md)
