# E2 · 바인딩

| 항목 | 설정 |
|---|---|
| 검색 바인딩 | ON |
| DB 최소 권한 | OFF |
| SQL_QUERY_MODE | `bound` |
| Catalog DB 역할 | `catalog_reader_wide` |

## 실행 · Ubuntu

프로젝트 루트에서 실행한다.

```sh
bash scripts/setup-ubuntu.sh --experiment E2
```

## 조건

- 검색값을 SQL 템플릿과 별도 인자로 전달.
- DB 역할과 조회 권한은 E1과 동일.
- 정상 검색·로그인·본인 주문 유지.
- E1과의 비교 요소: 검색 바인딩.

## 직접 비교·기록할 내용

E1과 동일한 입력·반복 횟수로 응답과 지연을 측정하고, 검색 코드의 인자 바인딩과 로그를 대조한다.
DB 역할·조회 권한은 E1과 같으므로 관측된 차이를 바인딩 적용과 연결해 분석한다. 정상 검색·로그인·본인 주문도 기록한다.

## 관련 파일

- `services/catalog/app/__init__.py`
- `services/common/runtime.py`
- `experiments/E2/compose.yml`

[브라우저 사용](../../README.md#브라우저-사용--kali-desktop--windows) · [결과 기록](../../docs/experiment_plan.md)
