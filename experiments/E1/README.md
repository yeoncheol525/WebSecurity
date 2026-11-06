# E1 · 기준선

| 항목 | 설정 |
|---|---|
| 검색 바인딩 | OFF |
| DB 최소 권한 | OFF |
| SQL_QUERY_MODE | `interpolated` |
| Catalog DB 역할 | `catalog_reader_wide` |

## 실행 · Ubuntu

프로젝트 루트에서 실행한다.

```sh
bash scripts/setup-ubuntu.sh --experiment E1
```

## 접속 · Kali Desktop / Windows

브라우저에서 `http://192.168.67.20:18080/shop`을 연다.
IP는 실제 Ubuntu Host-only 주소로 지정한다.
검색창 입력과 요청 관찰은 [브라우저 사용](../../README.md#브라우저-사용--kali-desktop--windows)을 따른다.

## 조건

- 문자열 삽입 방식의 상품 검색.
- wide 역할의 조회 권한 사용.
- 로그인·주문은 바인딩과 주문 소유자 검사 유지.
- 다른 조건과 같은 주소·DB 사용.

## 직접 비교·기록할 내용

정상 기능과 기준선 응답을 기록하고, 이후 조건에도 사용할 입력 집합·반복 횟수·판정 기준을 팀에서 확정한다.
실행 조건과 실제 DB 역할·query_mode를 확인하고 요청·응답·로그를 근거로 남긴다. 결과는 아직 미측정이다.

## 관련 파일

- `services/catalog/app/__init__.py`
- `services/common/runtime.py`
- `database/migrations/001_schema.sql`
- `experiments/E1/compose.yml`

[결과 기록](../../docs/experiment_plan.md) · [E4](../E4/README.md)
