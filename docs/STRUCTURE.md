# 웹사이트와 DB 구조

## 요청 경로

| 요청 | 기본 동작 | 주요 파일 |
|---|---|---|
| `GET /` | 홈 | `shop.py` |
| `GET /login` | 로그인 폼 | `auth.py` |
| `POST /login` | 계정 확인 후 세션 생성 | `auth.py` |
| `POST /logout` | 세션 종료 | `auth.py` |
| `GET /products?keyword=...` | 공개 상품 검색 | `shop.py` |
| `GET /orders?order_id=...` | 로그인 사용자의 주문 목록·검색 | `shop.py` |
| `GET /orders/<id>` | 로그인 사용자의 주문 상세 | `shop.py` |
| `GET /health` | 앱·DB 상태 JSON | `__init__.py` |

화면은 서버가 Jinja 템플릿을 HTML로 만들어 반환합니다. CSS는 `static/style.css`에서 제공합니다. 별도의 프런트엔드 빌드 도구나 Node.js는 필요하지 않습니다.

## 테이블

| 테이블 | 컬럼 |
|---|---|
| `users` | `id`, `username`, `password_hash` |
| `products` | `id`, `name`, `price`, `is_public` |
| `orders` | `id`, `user_id`, `product_id`, `quantity` |

`orders.user_id`는 `users.id`, `orders.product_id`는 `products.id`를 참조합니다. DB 연결 시 외래 키 검사를 켭니다.

DB 파일은 `instance/minishop.sqlite3`입니다. 스키마와 샘플 데이터는 Git으로 관리하고, DB 파일은 각자 생성합니다. 앱 생성은 기존 테이블이 있으면 데이터를 그대로 사용합니다. 테이블 구조를 바꾸는 작업은 초기화 또는 별도 마이그레이션을 팀에서 결정해야 합니다.

## 현재 구현 범위

일반 웹사이트를 실행하는 최소 로그인·조회 기능, DB, 화면과 Docker Compose 구성을 제공합니다. SQL은 값 바인딩을 사용하고 주문은 현재 사용자 범위로 조회합니다. 이는 기본 서비스 동작이며, 공격·방어 전후 실험을 구현한 상태는 아닙니다.

이후 팀이 구현할 시나리오·관측 지점·방어 비교는 별도 작업으로 설계하고 추가합니다.
