# Build Report — Baptist Commentary 컬렉션을 채팅 검색에 연결

- 일자: 2026-09-26
- 유형: 버그 수정 (기존 흐름에 신규 연결 추가, ADR/Architecture 변경 없음)
- 배경: 사용자 요청("앱을 처음 실행해도 조직신학이나 주석의 침례교 관련
  질의의 답을 얻을 수 있어야 한다")에 따른 조사에서 발견 — `nae_ref_commentary_v1`
  (Gill/Broadus/Carroll/Spurgeon, 10,517건, ADR-030 Amendment B 하에 2026-09-17
  임베딩 완료)이 실제 채팅 흐름에서 단 한 번도 조회되지 않고 있었음.

## 문제

`ui/pages/chat.py::_inject_smith_context`가 (1) `search_reference()`를
`collection_names` 없이 호출해 기본값인 `nae_ref_v1`(Smith Bible Dictionary)만
조회하고, (2) 반환된 결과를 `"smith" in source_id/volume`으로 재필터링해
비-Smith 결과를 전량 폐기함. 그 결과 임베딩까지 완료된 침례교 주석
코퍼스가 죽은 데이터로 남아 있었음 — 최초 실행 여부와 무관하게 코드
자체가 이 경로를 열어주지 않았음.

## 수정

`ui/pages/chat.py`:
- `_inject_smith_context` → `_inject_reference_context`로 일반화. Smith
  컬렉션(`nae_ref_v1`)과 Commentary 컬렉션(`nae_ref_commentary_v1`)을
  각각 별도로 조회(top_k=2씩) — 두 컬렉션을 한 번에 병합해 top_k=3을
  뽑는 방식을 먼저 시도했으나, Smith 코퍼스(34,948건)가 Commentary
  코퍼스(10,517건)보다 훨씬 커서 원시 코사인 점수 경쟁에서 Commentary가
  밀려나 결과에서 사라지는 현상을 실측으로 확인 — 컬렉션별 개별 조회로
  전환해 두 출처 모두 노출을 보장.
- `content_type` 필드(ingest 시점에 부여: Smith 기본값
  `reference_dictionary`, Commentary는 `scripts/nae_commentary_ingest.py`가
  명시적으로 `reference_commentary` 태깅)로 구분해 각각 별도 레이블
  ("Smith Bible Dictionary" / "침례교 주석가 문헌 (Gill/Broadus/Carroll/
  Spurgeon)")로 `<reference>` 블록에 주입 — ADR-028 계층 원칙(참고 자료는
  보조, TSU/성경이 우선) 유지, 표현만 두 출처 모두를 포괄하도록 일반화.
- `_format_smith_context` → `_format_reference_context(entries, label)`로
  일반화(로직 무변경, 레이블 파라미터화).

## Changed Files

- `ui/pages/chat.py` (`_inject_smith_context`→`_inject_reference_context`,
  `_format_smith_context`→`_format_reference_context`, 호출부/독스트링 갱신)
- `tests/test_chat_evidence_hold.py` (monkeypatch 대상 함수명 갱신)
- `scripts/smith_e2e_verify.py` (함수명 갱신, 로직 무변경)
- `tests/test_chat_commentary_reference_wiring.py` (신규 — 회귀 테스트 3건)

## Tests

- 신규 3건(`tests/test_chat_commentary_reference_wiring.py`): 양쪽 컬렉션
  조회 확인, Smith-only 폴백 확인, 비활성 시 조회 자체가 없음 확인 — 전부 PASS
- 실제 Qdrant(`nae_qdrant`, 포트 7333)에 대한 수동 smoke:
  `search_reference()` 직접 호출로 `nae_ref_commentary_v1`에서
  `content_type=reference_commentary` 결과 확인, `_inject_reference_context()`
  End-to-End 호출로 로마서 8장 질의 시 Smith 블록 + Gill/Broadus 주석 블록이
  동시에 `llm_context_block`에 주입됨을 확인

## Regression

`pytest tests --ignore=tests/nae`: **2992 passed / 17 skipped** (기존
환경 갭 스킵과 동일 패턴, 신규 실패 없음)

## Architecture Rule / ADR Conflict

없음 — `core/retrieval.py`(TSU 경로), Embedding Engine, RAW 데이터,
Production Registry 무접촉. ADR-028(Smith는 보조 자료, citation badge
없음) 원칙을 Commentary 그룹에도 동일하게 적용해 확장했을 뿐, 원문 변경
없음. ADR-030 M2 고정 베이스라인(등록 레코드) 무접촉 — 이미 등록·임베딩된
데이터를 조회 경로에 연결한 것뿐, 신규 등록 없음.

## Git (Commit/Push)

완료 조건 충족(구현 완료·Test PASS·Regression PASS·Architecture Rule
PASS·ADR Conflict 없음) → 정책에 따라 커밋 후 현재 브랜치로 push.

## Next

- 사용자 실사용 확인 권장: 조직신학(예: "중생이란 무엇인가")과 주석형
  질의(예: "로마서 8장에 대한 침례교 관점 주석") 양쪽을 앱에서 직접
  질문해 답변에 두 레이어가 의도대로 반영되는지 확인.
- `nae_pd` 모듈(`config.yaml: modules.nae_pd.enabled: false`)은 이번
  수정과 무관 — Public Theology 섹션 UI 게이트일 뿐, Reference 검색
  경로는 이 플래그와 무관하게 항상 활성.
