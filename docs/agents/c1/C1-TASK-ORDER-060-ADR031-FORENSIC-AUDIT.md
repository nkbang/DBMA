# C1 Task Order 060 — ADR-031 Forensic Audit (승격 검증)

**상태**: 발급됨 — C1 Forensic Auditor 독립 검증 착수
**우선순위**: P0 (승격 차단 조건)
**선행 작업**: ADR-031 구현 완료 (CUE Task Order 031~033), Build Report 001
**근거 문서**: [docs/architecture/ADR-031-NAE-Passage-Commentary-Viewer.md](../architecture/ADR-031-NAE-Passage-Commentary-Viewer.md)
**작성일**: 2026-09-04
**역할**: Independent Forensic Auditor (NAE_C1_FORENSIC_AUDITOR_RULES 적용)

---

## 1. 배경 — 현재 상태 재확인

ADR-031(NAE Passage Commentary Viewer)은 **신규 Architecture Layer**입니다.
CUE 정책상 "새 Architecture Layer 추가"에 해당하므로, 다음 4개 조건을 모두
만족해야 `Proposed` → `Approved`로 승격됩니다:

| # | 조건 | CUE 보고 상태 |
|---|------|---------------|
| 1 | 구현 완료 | ✅ 6개 신규 파일 + 5개 수정 파일 |
| 2 | 회귀 통과 | ✅ 39개 단위테스트 + 290개 회귀테스트 PASS |
| 3 | C1 독립 리뷰 | ⏳ **이 Task Order** |
| 4 | 사용자 승인 | ⏳ Rev. Bang / HQ 대기 |

> **절대 규칙**: CUE가 제출한 PASS 결과를 독립 검증 없이 그대로 재사용하지 않는다.
> 모든 숫자는 처음부터 직접 재계산한다.

---

## 2. 검증 범위 (Scope)

### 2.1 필수 검증 항목 (모두 독립 실행)

| # | 검증 항목 | 방법 |
|---|-----------|------|
| V1 | 코드 경로 추적 | `retrieve_passage_commentary()` → `make_response_package()` → `generate_stream()` 실제 구현 grep/read |
| V2 | 테스트 재현 | `pytest tests/test_bible_text.py tests/test_passage_commentary.py tests/test_citation_format.py -q` 독립 실행 |
| V3 | ADR 정합성 | ADR-001(One Retrieval Engine) 준수, 기존 시그니처 무변경 확인 |
| V4 | Fail-closed | `BibleText.unavailable()` 경로가 예외를 전파하지 않는지 확인 |
| V5 | 기존 파이프라인 무접촉 | `git diff HEAD -- core/retrieval.py core/generation.py ...` 실행 |
| V6 | 회귀 테스트 | 넓은 `-k` 필터로 관련 전체 테스트 재실행 |
| V7 | 프롬프트 가드 | `_GUIDANCE`에 "추측 금지" 문구 포함 확인 |

### 2.2 제외 항목 (이번 Audit 범위 밖)

- Streamlit E2E 브라우저 테스트 (수동 검증은 CUE가 이미 수행)
- 성경 JSON 실제 데이터 (스키마만 검증, 실제 번역본 아님)
- ADR-030/032 등 다른 ADR (별도 Audit 필요)

---

## 3. 구현 범위 (C1 검증 작업)

### 3.1 코드 경로 추적 (V1)

다음 함수의 실제 호출 체인을 grep/read로 확인:

```bash
# 핵심 함수 정의 위치 확인
grep -n "def retrieve_passage_commentary\|def make_response_package\|def build_footnotes\|def generate_passage_commentary" core/passage_commentary.py

# UI 통합 경로 확인
grep -n "retrieve_passage_commentary\|make_response_package" ui/pages/_passage_commentary_tab.py
```

**검증 기준**:
- `processor.process()` 재사용 (새 엔진 인스턴스 없음)
- `compute_passage_match_score()` 재사용
- `GenerationService.generate_stream()` 재사용
- 새 검색 경로/엔진 생성 없음 (ADR-001 준수)

### 3.2 테스트 독립 재현 (V2, V6)

```bash
# 단위 테스트
cd ~/DBMA && source ~/envs/dbma311/bin/activate && python -m pytest tests/test_bible_text.py tests/test_passage_commentary.py tests/test_citation_format.py -v --tb=short 2>&1

# 회귀 테스트 (확장)
python -m pytest tests/test_generation_stream_contamination.py tests/test_corpus_admissions.py -v --tb=short 2>&1
```

**검증 기준**:
- CUE 보고 숫자와 일치해야 함 (39/39 단위, 74+/74 회귀)
- 출력 그대로 보고서에 복사

### 3.3 ADR 정합성 (V3)

```bash
# 기존 시그니처 무변경 확인
git diff HEAD -- core/retrieval.py core/generation.py core/embedder.py core/tsu_builder.py core/identity_registry.py core/index_orchestrator.py core/processing.py
```

**검증 기준**:
- git diff empty (파일 변경 없음)
- `QueryProcessor.process()` 시그니처 변경 없음
- `GenerationService.generate_stream()` 시그니처 변경 없음

### 3.4 Fail-closed (V4)

```bash
grep -A 5 "def unavailable\|class BibleText" core/bible_text.py
```

**검증 기준**:
- `BibleText.unavailable(reason)` 센티넬 객체 반환
- 예외 전파 없음
- `_parse()` 에서 스키마 불일치 시 `unavailable()` 반환

### 3.5 프롬프트 가드 (V7)

```bash
grep -A 10 "_GUIDANCE = " core/passage_commentary.py
```

**검증 기준**:
- "자료가 없는 내용은 추측하거나 지어내지 않는다" 문구 포함
- "오직 <자료> 에 근거해" 문구 포함

---

## 4. 판정 규칙 (Gate Rules)

```
PASS       = 실제로 독립 재현·검증한 evidence에 근거한 경우에만
NOT VERIFIED = 필요한 evidence를 독립적으로 재현할 수 없는 경우
NOT VERIFIED = 아직 해소되지 않은 discrepancy가 남아있는 경우
```

**오류를 발견하지 못했다는 사실만으로 PASS를 선언하지 않는다.**

### 판정 테이블

| 항목 | 결과 |
|------|------|
| V1 코드 경로 추적 | [C1 작성] |
| V2 테스트 재현 | [C1 작성: N/N PASS] |
| V3 ADR 정합성 | [C1 작성] |
| V4 Fail-closed | [C1 작성] |
| V5 기존 파이프라인 무접촉 | [C1 작성] |
| V6 회귀 테스트 | [C1 작성: N/N PASS] |
| V7 프롬프트 가드 | [C1 작성] |

**최종 판정**: [PASS / NOT VERIFIED]

---

## 5. 산출물

1. **이 파일** (`C1-TASK-ORDER-060-ADR031-FORENSIC-AUDIT.md`) — 검증 결과 기록
2. **ADR-031 상태 변경** (PASS 시): `docs/architecture/ADR-031-NAE-Passage-Commentary-Viewer.md` Proposed → Approved
3. **Forensic Audit 보고서**: `docs/NAE_FORENSIC_AUDIT_ADR-031.md` (별도 파일)

---

## 6. 제약 조건 (ABSOLUTE RULES)

### 절대 금지 사항

- Production TSU 수정
- Production corpus 수정
- Human Decision 수정
- `exception_queue.json` 수정
- screening state 수정
- authoritative Evidence 파일 수정
- Promotion 실행
- discrepancy를 발견한 뒤 임의로 수정 (REPORT ONLY 원칙)
- CUE가 제출한 PASS 결과를 독립 검증 없이 그대로 재사용
- 승인 없이 다른 모델로 전환

### 검증 규칙

- 모든 숫자는 직접 실행한 도구 호출 결과에 근거해야 한다
- 정적 문서(STATE.md, ADR 요약 등)를 인용하기 전에 원본을 다시 열어서 확인한다
- 테스트/검증 스크립트에 mock, synthetic, 하드코딩된 샘플 데이터를 쓰지 않는다
- "문제가 있다"거나 "해야 할 일"로 목록에 올리는 것 자체가 사실 주장이다 — 확인 안 하고 목록에 넣지 않는다

---

## 7. 실행 순서

1. §2 검증 항목 모두 독립 실행
2. §4 판정 테이블 작성
3. PASS 시 §8로 → ADR Approved 승격 처리
4. NOT VERIFIED 시 — 차단 사유 명시, HQ 보고

---

**발급자**: CUE (David Bang)
**수령자**: C1 (Forensic Auditor)
**모드**: Plan mode 발급 → Act mode 전환 후 실행
