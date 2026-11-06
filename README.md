# MiniShop

SQL Injection에 대한 세 가지 방어 — 쿼리 바인딩(D1), DB 최소권한(D2), 객체 인가(D3) — 의 효과를 분리 검증하는 웹 보안 실습 환경.

연구 질문: SQL Injection이 남아 있어도 DB 최소권한으로 고객·거래정보 노출을 막을 수 있는가?
VMware Host-only 격리망, 합성 데이터(고객 100 · 주문 300 · 결제 300)만 사용한다.

| 문서 | 내용 |
|---|---|
| [docs/SETUP.md](docs/SETUP.md) | VM·네트워크·설치, Burp 사용 |
| [docs/ATTACK.md](docs/ATTACK.md) | 조건별(E1~E4·A·C2) 공격·방어·판정 절차 |
| [docs/DEFENSE.md](docs/DEFENSE.md) | 방어 원리와 측정·판정 기준 |
| [docs/EXPERIMENT.md](docs/EXPERIMENT.md) | 실험 매트릭스, 지표, 결과표 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 구조와 권한 경계 |

## 빠른 시작 · Ubuntu

```sh
git clone https://github.com/yeoncheol525/WebSecurity.git minishop && cd minishop
bash scripts/setup-ubuntu.sh --bind 192.168.67.20   # 최초 E4 · Docker·시드·기동
python3 scripts/demo_credentials.py                 # 웹 로그인 계정
```

조건 전환은 `bash scripts/setup-ubuntu.sh --experiment <조건>`, 적용 조건 확인은 `/health/catalog`·`/health/orders`.

## 실험 조건

한 번에 한 조건만 실행하며 모든 조건은 같은 DB·주소·포트를 공유한다.

| 조건 | 바인딩 D1 | 최소권한 D2 | Catalog 역할 | 의미 |
|---|---|---|---|---|
| E1 | OFF | OFF | `catalog_reader_wide` | 기준선 · 유출 |
| E2 | ON | OFF | `catalog_reader_wide` | 바인딩 |
| E3 | OFF | ON | `catalog_reader` | 최소권한 · 42501 |
| E4 | ON | ON | `catalog_reader` | 이중 · 기본 |
| A | — | — | E4 기반 | 로그인 SQLi |
| C2 | — | — | E4 기반 | IDOR |

주문 소유자 검사는 E1~E4에서 유지하며, A·C2는 보조 조건이다. 절차는 [docs/ATTACK.md](docs/ATTACK.md).

## 화면과 API

| 기능 | 화면 | API |
|---|---|---|
| 상품 검색 | `/shop` | `GET /products?q=...` |
| 로그인 | `/login` | `POST /login` |
| 본인 주문 | `/account/orders` | `GET /orders`, `GET /orders/{id}` |
| 상태 | — | `GET /health/catalog`, `/health/orders` |

user1 주문 1001~1003, user2 주문 2001~2003. 검색 응답 최대 100행. 자동 탐지 규칙 미구현(탐지율·오탐률 `N/A`).

## 서버 관리 · Ubuntu

```sh
sudo docker compose ps
sudo docker compose logs --tail 30 catalog-service order-service
bash scripts/setup-ubuntu.sh --experiment E4     # 종료 후 안전 조건 복귀
sudo docker compose down
```

조건 전환은 반드시 `setup-ubuntu.sh`로 한다(`docker compose up`만으로는 조건 설정이 적용되지 않음). `.env`·DB·세션 쿠키·VM·결과는 Git에서 제외한다.

## 소스

`services/`(catalog·orders·common) · `database/`(역할·스키마·시드) · `experiments/`(조건별 compose) · `scripts/` · `tests/`
