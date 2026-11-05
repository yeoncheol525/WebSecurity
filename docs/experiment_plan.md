# 다음 단계의 실험 계약

기준 자료는 `4조_MiniShop_실증형_최종기획서.pdf`(7쪽)와 사용자가 별도로 제공한 개발환경 구축 지시서입니다.
이번 구현은 지시서의 **안전한 환경 구축 단계**만 수행합니다. 이전 SQLite/V0~V2 기획의 배송지 수정 기능을
새 PostgreSQL 환경에 임의로 추가하지 않았습니다.

## 2×2 조건과 현재 상태

| 지시서 | 최종기획서 | 바인딩 | Catalog DB 역할 | 현재 상태 |
|---|---|---|---|---|
| E1 | S00 | OFF | catalog_reader_wide | 취약 쿼리 미구현, 실행 불가 |
| E2 | S10 | ON | catalog_reader_wide | 역할·선택용 override 준비, 직접 DB 권한만 검증 |
| E3 | S01 | OFF | catalog_reader | 취약 쿼리 미구현, 실행 불가 |
| E4 | S11 | ON | catalog_reader | 기본 정상 서비스, 환경·인가 검증 완료 |

환경 검증 T01~T12와 추후 공격·방어 실험 E1~E4는 서로 다른 테스트입니다.
현재 T03~T05는 실제 역할로 직접 접속해 권한 오류를 확인한 증거이며, SQLi가 존재하는 서비스에서
고객정보 유출을 방어했다는 실험 결과는 아닙니다.

## 모드 선택 경계

기본 Compose는 `DB_USER=catalog_reader`, `SQL_QUERY_MODE=bound`를 고정합니다.
다른 SQL_QUERY_MODE는 앱 시작을 거부합니다. 취약 모드가 구현된 것처럼 조용히 동작하지 않습니다.
다음 단계에서는 별도 코드 검토·격리 확인 후, 실험 전용의 쿼리 전략을 추가해야 합니다.

과다 SELECT 역할은 미리 권한을 구성하되 기본 NOLOGIN입니다. T12에서만 5분 만료로 잠시 로그인 허용 후,
고객100/주문300/결제메타300 조회 성공과 auth 조회 거부를 확인합니다. finally에서 NOLOGIN·만료 및
남은 wide 연결 종료를 수행하고, 정상 Catalog 역할이 `catalog_reader`임을 다시 확인합니다.
서비스 계정 전환 없이 권한 차이만 검사한 테스트라는 점을 구별합니다.

격리된 VM에서 실제 wide 역할로 **안전한 쿼리**를 실행할 준비도 제공합니다.
아래 절차는 다음 단계의 수동 실험용이며 이번 환경 구축 중 서비스 역할 전환은 실행하지 않았습니다.

```sh
# 실험 전: Host-only 격리와 바인딩 주소 확인, 실험 기록 시작.
# 관리자 자격증명은 postgres 컨테이너 안에서만 사용.
docker compose exec postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

psql에서 다음 관리 SQL을 실행하고 `\q`로 종료합니다.

```sql
SELECT format('ALTER ROLE catalog_reader_wide LOGIN VALID UNTIL %L',
              clock_timestamp() + interval '5 minutes') \gexec
```

```sh
docker compose -f docker-compose.yml -f experiments/wide.compose.yml up -d --no-deps --wait catalog-service
curl http://192.168.67.20:18080/health/catalog
# database_role=catalog_reader_wide, query_mode=bound 확인.
# Catalog에는 선택된 wide 역할의 비밀번호만 주입됨.
python3 scripts/restore_safe.py
curl http://192.168.67.20:18080/health/catalog
# database_role=catalog_reader, query_mode=bound 확인.
```

5분 만료는 추가 로그인 제한이며 이미 열린 DB 연결을 자동 종료하는 타이머가 아닙니다.
실험 종료·실패 시 반드시 `restore_safe.py`로 역할과 기존 연결을 복구합니다.
T12와 수동 wide 실험을 동시에 실행하지 마세요. 기본 앱 계정의 권한은 실험 중에도 확대하지 않습니다.

## 후속 실험 수용 기준

1. 공격 집합과 정상 집합을 분리하고 sequence_id를 고정. 공격 유형3종×10회×4조건=120회는 **향후 목표**.
2. 동일 시드·컨테이너 digest·입력·요청 순서 유지. 각 시퀀스 전 복원 시 기존 증거를 보존.
3. 공격 성공은 HTTP 200이나 SQL 오류가 아니라 비로그인 응답의 합성 customer_id 노출로 판정.
4. E3/S01에서는 SQL 구조 변조가 실제 성립하는 증거와 private SELECT 권한 거부를 함께 제시.
5. 코드 `execute(sql, params)`, SQL 템플릿, 실제 DB 역할, HTTP 응답을 연결. 펼쳐진 SQL 로그만으로 바인딩 판정 금지.
6. 고객 노출량은 고유 customer_id, 주문 노출량은 고유 order_id로 집계. 탐지는 sequence_id/rule_id 중복 제거.
7. 정상 요청은 조건별 30회 이상, median/p95 측정. 현재 구축 테스트의 소요시간을 공격 실험 결과로 재사용하지 않음.
8. 로그인 SQLi는 실제 해시 검증을 통과한 세션만 성공. 현재 로그인은 안전한 바인딩만 구현.
9. IDOR 보조 실험은 정상 user1 세션과 숫자형 타인 주문 ID로 독립 수행. 현재 소유자 검증은 항상 활성화.

최종기획서의 `account_role`은 이번 지시서의 명칭에 맞춰 `order_service`,
`catalog_overprivileged`는 `catalog_reader_wide`로 구현했습니다.
