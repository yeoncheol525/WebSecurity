# 아키텍처와 권한 경계

```text
Kali(Browser·Burp·sqlmap)  →  Ubuntu :18080
  192.168.67.10                 Nginx  →  Catalog(Flask)  →  PostgreSQL
                                       →  Orders(Flask)   →
```

프론트는 브라우저의 HTML 템플릿과 `app.js`(API 호출)이고, 백엔드는 Flask 두 서비스와 PostgreSQL이다. 취약점과 방어는 모두 백엔드에 있으며, 공격은 프론트를 거치지 않고 API에 직접 전송된다.

## 네트워크

| 네트워크 | 서비스 | 외부 경로 |
|---|---|---|
| edge | Nginx | Host-only 주소의 HTTP 포트 하나만 공개 |
| web (internal) | Nginx·Catalog·Orders | 앱 포트 비공개 |
| database (internal) | PostgreSQL·Catalog·Orders | DB 포트 비공개 |

## DB 권한

- 테이블/뷰 소유자는 `minishop_owner`(NOLOGIN). 앱 역할은 소유자·상속 멤버가 아니다.
- `catalog_reader`: `catalog.public_products` SELECT만. `private`/`auth` 접근 없음.
- `catalog_reader_wide`: 실험용으로 `private` 테이블 SELECT까지 허용(E1·E2).
- `order_service`: 로그인·본인 주문 처리에 필요한 접근만. 고객 테이블은 `(id, user_id)` 열로 제한.
- 공개 상품은 security_barrier 뷰 + RLS로 공개 행만 반환한다.

| 스키마 | 테이블 |
|---|---|
| catalog | products, public_products(뷰) |
| private | customers, orders, payment_meta |
| auth | users, sessions |

## 보안 설정

- 앱·Nginx는 비root, 루트 파일시스템 읽기 전용, `/tmp` tmpfs, capability 제거로 실행.
- PostgreSQL은 외부 포트를 공개하지 않는다.
- 인증은 저장된 비밀번호 해시(PBKDF2-SHA256) 검증 후에만 세션을 만든다. 로그인은 JSON·동일 출처, 로그아웃은 CSRF 토큰을 검사한다.
- 세션 쿠키 원문은 저장하지 않고 해시만 보관한다.
- Nginx가 요청별 `X-Request-ID`를 발급해 앱 로그·응답에 전달한다. SQL 로그는 템플릿·파라미터 수·타입만 남기고 값은 마스킹한다. 실험 모드의 문자열 삽입 검색만 `binding=interpolated`로 기록한다.
