# C2 · 객체 수준 인가 누락 (IDOR / BOLA)

보조 실험. **바인딩이 적용돼 있어도** 객체별 인가가 없으면 타인 주문에 접근된다는 점을 보인다.
쿼리 바인딩(SQLi 방어)과 객체 수준 인가가 서로 다른 통제임을 실증한다.

| 항목 | 설정 |
|---|---|
| 주문 소유자 검사 | `off` |
| 로그인 / 검색 / DB 권한 | E4와 동일(안전) |
| Catalog DB 역할 | `catalog_reader` |

## 실행 · Ubuntu

```sh
bash scripts/setup-ubuntu.sh --experiment C2
```

## 조건

- `GET /orders`, `GET /orders/<id>`에서 세션 사용자와 주문 소유자를 대조하지 않는다.
- 정상 로그인 세션 하나로 다른 사용자의 주문 목록·상세를 조회할 수 있다.
- SQL은 모두 바인딩돼 있다. 즉 이 노출은 SQLi가 아니라 인가 설계 결함이다.
- 이 조건은 `LAB_EXPERIMENTS_ENABLED=true`에서만 활성화되며 E4 기본 설치에서는 불가능하다.

## 확인·기록할 내용

[공격 가이드 §C2](../../docs/attack_guide.md#c2-idor-객체-수준-인가-누락)의 절차로 user1 세션이
user2 주문(2001~2003)을 받는지 확인하고, 소유자 검사 ON(E4/기본값)과 응답을 비교한다.

[공격 가이드](../../docs/attack_guide.md) · [방어 가이드](../../docs/defense_guide.md) · [결과 기록](../../docs/experiment_plan.md)
