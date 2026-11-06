# 실제 VM 검증 기록 · E1~E4 분리 이전 버전

아래는 이전 코드의 실행 이력이다. 현재 설치는 검증을 실행하지 않는다.
별도 개발 검사 방법은 [development_checks.md](development_checks.md),
조건별 결과 기록은 [experiment_plan.md](experiment_plan.md)를 따른다.

검증일: **2026-11-05 KST**. Ubuntu 실행 ID: `20261105T195804_KST`.
**Ubuntu VM 32/32, Kali API 8/8, Kali Firefox 화면 8/8 검증을 통과**했다.
Docker가 없는 별도 새 Ubuntu VM에서도 한 명령으로 설치와 32/32 검증을 통과했다.
Windows Docker는 서버 실행이나 이 검증에 사용하지 않았다.

## 실행 환경

| 항목 | 실제 값 |
|---|---|
| 서버 VM | Ubuntu 24.04.5 LTS, VMware, 사용자 lab |
| 서버 소스 | /home/lab/minishop |
| 공격자 VM | Kali 2026.3, VMware |
| 네트워크 | Kali 192.168.67.10 → VMnet1 Host-only → Ubuntu 192.168.67.20:18080 |
| Ubuntu Docker / Compose | 29.9.2 / 5.6.1 |
| 관리용 / 컨테이너 Python | 3.12.3 / 3.13.18 |
| Flask / Psycopg / Gunicorn | 3.1.3 / 3.3.8 / 26.2.0 |
| PostgreSQL / Nginx | 17.11 / 1.30.6 |

VMware Ubuntu에는 기존 Docker가 설치돼 있었으며 기존 웹서비스의 NAT 5000 연결을 보존했다.
MiniShop에는 별도 Host-only NIC와 Docker 프로젝트를 사용했다.
Kali의 NAT는 끊고 자동 연결을 비활성화했다. 서비스에 보내는 TCP의 실제 출발지 192.168.67.10을 확인했다.

## Ubuntu에서 T01~T12

`python3 scripts/verify_environment.py --no-build` 실제 실행:
컨테이너 pytest 29개와 호스트 재시작·미공개 포트·로그 검사 3개를 합쳐 **32/32 PASS**이다.

| ID | 실제 관측 | 판정 |
|---|---|---|
| T01 | Nginx 경유 Catalog 200, 역할 catalog_reader, 공개 상품 12개 | PASS |
| T02 | Nginx 경유 Orders 200, 역할 order_service | PASS |
| T03 | 실제 catalog_reader로 공개 상품 SELECT 12개, 비공개 0개 | PASS |
| T04 | private.customers SELECT 거부, SQLSTATE 42501 | PASS |
| T05 | orders·users·payment_meta SELECT 각각 권한 거부 | PASS |
| T06 | 주문 역할의 정상 조회, 불필요한 고객 PII·결제 접근 거부 | PASS |
| T07 | user1/user2 로그인·본인 주문 조회 정상 | PASS |
| T08 | user1의 user2 주문 2002 조회 404, 미존재와 같은 응답 | PASS |
| T09 | 익명 주문 목록·상세 401 | PASS |
| T10 | 컨테이너 4개 재시작 후 세션·주문·시드 100/300/300 유지 | PASS |
| T11 | DB·앱 포트 미공개, Ubuntu 호스트에서 5432 접속 실패 | PASS |
| T12 | wide 계정 SELECT 추가 권한 확인 후 NOLOGIN·기본 역할 복귀 | PASS |

추가로 역할 속성·상속·PUBLIC DDL/TEMP, 쓰기 거부, 일반 작은따옴표 검색, 비공개 상품,
request_id, 로그인 실패, JSON·Origin·CSRF, 로그아웃 후 복사 쿠키 거부, 로그 필드·비밀값 마스킹을 검사했다.
환경 기록에는 실제 Linux 배포판과 `systemd-detect-virt=vmware`를 저장한다.

추가한 설치/화면 검사 8개는 설정 재사용·기존 SQLite 파일 보존·불완전한 설정 보존·IP만 변경할 때
비밀번호 유지·NAT/가상 NIC 자동 선택 제외·HTML/정적 파일·기존 브라우저 URL 호환·세션/CSRF 쿠키를 확인한다.
갱신 시 바인드 마운트의 Nginx 설정이 기존 프로세스에 남는 문제를 발견해,
설치 스크립트가 프록시를 재생성한 뒤 검증하도록 수정했다.

## Kali에서 K01~K08

Kali 192.168.67.10에서 `python3 /home/kali/verify_minishop.py`를 실행했다.
테스트용 웹 비밀번호만 프로세스 stdin으로 전달했고, DB 비밀번호는 Kali에 전달하지 않았다.

| ID | 실제 관측 | 판정 |
|---|---|---|
| K01 | Ubuntu 상품 API 200, 공개 상품 12개 | PASS |
| K02 | Catalog/Orders health 200, 제한된 DB 역할·bound SQL | PASS |
| K03 | 익명 주문 조회 401 | PASS |
| K04 | user1 본인 주문 200, 타인 주문 404 | PASS |
| K05 | user2 본인 주문 200, 타인 주문 404 | PASS |
| K06 | Ubuntu 5432와 8000 직접 TCP 접속 실패 | PASS |
| K07 | eth1·192.168.67.10 경로 사용, Kali 기본 인터넷 경로 없음 | PASS |
| K08 | 실제 HTTP TCP 출발지 192.168.67.10 확인 | PASS |

## Kali Firefox 실제 화면 검사

Kali의 Firefox 140.15.0을 geckodriver로 실행했다. 서버 응답만 검사한 결과와 별도이다.

| ID | 실제 관측 | 판정 |
|---|---|---|
| B01 | 기존 홈 화면과 쇼핑백 일러스트 표시 | PASS |
| B02 | 상품 API를 받아 상품 카드 12개 렌더링 | PASS |
| B03 | O'Reilly 일반 검색 결과 1개 | PASS |
| B04 | 잘못된 비밀번호 오류 표시 | PASS |
| B05 | user1 로그인 후 본인 주문 1001~1003 표시 | PASS |
| B06 | 본인 주문 상세 표시 | PASS |
| B07 | 타인 주문 2002는 오류 표시, 상세 데이터는 숨김 | PASS |
| B08 | 로그아웃 후 홈과 로그인 버튼 표시 | PASS |

소스는 `tests/browser_smoke.py`이다. 별도 선택 검사이므로 기본 설치에 Firefox를 설치하지 않는다.
Kali에서 캡처한 화면은 로컬 `results/renewal/kali-ui.png`에 보관한다.

## Docker 없는 새 Ubuntu에서 처음 설치

공식 Ubuntu 24.04 LTS cloud image의 SHA-256을 확인한 임시 VMware VM을 사용했다.
처음에 Docker 명령이 없고 사용자도 Docker 그룹에 없는 상태를 확인했다.
이 VM의 sudo는 비대화형 검증을 위해 NOPASSWD로 설정했으며,
일반 설치 환경에서는 Ubuntu 계정의 sudo 비밀번호를 입력한다.

`bash scripts/setup-ubuntu.sh` 한 명령으로 공식 apt 저장소에서 Docker 29.9.3·Compose 5.7.0을 설치하고,
전용 NIC의 192.168.67.21을 자동 선택해 32/32 검증을 통과했다.
다시 실행했을 때 `.env`의 SHA-256이 같았고 시드 건수도 100/300/300으로 유지됐다.
임시 VM은 프로젝트의 무시된 `results/bootstrap-cleanvm/`에만 보관하며 소스 배포에는 포함하지 않는다.

## 증거

- Ubuntu: `/home/lab/minishop/results/20261105T195804_KST/`의 JUnit XML·CSV·호스트 검사·버전·감사 로그.
- `results/renewal/ubuntu-summary.json`: 현재 Ubuntu 검증 요약.
- `results/renewal/kali-api.json`: Kali API 결과·출발지·대상·시각.
- `results/renewal/kali-browser.json`, `kali-ui.png`: 실제 Firefox 검사와 캡처.
- `results/bootstrap-cleanvm/acceptance.json`, `first-install.log`: Docker 없는 새 Ubuntu의 설치·재실행 결과.
- `results/vm/machines.json`: VM 경로. 변경 전 VMX도 같은 폴더에 백업.
- `Downloads/minishop/downloads/kali-image/kali-image-source.json`: 공식 이미지 SHA-256 검증.

## 남은 범위

SQLi 취약 쿼리·공격 코드, E1~E4 반복 공격 실험, 탐지율·응답 p95 연구는 환경 검증 범위에 포함하지 않는다.
Kali의 Burp/sqlmap/Firefox는 설치 경로만 확인했다. SQLi 공격 성공은 해당 검증의 대상에 포함하지 않았다.

검증 결과는 위 표에 명시한 검사 항목에 한정한다.
