# NAE 성경·개인 서재 통합 검색 및 근거 통제 파이프라인 — 실행 계획서 v3

**작성일:** 2026-07-29
**근거 문서:** PM/Implementation Engineer 작업명령서 "성경·개인 서재 통합 고급 검색 및 근거 통제 파이프라인" (본 대화 첨부)
**관계:** [DBMA-Search-Trust-Pipeline-Plan-v2.md](DBMA-Search-Trust-Pipeline-Plan-v2.md)를 **대체가 아니라 상위 프레임으로 일반화**함.
v2의 Dataset Registry/Trust Tier(T1~T4)/ClaimGuard/무마찰 원칙은 그대로 유지되고, v3에서 "Scripture Corpus"
하나의 코퍼스로 재배치된다. v1은 계속 폐기 상태 유지.

---

## 0. 브랜드 메모 확인

- 제품 브랜드(내서재/NAE)는 2026-07-28 동결됨 — 본 지시서의 "NAE" 표기는 이 동결과 일치, 신규 rename 아님.
- 코드베이스 내부 식별자는 계속 `DBMA` 유지 ([[project_brand_freeze_nae]] 참고). 본 문서도 내부적으로는
  DBMA 레포 안에서 작업하되, 문서 제목만 사용자 지시서의 "NAE" 표기를 따른다.

## 1. v2 → v3 확장 핵심

| 항목 | v2 (성경 전용) | v3 (통합) |
|---|---|---|
| 대상 코퍼스 | Scripture만 | Scripture / Logos / Personal Library(DEVONthink) / Obsidian / Sermon / Research, 6종 |
| 공통 모델 | `BibleTagAnnotation` 등 성경 전용 | `EvidenceUnit` — 모든 코퍼스 공통 인터페이스 |
| 신뢰 등급 | Dataset 단위 trust_tier | `source_tier` + `annotation_tier` 로 세분화, EvidenceUnit에 내장 |
| ClaimGuard | 성경 답변에만 | **모든 코퍼스의 모든 생성 답변**에 적용 (단일 저자 견해/개인노트/성경사실 자동 구분) |
| 커넥터 | 없음(성경 데이터만) | DEVONthink / Obsidian / Logos / PDF·DOCX·EPUB·HTML / OCR / Scrivener |
| 검색기 | `ParallelRetriever` (성경 7종 검색) | Intent Router → 코퍼스별 Retriever 6종 → Evidence Normalizer → Hybrid Ranker |
| 저장소 | 구조화 DB + Qdrant (미확정) | 동일 구조 유지, EvidenceUnit 스키마로 통합 (구조화 DB 선택은 v2 미해결사항 그대로 승계) |

**v2 Sprint A~E는 폐기되지 않는다** — v3 Phase 1(공통 기반)·Phase 4(통합 검색)의 "Scripture Retriever" 부분에
그대로 흡수된다. 즉 v2가 먼저 구현해야 할 성경 전용 최소 스펙이고, v3가 이를 감싸는 일반화 레이어다.

---

## 2. 핵심 신규 개념

- **EvidenceUnit**: 성경 절, PDF 문단, Obsidian block, Logos 위치를 하나의 스키마로 정규화. `corpus_type`,
  `location`(canonical_bible_ref/page/section/block 등 다형적), `provenance`(원본 해시·추출기·OCR 품질),
  `rights`(license_status/retrieval_allowed/export_policy), `quality`(pass/rechunk/review/quarantine),
  `trust`(source_tier/annotation_tier) 5개 축.
- **이중 기준 금지**: 성경만 근거 통제하고 개인 PDF/노트는 단정적 요약을 허용하는 방식 금지 — 코퍼스별
  근거 기준·인용 단위는 달라도 통제 자체는 전 코퍼스 동일 적용.
- **Corpus-aware Ranking**: 단일 점수가 아니라 코퍼스 성격별 가중치(semantic + lexical + bible_ref_match +
  metadata_match + citation_readiness + source_tier_weight + user_library_preference - noise - rights_penalty).
- **Citation-ready 출력**: 최종 답변에서 [성경 본문] / [사용자 서재] / [외부 자료] / [NAE 분석] 4블록 분리 표시.

---

## 3. Phase 분할 (지시서 원문 채택, v2 Sprint와의 매핑 포함)

| Phase | 목표 | v2와의 관계 |
|---|---|---|
| **1. 공통 기반** | `EvidenceUnit`/`SourceRecord`/`RightsPolicy`/`QualityStatus`, canonical ref parser 전 코퍼스 연결, 구조화DB/VectorDB 역할 분리 | v2 Sprint A(DatasetRegistry/TrustTier/ClaimPolicy)를 EvidenceUnit 하위 필드로 재구성 |
| **2. 커넥터·인제스트** | DEVONthink/Obsidian/Logos/PDF·DOCX·EPUB·HTML/OCR/Scrivener 어댑터, 인제스트 리포트 | v2 Sprint B(TagIngestValidator)를 코퍼스별 adapter로 확장 |
| **3. 품질·청킹** | 문서유형별 semantic chunker, pass/rechunk/review/quarantine 자동분류, 중복판본 방지 | 신규 (성경 코퍼스는 기존 청킹 파이프라인 재사용) |
| **4. 통합 검색·랭킹** | Intent Router, 코퍼스별 Retriever 6종, hybrid retrieval, corpus-aware 재랭킹, 필터·그룹화 UI | v2 Sprint C(ParallelRetriever)가 Scripture Retriever로 그대로 편입 |
| **5. ClaimGuard·Evidence Renderer** | 코퍼스별 정책의 ClaimGuard, 근거분리 렌더러, Markdown/Obsidian 내보내기 | v2 Sprint D 그대로 확장 (위험표현 사전에 "정통 교리/모든 학자/학계의 합의" 추가) |
| **6. 감사·재현성·운영자동화** | QueryAuditLog, n8n 배치 인제스트/품질보고, Slack 예외통지 | v2 Sprint E(평가) + 신규 운영자동화 |

각 Phase는 별도 Task Order로 세분화 발급. 순서는 위 표 순서를 기본으로 하되, **Phase 1은 성경 코퍼스
스펙(v2 Sprint A)이 선행되어야 하므로 v2 착수가 v3 Phase 1의 전제조건**이다.

---

## 4. 테스트 시나리오 (지시서 원문, 수용 기준의 실측 근거로 사용)

- **A. 성경+개인노트**: "창세기 24장의 기도에 관해 내가 이전에 연구한 내용과 근거를 보여줘"
- **B. 논문 주장 검증**: "'창세기 24:12가 성경 최초의 기도'라고 주장하는 자료와 반대 근거를 비교해줘"
- **C. 설교 준비**: "창세기 24:12–14 설교를 준비한다. 과거 설교·노트·주석에서 근거를 모아줘"

세 시나리오 모두 Phase 4~5 완료 후 회귀 테스트 세트로 고정.

---

## 5. 수용 기준 (지시서 원문 요약)

- [ ] 성경 본문과 개인 자료가 동일 `EvidenceUnit`으로 검색된다.
- [ ] 모든 결과가 원본 위치·출처·버전·권리·품질 상태를 가진다.
- [ ] 성경참조가 개인노트/PDF/설교문/Logos 자료에서 자동 추출·정규화된다.
- [ ] DEVONthink/Obsidian/Logos 링크가 원문으로 되돌아갈 수 있게 보존된다.
- [ ] 개인 노트·외부 학술자료·성경 본문이 답변에서 명확히 구분 표시된다.
- [ ] ClaimGuard가 전 코퍼스에 적용된다.
- [ ] 라이선스·권리 정책에 따라 표시/내보내기가 제한된다.
- [ ] 저품질 OCR·중복 자료가 상위 결과를 오염시키지 않는다.
- [ ] 한 질의로 6개 코퍼스 병렬 검색이 가능하다.
- [ ] 검색·질의확장·출처·응답·정책적용이 자동 감사 로그에 남는다.
- [ ] 승인/보류/거부 단계는 일반 사용 흐름에 없음 (v2 원칙 승계).

---

## 6. 미해결 사항 (사용자 확인 필요, v2 항목 승계 + 신규)

1. ~~구조화 저장소 선택~~ → **결정됨 (2026-07-29): SQLite** (v2와 동일 결정 승계). v3에서 코퍼스 6종까지
   확장될 때 SQLite로 스키마 복잡도가 감당 가능한지는 v2 완결 후 Phase 2 착수 시점에 재점검.
2. **Logos 라이선스 경계**: "합법적으로 로컬 접근 가능한 범위"의 구체적 판단 기준(어떤 API/내보내기 방식이
   허용되는지) — Logos 측 이용약관 재확인 필요, 코드 작업 착수 전 사용자 확인 요망.
3. ~~착수 순서~~ → **결정됨 (2026-07-29): v2(성경 전용, Sprint A~E) 먼저 완결 후 v3로 병합 진행.**
   즉 성경 코퍼스는 v2 스펙(DatasetRegistry/TrustTier/ParallelRetriever/ClaimGuard) 그대로 먼저 구현하고,
   이후 v3 Phase 2(커넥터)부터 이어서 다른 코퍼스를 붙인다. v2 완결 전에는 EvidenceUnit 일반화 작업을
   시작하지 않는다.
4. DEVONthink/Obsidian 실제 vault·DB 경로 및 접근 권한 확인 (로컬 파일시스템 스캔 범위).

## 7. 착수 계획

**확정 순서:** v2 Sprint A → B → C → D → E (성경 코퍼스 완결) → v3 Phase 2(커넥터: DEVONthink/Obsidian/Logos 등) →
Phase 3~6. v2가 곧 v3 Phase 1의 성경 부분 구현이므로, v2 완결 시점에 Phase 1도 사실상 완료된 상태가 된다.
남은 Phase 1 작업(EvidenceUnit을 성경 외 코퍼스로 일반화하는 스키마 조정)은 Phase 2 착수 직전에 별도 확인.

다음 조치: v2 Sprint A Task Order 작성 (저장소 SQLite로 확정됨, 남은 미해결은 Logos 라이선스 경계뿐).

진행률: v2(Sprint A~D + 응답생성 연동) 완료. v3 Phase 2 착수 시도 중 — **DEVONthink 실제 접근 방식은
사용자가 "일단 보류"함(2026-07-29)**. 그 결정과 무관한 부분(EvidenceUnit 공통 모델, EvidenceSourceAdapter
인터페이스, 픽스처 기반 DevonthinkFixtureAdapter)만 C1 Task Order 025로 완료.

**Task Order 025 완료 (2026-07-29):** `core/evidence_unit.py`(EvidenceUnit + 하위 모델 7종),
`core/evidence_adapters/`(base.py + devonthink_fixture_adapter.py), 픽스처 JSON 3건.
CUE 재검증: 신규 31/31 통과, **전체 회귀 스위트 1020/1020 통과**, `core/retrieval.py`/
`core/parallel_retriever.py`/`core/generation.py`/`ui/pages/chat.py` 미접촉 확인, 어댑터 코드에
osascript/sqlite3/실제 DEVONthink 접근 호출 없음을 grep으로 확인.

**DEVONthink 연동 철회 (2026-07-29, 사용자 결정).** 접근 방식 3안 중 아무것도 선택하지 않고 연동 자체를
취소함. `core/evidence_unit.py`/`core/evidence_adapters/`(EvidenceUnit 모델 + 픽스처 어댑터, Task Order 025)는
DEVONthink 전용이 아니라 범용 인프라이므로 코드는 그대로 남겨두되, **DEVONthink 실제 연동은 v3 로드맵에서
제외**한다.

**Notion 커넥터 추가 (2026-07-30, 사용자 결정).** DEVONthink 대신 Notion을 개인 지식 코퍼스로 선택.
`CorpusType.NOTION` 신규 추가, `core/evidence_adapters/notion_fixture_adapter.py`(픽스처 기반, 실제
Notion API 미호출)를 C1 Task Order 028로 착수·완료. CUE 재검증: 신규 15/15 + 관련 46/46 통과,
`core/retrieval.py`/`core/parallel_retriever.py`/`core/generation.py`/`ui/pages/chat.py` 미접촉 확인,
실제 API 호출 코드(`api.notion.com`/`NOTION_TOKEN`/`notion_client`) 없음을 grep으로 확인.

**실제 Notion 연동 착수 전 사용자 결정 필요 (5개, C1 정리):** (1) Integration Token 발급,
(2) 워크스페이스 범위, (3) 페이지 매핑 정책(블록 단위 vs 페이지 단위), (4) 속성 스키마 매핑,
(5) 증분 동기화 전략. DEVONthink와 같은 원칙으로 별도 결정 후 진행.
