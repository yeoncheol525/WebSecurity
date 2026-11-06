# E4 · 바인딩 + 최소 권한

| 항목 | 설정 |
|---|---|
| 검색 바인딩 | ON |
| DB 최소 권한 | ON |
| SQL_QUERY_MODE | `bound` |
| Catalog DB 역할 | `catalog_reader` |

## 실행 · Ubuntu

프로젝트 루트에서 실행한다.

```sh
bash scripts/setup-ubuntu.sh --experiment E4
```

## 조건

- 최초 설치의 기본 조건.
- 검색값을 SQL 템플릿과 별도 인자로 전달.
- Catalog의 DB 접근을 최소 권한 역할로 제한.
- 로그인·주문 소유자 검사 유지.
- E2와의 비교 요소: DB 권한.
- E3과의 비교 요소: 검색 바인딩.

## 직접 비교·기록할 내용

같은 입력·반복 횟수로 네 조건의 결과표를 완성하고, 정상 검색·로그인·본인 주문 유지 여부를 확인한다.
바인딩 효과는 E2/E1·E4/E3, 최소 권한 효과는 E3/E1·E4/E2 비교를 근거로 설명한다. 회귀 검사 결과와 실험 측정값을 구분한다.

## 관련 파일

- `services/catalog/app/__init__.py`
- `database/migrations/001_schema.sql`
- `experiments/E4/compose.yml`

[브라우저 사용](../../README.md#브라우저-사용--kali-desktop--windows) · [회귀 검사](../../docs/development_checks.md) · [결과 기록](../../docs/experiment_plan.md)
