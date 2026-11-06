# 설치와 접속

## 환경

| 구분 | 조건 |
|---|---|
| 서버 | Ubuntu 24.04 LTS amd64, Docker, Bash |
| 클라이언트 | Kali 또는 Windows, Burp Suite Community |
| 네트워크 | Host-only. Ubuntu `192.168.67.20`, Kali `192.168.67.10` (예시) |
| 포트 | HTTP `18080` |

두 VM을 같은 Host-only 네트워크에 두고, Host-only 인터페이스에는 외부 게이트웨이를 설정하지 않는다.

## 서버 설치 · Ubuntu

```sh
sudo apt-get update && sudo apt-get install -y git
git clone https://github.com/yeoncheol525/WebSecurity.git minishop
cd minishop
bash scripts/setup-ubuntu.sh --bind 192.168.67.20
```

- `--bind`: Ubuntu의 실제 Host-only 주소. 생략 시 기존 설정 유지, 첫 설치는 전용 사설 NIC 자동 선택.
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
