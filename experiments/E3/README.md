# E3 · 최소 권한

| 항목 | 설정 |
|---|---|
| 검색 바인딩 | OFF |
| DB 최소 권한 | ON |
| SQL_QUERY_MODE | `interpolated` |
| Catalog DB 역할 | `catalog_reader` |

## 실행 · Ubuntu

프로젝트 루트에서 실행한다.

```sh
bash scripts/setup-ubuntu.sh --experiment E3
```

## 조건

- 상품 검색 방식은 E1과 동일.
- Catalog의 DB 접근을 최소 권한 역할로 제한.
- 로그인·주문은 바인딩과 주문 소유자 검사 유지.
- E1과의 비교 요소: DB 권한.
- 기존 DB 볼륨의 권한 변경은 별도 마이그레이션으로 적용.

## 직접 비교·기록할 내용

E1과 동일한 입력·반복 횟수를 사용하고, 실제 DB 역할·GRANT와 요청 ID가 같은 서버 로그를 대조한다.
권한 거부, 입력 오류, 연결 실패를 구분해 최소 권한의 효과를 분석한다. 정상 기능의 실패나 한계도 함께 기록한다.

## 관련 파일

- `database/migrations/001_schema.sql`
- `services/catalog/app/__init__.py`
- `experiments/E3/compose.yml`

[브라우저 사용](../../README.md#브라우저-사용--kali-desktop--windows) · [결과 기록](../../docs/experiment_plan.md)
