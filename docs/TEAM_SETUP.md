# 설치와 접속

## 환경

| 구분 | 조건 |
|---|---|
| 서버 | Ubuntu 24.04 LTS amd64, Python 3, Bash |
| 클라이언트 | Kali Desktop 또는 Windows, Burp Suite Community Edition |
| 네트워크 | Ubuntu의 Host-only 주소에 접근 가능 |
| 기본 포트 | HTTP 18080 |

Kali VM 사용 시 Ubuntu와 같은 Host-only 네트워크에 연결한다.
IP 예시: Ubuntu `192.168.67.20/24`, Kali `192.168.67.10/24`.
Host-only 인터페이스에는 외부 기본 게이트웨이를 설정하지 않는다.
VMware 구성은 [VM 설정](vm_setup.md)을 따른다.

## Ubuntu 서버 설치

처음 소스를 받는 Ubuntu에서 실행한다. GitHub 접근 권한·인증, 인터넷 연결과 sudo 권한이 필요하다.

```sh
sudo apt-get update
sudo apt-get install -y git
git clone https://github.com/yeoncheol525/WebSecurity.git minishop
cd minishop
```

이미 소스를 받았다면 `docker-compose.yml`이 있는 프로젝트 루트에서 다음 명령부터 실행한다.

```sh
bash scripts/setup-ubuntu.sh --bind 192.168.67.20
```

- `--bind`: Ubuntu에 할당된 실제 Host-only 주소.
- `--local`: 서버 내부 접속용 loopback.
- 주소 생략: 기존 설정 유지. 첫 설치는 전용 사설 NIC 자동 선택, 후보가 없으면 loopback, 여럿이면 `--bind` 필요.
- 설치 중 비밀번호: Ubuntu 사용자의 sudo 비밀번호.
- 앱 Python 패키지와 PostgreSQL: Docker 컨테이너 내부 설치.
- 첫 실행: E4. 이후 실행: 저장된 조건 유지.
- 기존 `.env`와 DB 유지.

서비스 healthcheck 후 설치가 끝난다. 실험·결과 집계는 팀원이 직접 수행하며,
개발 회귀 검사는 [별도 절차](dev/development_checks.md)로 실행한다.

## 웹 계정 확인 · Ubuntu

```sh
python3 scripts/demo_credentials.py
```

## 브라우저 접속 · Kali Desktop / Windows

1. 앱 목록 또는 시작 메뉴에서 **Burp Suite**를 실행한다.
2. **Proxy → Intercept → Intercept off → Open browser**로 내장 브라우저를 연다.
3. `http://192.168.67.20:18080/shop`에 접속한다.
4. 검색창에 `Notebook`을 입력하고 **검색**을 누른다.
5. **Proxy → HTTP history**에서 `/products?q=Notebook`의 요청과 응답을 확인한다.
6. **로그인**에 웹 계정을 입력한 뒤 **내 주문 → 상세 보기**를 연다.

주소의 IP는 실제 Ubuntu Host-only 주소로 바꾼다.
설치·요청 기록·정상 요청 재전송은 [Burp 사용 순서](../README.md#브라우저-사용--kali-desktop--windows)를 따른다.

## 조건 선택 · Ubuntu

```sh
bash scripts/setup-ubuntu.sh --experiment E1
```

허용값: 메인 `E1`, `E2`, `E3`, `E4`와 보조 `A`(로그인 SQLi), `C2`(IDOR).
조건 변경 후 브라우저에서 같은 주소를 새로고침한다.
동시에 한 조건만 실행하며 같은 DB·주소·포트를 재사용한다.
네 조건은 같은 사이트의 설정이다. 전환 후 `/health/catalog`의 `database_role`과 `query_mode`를 확인한다.
기동·전환은 설치 스크립트로 수행한다. `docker compose up`만으로는 저장된 조건 설정이 적용되지 않는다.

종료 후 기본 방어 조건 복귀:

```sh
bash scripts/setup-ubuntu.sh --experiment E4
```

서비스 종료:

```sh
sudo docker compose down
```

기존 PostgreSQL 볼륨에는 초기화 SQL 변경이 자동 적용되지 않는다.
스키마·권한 변경은 별도 마이그레이션으로 적용한다.

[실행 조건](../README.md) · [결과 기록](experiment_plan.md) · [검증](dev/development_checks.md)
