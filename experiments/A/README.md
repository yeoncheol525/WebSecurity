# A · 로그인 SQL Injection (인증 우회)

보조 실험. 검색(E1~E4)과 독립적으로 **로그인 인증 우회**만 재현한다.

| 항목 | 설정 |
|---|---|
| 로그인 쿼리 | `interpolated` (문자열 결합) |
| 검색 바인딩 / DB 권한 | E4와 동일(안전) |
| 주문 소유자 검사 | ON 유지 |
| Catalog DB 역할 | `catalog_reader` |

## 실행 · Ubuntu

```sh
bash scripts/setup-ubuntu.sh --experiment A
```

## 조건

- `POST /login`의 `username`이 SQL 문자열에 직접 결합된다.
- 행이 반환되면 비밀번호 해시 검증 없이 인증된 것으로 처리한다(레거시 결함).
- 검색·DB 권한·주문 소유자 검사는 안전한 기본값을 유지한다.
- 이 조건은 `LAB_EXPERIMENTS_ENABLED=true`에서만 활성화되며 E4 기본 설치에서는 불가능하다.

## 확인·기록할 내용

[공격 가이드 §A](../../docs/attack_guide.md#a-로그인-sql-injection)의 절차로 비밀번호 없이
세션이 발급되고 보호 API에 접근되는지 확인한다. 방어(바인딩) 적용은 E4(또는 기본값)와 비교한다.

[공격 가이드](../../docs/attack_guide.md) · [방어 가이드](../../docs/defense_guide.md) · [결과 기록](../../docs/experiment_plan.md)
