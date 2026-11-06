# 설치와 접속

## 환경

| 구분 | 조건 |
|---|---|
| 서버 | Ubuntu 24.04 LTS amd64, Docker, Bash |
| 클라이언트 | Kali 또는 Windows, Burp Suite Community |
| 네트워크 | 어댑터 2개 — NAT(설치용 인터넷) + Host-only(실험망). Ubuntu `192.168.67.20`, Kali `192.168.67.10` (예시) |
| 포트 | HTTP `18080` |

## VM 네트워크 설정

각 VM(Ubuntu 서버, Kali 공격자)에 네트워크 어댑터를 2개 둔다.

| 어댑터 | 용도 | 비고 |
|---|---|---|
| NAT | 인터넷 — apt·Docker 설치, 이미지 다운로드 | 설치 단계에만 필요 |
| Host-only | Kali ↔ Ubuntu 격리 실험망 | 공격·측정에 사용, 외부 비노출 |

- Host-only 망은 `192.168.67.0/24`(예시)로 만들고 외부 게이트웨이를 설정하지 않는다. 고정 IP로 Ubuntu `192.168.67.20`, Kali `192.168.67.10`을 둔다. 다른 대역을 쓰면 이후 명령의 주소도 함께 바꾼다.
- VMware: VM 설정 → 네트워크 어댑터에서 하나는 NAT, 다른 하나는 Host-only(또는 사용자 지정 VMnet)로 추가한다. Host-only 서브넷은 Edit → Virtual Network Editor에서 지정한다.
- VirtualBox: 설정 → 네트워크 → 어댑터 1 = NAT, 어댑터 2 = 호스트 전용 어댑터. Host-only 망은 도구 → 네트워크 관리자에서 먼저 생성한다.
- 확인: Ubuntu에서 `ip addr`로 Host-only IP를, `ping 192.168.67.10`으로 Kali 연결을, `ping 8.8.8.8`로 인터넷(NAT)을 확인한다.
- 측정 단계에서 완전 격리를 보이려면 설치·이미지 다운로드를 마친 뒤 NAT 어댑터를 비활성화한다(선택).

## 서버 설치 · Ubuntu

```sh
sudo apt-get update && sudo apt-get install -y git
git clone https://github.com/yeoncheol525/WebSecurity.git minishop
cd minishop
bash scripts/setup-ubuntu.sh --bind 192.168.67.20   # 본인 Host-only IP로 교체, 또는 생략해 자동 선택
```

- `--bind`: 이 Ubuntu VM의 Host-only 주소. `ip addr`로 확인해 넣는다. 생략하면 기본 경로(NAT)를 제외한 사설 NIC(Host-only)를 자동 선택하며, 후보가 여럿이면 안내한다. 지정한 주소가 이 VM에 없으면 설치를 거부한다.
- `--local`: Host-only 어댑터 없이 단일 VM에서 loopback(`127.0.0.1`)으로만 기동할 때 사용한다. Kali에서 접속할 수 없으므로 기능 확인용이다.
- 최초 실행 조건은 E4. Docker 설치·합성 시드·서비스 기동·healthcheck까지 수행하며 기존 DB·비밀번호는 유지한다.
- 웹 계정 확인: `python3 scripts/demo_credentials.py`.

## 조건 전환 · Ubuntu

```sh
bash scripts/setup-ubuntu.sh --experiment E1   # E1~E4, A, C2
```

전환 후 `/health/catalog`의 `database_role`·`query_mode`, `/health/orders`의 `ownership_enforced`·`login_sql_mode`로 실제 조건을 확인한다. DB·비밀번호·결과는 전환 시 초기화되지 않는다.

## 회귀 검사 · Ubuntu (선택)

환경과 제공 코드가 정상인지 확인하는 검사이며, E1~E4 반복 실험·방어 효과 측정과는 별개다. **E4에서만** 실행한다.

```sh
bash scripts/setup-ubuntu.sh --experiment E4
python3 scripts/verify_environment.py          # HTTP·DB 권한·세션·감사 로그, 재시작 후 데이터 유지
```

컨테이너 재시작을 포함하므로 측정 중인 요청을 끝낸 뒤 실행한다. 산출물은 `results/`에 남으며 Git에서 제외한다. Kali 출발 검사는 `scripts/verify_kali_client.py`, 화면 검사는 `tests/browser_smoke.py`로 수행한다.

## Burp Suite 사용 · Kali / Windows

1. Burp 실행 → **Proxy → Intercept off → Open browser**.
2. `http://192.168.67.20:18080/shop`에서 검색 → **Proxy → HTTP history**에서 `/products` 요청의 상태코드·응답 본문·`X-Request-ID` 확인.
3. 요청 우클릭 → **Send to Repeater** → **Send**로 같은 요청을 반복 전송.
4. 로그인 후 **내 주문 → 상세 보기**로 주문 API 요청 관찰.

화면은 `/shop?q=...`, 상품 API는 `/products?q=...`. `localhost`는 서버 주소가 아니다. curl로도 동일하게 요청할 수 있다(응답 헤더 확인: `curl -D - ...`).

## Git

작업 위치는 `docker-compose.yml`이 있는 프로젝트 루트다.

```sh
git switch -c feature/<작업명>   # 기능 브랜치
git add -A && git commit -m "<요약>"
git push -u origin feature/<작업명>
```

`.env`·DB·VM·설치 이미지·`results/`는 커밋하지 않는다.
