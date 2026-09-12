# DBMA/NAE Proposal ↔ Current-Pipeline Conflict Register

- 작성일: 2026-09-10
- 대상 제안서: `docs/DBMA_NAE_EVIDENCE_BASED_IMPROVEMENT_PROPOSAL_v1.md`
- 증거 기준: 본 세션의 **1차 점검 보고서**·**2차 운영 검증 보고서**에서 확인된 사실만.
- 처리 원칙 (Conflict Protocol): 충돌 항목을 즉시 구현하지 않는다 / 기존 경로를 삭제·교체하지 않는다 / feature flag를 변경하지 않는다 / 전체 재색인·재청킹·DB migration을 실행하지 않는다 / 기존 데이터를 수정·삭제하지 않는다. 본 문서 작성 중 어떤 코드·설정·데이터·인덱스·서비스도 변경하지 않았다.
- 대규모 교체·전면 재작성은 **D안으로만** 기록하며 현 시점 권고안으로 제시하지 않는다.
- **개정 (2026-09-10)**: 이 문서가 UNKNOWN으로 두었던 **UK-1 / CON-008 / P1-4 선행조건**(= `absolute_claim_blocked`·citation card·Smith 항목의 실제 화면 동작)이 관측으로 해소되어 해당 서술을 갱신했다. 근거는 `docs/audit/DBMA-NAE-2ND-VERIFICATION-2026-09-09.md` **부록 A·B** — 기본 모델(`my-theology-bot-v2`, 70.6B) 대신 앱 자체 선택기로 `llama3.1:8b`를 골라 생성을 완료시킨 뒤 DOM 수준에서 관측했다. 관측 시 코드·설정·데이터·인덱스는 변경하지 않았다(해시 5종 전후 동일). 갱신된 항목에는 취소선 또는 `RESOLVED` 표기를 남겨 원래 판단 이력을 지우지 않았다.

---

# Conflict Register

| ID | Proposal Requirement | Current Evidence | Status | Severity | Active-Path Impact |
|----|---------------------|------------------|--------|----------|--------------------|
| CON-001 | P0-1: `_extract_keywords`가 `[]`일 때 문서측 토크나이저 `_tokenize`를 질의에도 적용해 BM25 keyword로 사용 | 질의 경로(`[a-zA-Z]{3,}`, `retrieval.py:470`)와 문서 경로(`_tokenize`, 한국어 2-gram)가 **분리 설계**돼 있음. BM25 하이브리드 가중 0.25. keyword 변경 시 모든 한국어 질의의 최종 랭킹 이동 [2차 §BM25, 1차 §3.3] | COMPATIBILITY_CONSTRAINT | HIGH | 직접 (legacy `QueryProcessor` 유일 활성 경로) |
| CON-002 | P0-2: `CitationBuilder`가 질의 시점에 `tsu_metadata_sidecar.json`를 읽어 `Citation.source_title/source_author`를 채움 | `tsu_manifest.json`이 `dataset_sha256`/`registry_sha256`/`config_sha256`로 provenance를 결속. TSU 메타는 `tsu_builder`가 registry 키 조건부로만 생성 [1차 §3.3/§3.4]. sidecar는 manifest가 포괄하지 않는 2차 메타 출처 | COMPATIBILITY_CONSTRAINT | MEDIUM | 직접 (citation 생성부) |
| CON-003 | P0-2(초안): `heading_path`가 없을 때 `verse_mapping` 파생 `scripture_reference`를 `text_location`으로 표시 | `verse_mapping` ↔ 본문 불일치 관측: `chunk_00018`=`MAT 25:1-13`인데 본문은 서론; `chunk_00261`=`MAT 6:14`인데 본문은 12절 해설 [2차 Q4/Q5] | CONFIRMED_CONFLICT | HIGH | 직접 (citation·성경참조 정확성). *제안서 slice에서 이미 제외* |
| CON-004 | P0-3: audit 로그를 `BASE_DIR/logs/retrieval_audit.jsonl`에 기록 | `config.yaml directories.logs_dir: "logs"` → `/Users/David/DBMA/logs` **디렉터리 부재**. 기존 telemetry 관례는 `DEFAULT_SEARCH_TELEMETRY_PATH = output/bench/search_telemetry.sqlite3` [1차 §3.3/§3.5] | COMPATIBILITY_CONSTRAINT | LOW | 간접 (신규 파일 위치 선택) |
| CON-005 | P0-4: Chat/Research 스피너에 클라이언트 hard timeout + "재시도" (답변 폐기 아님) | `research.py:277` `# Always run AI answer path alongside search (UX-007 §4.1)`. 검색결과·citation 렌더가 생성 완료에 의존. 진행 중 생성에 재시도 → 동시 생성 위험 (2차에서 curl 1회 경합이 결과를 흐림) [2차 D-절, V2] | CONFIRMED_CONFLICT | MEDIUM | 직접 (generation↔UI 렌더) |
| CON-006 | P1-3: Smith(`nae_ref_v1`) 결과를 citation 목록에 `source_type="reference"` 보조 출처로 전달 | Smith 항목을 `render_citation_card`로 전달하는 호출부 **없음** [2차 Q8]. `Citation` dataclass에 주/보조 구분 필드 없음 [1차 §3.2]. `nae_ref_v1`에 `review_status`/`usage_permission`/`copyright_status`/`citation_policy` 필드 자체가 없음 [2차 Q10] | CONFIRMED_CONFLICT | MEDIUM | 직접 (Smith 활성, citation 모델) |
| CON-007 | P1-1: subset 판정축 "알려진 정답 청크가 top-k에 존재" | 청크/문서 ID 단위 정답을 제공하는 파일이 없음 — `gold_queries.json`은 `expected_books`만, `expected_documents`는 자연어; `output/eval/*` chunk ID 0/8 일치 [2차 Q13/Q14, V10] | COMPATIBILITY_CONSTRAINT | MEDIUM | 없음 (eval 자산) |
| CON-008 | P1-4(C안): ClaimGuard 예외 시 "자동 검증 실패" 배지 (차단 아님) | ~~UNKNOWN~~ → **관측 완료(2026-09-10)**: `absolute_claim_blocked=True`여도 답변 전문이 먼저 렌더되고 `주장 검증: {reason}` caption 1줄이 뒤에 붙을 뿐, 차단·대체·재작성 없음 (`docs/audit/DBMA-NAE-2ND-VERIFICATION-2026-09-09.md` 부록 B §B.3). 배지 신설은 **현행 caption과 중복** | **RESOLVED** (구 UNVERIFIED_CONFLICT) | MEDIUM | 직접 (generation 출력·UI) |
| CON-009 | P0-1/P0-2/P0-3: 신규 feature flag를 프로세스 수준에서 토글하면 즉시 반영된다고 가정 | `get_shared_query_processor()`는 processor를 캐시하고 `dataset_sha256` 변경 시에만 재생성. `is_enabled()`는 `os.environ`을 호출 시점 조회 [2차 §"query→답변", §활성경로판정] | COMPATIBILITY_CONSTRAINT | MEDIUM | 직접 (롤아웃 메커니즘) |
| CON-010 | P1-5: 상대 `bench_dir`을 `BASE_DIR` 기준으로 재해석 | `scripts/` 97개 중 cwd 상대 `bench_dir` 동작에 의존하는 것이 있는지 **미확인**; `.automation/` control-plane 동작도 UNKNOWN [1차 U3/U15] | UNVERIFIED_CONFLICT | LOW | 간접 (실행 위치) |
| CON-011 | P0-2(초안): sidecar에 `rights: {copyright_status, usage_permission}` 포함 | 매튜 풀 EPUB DC `rights=[]` (빈 값). 상업 출판물(크리스챤다이제스트, ISBN 978-89-447-8472-9). 프로젝트 관례는 미확인 권리를 `AUTHORITATIVE_SOURCE_MISSING`으로 표시(`nae_tsu_v1` `citation_policy_status` 100%) [1차 §3.4, 2차 Q10] | CONFIRMED_CONFLICT | HIGH | 간접 (citation 표시·저작권 정확성). *제안서 slice에서 이미 제외* |
| CON-012 | 제안서 전체: P0-1(retrieval), P0-2(citation), P0-3(telemetry), P1-3(NAE 경계) 변경 | ADR-001~ADR-033이 존재하나 두 점검은 **개수·일부 번호만 확인, 본문 미판독** [1차 §1.2]. retrieval·citation·telemetry·NAE 경계를 규율하는 Approved ADR과의 정합을 확인할 수 없음 | UNVERIFIED_CONFLICT | HIGH | 전 경로 (거버넌스) |

---

# Conflict Detail

## CON-001 — 질의 토크나이저 재사용과 BM25 랭킹 계약

- **Proposal requirement**: P0-1. `_extract_keywords()`가 ASCII 정규식으로 `[]`를 반환할 때, 문서 색인이 쓰는 `_tokenize`를 질의에도 적용한 토큰을 `bm25_score(keywords, doc_text)`의 keyword로 사용한다 (플래그 `RETRIEVAL_KOREAN_KEYWORDS`, 기본 off).
- **Current pipeline evidence**: 질의 파싱은 `re.findall(r'\b[a-zA-Z]{3,}\b', query.lower())` (`core/retrieval.py:470`)로 라틴 문자만 뽑고, 문서측은 `_tokenize`가 한국어를 2-gram(`'구하라 그리하면'`→`['구하','그리']`)으로 처리한다. 두 경로가 다르다는 것은 실행으로 확인됨 [2차 §"BM25가 0인 이유"]. 하이브리드 최종 점수는 `0.25·BM25 + 0.20·vector + 0.30·theological + 0.20·PassageMatch + 0.05·SourceTierBonus` [1차 §3.3].
- **Conflict type**: COMPATIBILITY_CONSTRAINT — 현재 랭킹은 "한국어 질의에서 BM25=0"을 전제로 튜닝된 상태다. keyword를 채우면 BM25 항이 살아나 **모든 한국어 질의**의 최종 순위가 이동한다. 결함이 아니라, 바꾸면 측정이 필요한 계약.
- **Reproduction status**: BM25=0·후보 풀 `pool[:100]`·A2 정확문구 누락은 CONFIRMED 재현 [2차 Q3/A1/A2]. **개선의 효과·부작용은 미재현**(구현·측정 안 됨).
- **Affected components**: `core/retrieval.py::QueryParser._extract_keywords`, `bm25_score`, 하이브리드 가중합(STEP 5), `RankedCandidate` 순위; 간접적으로 `ContextAssembler`(다른 top-k), `CitationBuilder`(다른 citation).
- **Data and compatibility impact**: 데이터 무결성 영향 없음(질의 시점). 원본·인덱스 불변. 플래그 off면 `_extract_keywords` 반환 바이트 동일 → 회귀 없음. 플래그 on이면 한국어 질의 결과가 달라짐 — 기존 사용자 경로의 **검색 품질 변화**(개선일 수도, 악화일 수도). rollback = 플래그 unset.
- **Existing ADR or policy relation**: retrieval 스코어링을 규율하는 ADR이 있는지 UNKNOWN [1차 §1.2] → CON-012에 종속. CUE Operating Policy상 "TSU Pipeline 진입"·"Metadata Model 변경"은 아니나 검색 랭킹 변경은 회귀 민감 → C1 Review 권장 대상.
- **A: retain current behavior**: 한국어 질의는 성경참조가 있을 때만(=`_metadata_filter` 경유) 제대로 검색되고, 그 외에는 vector·theological 항에만 의존한다. 위험: PB-01이 그대로 남음(A2류 실패). 수용 조건: 한국어 사용자가 항상 성경참조를 포함하거나, vector 유사도만으로 충분하다고 판단될 때.
- **B: minimal reinforcement**: 플래그 뒤 구현 + KO/EN/scripture 3분리 acceptance + P1-1 subset 회귀. 기본값은 off 유지, "opt-in 실험 플래그"로만 병행. 기존 경로 무변경.
- **C: isolated / feature-flag PoC**: B와 동일 형태이되, 별도 브랜치·플래그에서 S1 subset으로 flag on/off A/B를 돌려 (a) KO-exact top-5 진입 (b) EN·scripture 완전 동일 (c) subset 종합 비회귀를 정량 확인한 뒤에만 기본값 전환 논의.
- **Required validation evidence**: P1-1 subset 구축(CON-007 해소) → S3 A/B 결과 → `_tokenize` 2-gram이 BM25 문서 통계(idf 등)와 어떻게 상호작용하는지 별도 측정.
- **Decision owner**: HQ (검색 품질 정책) — 측정 증거는 CUE, 독립 검토는 C1.
- **Decision status**: **HOLD** — 플래그 구현·acceptance 설계까지는 진행 가능(APPROVE FOR POC 수준), 기본값 전환은 S1+S3 통과 전까지 HOLD.

## CON-002 — sidecar 메타데이터 출처와 manifest provenance 계약

- **Proposal requirement**: P0-2. `output/bench/tsu_metadata_sidecar.json`(신규 additive)을 `CitationBuilder.build_citations()`가 질의 시점에 읽어, TSU 레코드의 `title`/`author`가 null일 때 `Citation.source_title`/`source_author`를 채운다.
- **Current pipeline evidence**: `tsu_manifest.json`은 `{dataset_sha256, registry_sha256, config_sha256, build_commit, builder_script, tsu_count}` 로 데이터셋의 provenance를 한 곳에 결속한다 [1차 §3.3]. TSU 메타(`source_provenance`/`nae_metadata`)는 `tsu_builder.py:450/459/470/477`이 registry에 특정 키가 있을 때만 생성한다 [1차 §3.4]. citation에 나타나는 값의 출처는 현재 전부 `tsu_dataset.jsonl` 한 파일이다.
- **Conflict type**: COMPATIBILITY_CONSTRAINT — sidecar는 manifest가 해시로 보증하지 않는 **두 번째 메타 출처**가 된다. citation에 표시되는 서지가 `dataset_sha256`로 추적되지 않는다.
- **Reproduction status**: 메타 null은 CONFIRMED [1차 §3.4]. sidecar는 미존재.
- **Affected components**: `core/retrieval.py::CitationBuilder.build_citations`, `Citation`, `ui/components/citation_card.py`(값이 truthy가 되면 행 추가), `tsu_manifest.json` provenance 모델, (신규) sidecar 빌더.
- **Data and compatibility impact**: `tsu_dataset.jsonl`·`dataset_sha256` 불변(무결성 OK). `Citation` 시그니처 불변(기존 필드 fill). 회귀 위험: `source_title is None`을 단언하는 테스트가 있으면 flag-off 경로로 유지해야 함. 프라이버시/저작권: 서지 메타만(본문 없음). rollback = 파일 삭제 / 플래그 unset.
- **Existing ADR or policy relation**: metadata model·provenance를 규율하는 ADR UNKNOWN [1차 §1.2] → CON-012. CUE Operating Policy상 "Metadata Model 변경"에 해당할 수 있어 C1 Review 대상.
- **A: retain current behavior**: citation card가 파일명+별점만 표시. 위험: PB-02 지속(학술 인용 불가). 수용 조건: 근거 카드가 "출처 파일 확인용"으로만 쓰이고 정식 인용은 사용자가 수동 보완할 때.
- **B: minimal reinforcement**: sidecar에 `provenance` 블록(`source: "epub_dc_metadata"`, `extracted_at`, `epub_sha256`)을 포함시켜 값의 출처를 명시하고, `tsu_manifest.json`에 `metadata_sidecar_sha256` 한 줄을 **추가 제안**(별도 승인). citation card에 서지 값의 출처 툴팁("원본 EPUB 서지"). 기존 경로 무변경.
- **C: isolated / feature-flag PoC**: `CITATION_SIDECAR_FILL` 뒤에서 A3 5건에 대해 fill 전후 citation dict를 비교, `dataset_sha256` 불변·`document_id` 조인 유일·`2710 passed` 확인(S4).
- **Required validation evidence**: S4 결과 + `document_id` 1:1 조인 증명(단일 문서에서 자명, 다중 문서 케이스는 CON 별건) + 서지 값이 EPUB DC와 일치함을 육안 대조.
- **Decision owner**: CUE (승인된 guardrail 내 구현 세부) + C1 Review(metadata 출처 추가).
- **Decision status**: **APPROVE FOR POC** — B의 provenance 블록을 포함해 S4까지. `tsu_manifest.json` 필드 추가는 별도 HQ 승인.

## CON-003 — verse_mapping을 표시 locator로 사용

- **Proposal requirement**: P0-2 초안. `heading_path`가 비면 `Citation.scripture_reference`(= `verse_mapping` 파생)를 citation card `text_location`으로 전달.
- **Current pipeline evidence**: `verse_mapping`과 본문 내용이 일부 어긋난다 — A1 #3 `chunk_00018`은 `verse_mapping` `MAT 25:1-13`이나 본문은 마태복음 서론; A3 #4 `chunk_00261`은 `MAT 6:14`로 매핑됐으나 본문은 주기도문 12절 해설 [2차 Q4/Q5]. `verse_mapping` 키 조합 중 chapter 없는 건이 1,294/1,363 [1차 §3.4] → `MAT ?:?` 문자열 생성 [2차 Q7].
- **Conflict type**: CONFIRMED_CONFLICT — 알려진 오매핑을 사용자에게 "본문 위치"로 표시하면 인용·성경참조 정확성을 직접 훼손한다.
- **Reproduction status**: CONFIRMED [2차 Q4/Q5, A1/A3 관측].
- **Affected components**: `ui/pages/chat.py` citation card 호출부, `Citation.scripture_reference`, `verse_mapping` 파이프라인(정제/색인 단계).
- **Data and compatibility impact**: 데이터 불변(표시만). 위험은 **인용 정확성**: 오매핑이 화면에 "근거 위치"로 노출.
- **Existing ADR or policy relation**: 성경참조 매핑을 규율하는 ADR UNKNOWN [1차 §1.2] → CON-012.
- **A: retain current behavior**: `text_location`을 채우지 않음(현행). citation card는 파일명만. 위험: locator 부재 지속. 수용 조건: locator보다 오정보 회피가 우선(신학 연구 맥락에서 타당).
- **B: minimal reinforcement**: `verse_mapping`의 신뢰도를 별도 조사(정제/색인 단계에서 verse_mapping이 어떻게 생성되는지, 오류율)한 뒤, chapter+verse가 모두 있고 본문 텍스트와 성경 구절 문자열이 실제로 겹칠 때(passage match ≥ 임계)만 locator로 표시.
- **C: isolated / feature-flag PoC**: `CITATION_VERSE_LOCATOR` 뒤에서, 정답이 알려진 소수 청크(주기도문 `chunk_00280` 등)에 대해 표시 locator vs 실제 본문 위치를 육안 대조.
- **Required validation evidence**: `verse_mapping` 생성 경로 판독 + 오매핑률 측정 + passage match 게이트의 정밀도.
- **Decision owner**: HQ (인용 정확성 정책).
- **Decision status**: **HOLD** — 제안서 첫 slice에서 이미 제외됨. P1-2(EPUB heading provider)로 실제 locator를 얻는 편이 낫다. verse_mapping locator는 신뢰도 조사 전까지 HOLD.

## CON-004 — audit 로그 위치와 기존 telemetry 관례

- **Proposal requirement**: P0-3. `BASE_DIR/logs/retrieval_audit.jsonl`에 append.
- **Current pipeline evidence**: `config.yaml directories.logs_dir: "logs"`가 가리키는 `/Users/David/DBMA/logs`는 **부재** [1차 §3.5]. 기존(비활성) telemetry는 `output/bench/search_telemetry.sqlite3`를 상수로 가짐 [1차 §3.3].
- **Conflict type**: COMPATIBILITY_CONSTRAINT — 관측 산출물이 `output/bench/`(telemetry)와 `logs/`(신규)로 갈린다. 또 `logs/` 디렉터리 자체가 없어 라이터가 생성해야 함.
- **Reproduction status**: 디렉터리 부재 CONFIRMED [1차 §3.5].
- **Affected components**: 신규 `core/retrieval_audit.py`, `core/config.py`(경로 상수), `.gitignore`(logs/ 무시 여부 확인 필요).
- **Data and compatibility impact**: additive. 무결성·호환성 영향 없음. rollback = 파일·디렉터리 삭제.
- **Existing ADR or policy relation**: 없음으로 추정(관측성은 REFERENCE 스코프, [메모리: NAE Dashboard Scope Discipline]) → CON-012.
- **A: retain current behavior**: 관측 산출물 없음(현행). 위험: PB-03 지속.
- **B: minimal reinforcement**: 경로를 **기존 관례에 맞춰** `BASE_DIR/output/bench/retrieval_audit.jsonl`로 두고, `core/config.py`에 `DEFAULT_RETRIEVAL_AUDIT_PATH` 상수를 `DEFAULT_SEARCH_TELEMETRY_PATH`와 같은 규칙(단, BASE_DIR 절대 — CON-010과 정합)으로 정의. `logs/` 신설 회피.
- **C: isolated / feature-flag PoC**: `RETRIEVAL_AUDIT_LOG` 뒤에서 S2. 경로가 `os.chdir` 무관하게 고정되는지 포함.
- **Required validation evidence**: S2 acceptance + `.gitignore` 확인(감사 로그가 커밋되지 않도록).
- **Decision owner**: CUE (구현 세부).
- **Decision status**: **APPROVE FOR POC** — B(경로를 `output/bench/`로, BASE_DIR 절대)로 확정하고 S2 진행.

## CON-005 — 생성 timeout/재시도와 "always run AI answer path" 계약

- **Proposal requirement**: P0-4. Chat/Research 스피너에 `UI_GENERATION_TIMEOUT_S` 초과 시 안내 + "재시도" 버튼(답변 폐기 아님).
- **Current pipeline evidence**: `ui/pages/research.py:277` `# Always run AI answer path alongside search (UX-007 §4.1)` — 검색 결과·citation card 렌더가 생성 완료에 의존 [2차 D-절]. 2차에서 검증자의 `curl` 1회가 진행 중 UI 생성과 경합해 결과를 흐렸을 가능성이 배제되지 않음 [2차 V2]. Chat ≈23분·Research ≈4~5분 미완료.
- **Conflict type**: CONFIRMED_CONFLICT — "재시도"가 이전 생성이 끝나기 전에 두 번째 생성을 띄우면 관측된 경합을 재현·악화한다. 또 검색 결과를 생성과 분리해 먼저 보여주는 변형은 UX-007 §4.1 의도와 충돌.
- **Reproduction status**: 의존성·미완료는 CONFIRMED. 동시 생성 악화는 PROBABLE [2차 V2].
- **Affected components**: `ui/pages/chat.py`, `ui/pages/research.py`, `core/generation.py::GenerationService.generate`, Ollama `llama-server` 프로세스.
- **Data and compatibility impact**: 데이터 불변. UX 계약(UX-007) 영향. 성능: 동시 생성 시 지연 악화.
- **Existing ADR or policy relation**: UX-007(문서 존재, 본문 미판독). ADR 여부 UNKNOWN → CON-012.
- **A: retain current behavior**: 무한 스피너 유지, timeout 없음(현행). 위험: 사용자가 "멈춤"과 "느림"을 구분 못함, PB-04 체감 지속.
- **B: minimal reinforcement**: **재시도 버튼 없이**, 스피너 텍스트에 경과 시간 + "생성 진행 중(모델이 큼)"만 표시(순수 표시, 재요청 안 함). 클라이언트 timeout은 넣지 않음. 동시 생성 위험 0.
- **C: isolated / feature-flag PoC**: `UI_GENERATION_ELAPSED_HINT` 뒤에서 B만. 재시도/timeout은 P0-4 하니스로 first-token·total을 측정해 "언제부터가 비정상인가" 기준이 생긴 뒤 별도 설계.
- **Required validation evidence**: P0-4 하니스의 first-token/total 분리 측정 + Ollama가 동시 요청을 어떻게 큐잉하는지 확인(2차 V2의 두 번째 `llama-server` 관측).
- **Decision owner**: HQ (UX 계약) — 측정은 CUE.
- **Decision status**: **HOLD** — B(경과 시간 표시만)는 APPROVE FOR POC 수준으로 가능. 재시도·클라이언트 timeout은 P0-4 측정 결과 전까지 HOLD.

## CON-006 — Smith 결과를 Citation으로 승격

- **Proposal requirement**: P1-3(b). `search_reference` 결과를 citation 목록에 `source_type="reference"`(위계 하위)로 전달.
- **Current pipeline evidence**: Smith는 `_inject_smith_context()`로 `<reference>` 블록을 LLM 컨텍스트에 넣을 뿐, `render_citation_card`로 전달되지 않는다(코드 확인) [2차 Q8]. `Citation` dataclass에 주/보조 출처 구분 필드 없음 [1차 §3.2]. `nae_ref_v1` payload에 `review_status`/`usage_permission`/`copyright_status`/`citation_policy`가 아예 없음 [2차 Q10]. 주입 텍스트에 OCR 열화 [2차 Q8].
- **Conflict type**: CONFIRMED_CONFLICT — citation에 넣으려면 (a) `Citation`에 필드 추가(guardrail #5 backward-compat 위반) 또는 기존 필드 오버로드, (b) 채울 rights 메타가 없음, (c) OCR 텍스트가 인용문으로 노출.
- **Reproduction status**: CONFIRMED [2차 Q8/Q10].
- **Affected components**: `ui/pages/chat.py::_inject_smith_context`, `NAE/reference_retrieval_adapter.py`, `core/retrieval.py::Citation`/`CitationBuilder`, `ui/components/citation_card.py`.
- **Data and compatibility impact**: `Citation` 필드 추가 시 직렬화·테스트 호환성. rights 필드 부재 → 인용 시 권리 표기 불가. OCR 텍스트 인용 시 품질 저하.
- **Existing ADR or policy relation**: ADR-013(Qdrant 분리), Smith reference 트랙([메모리: Reference Dictionary TSU Mismatch] — reference 전용 임베딩 경로) 관련. ADR 본문 UNKNOWN → CON-012.
- **A: retain current behavior**: Smith는 컨텍스트에만, citation 미표시(현행). 위험: 답변에 쓰인 사전 텍스트가 화면에서 추적 안 됨(PB-08).
- **B: minimal reinforcement**: `Citation` 변경 없이, Smith 주입 블록에 **출처 라벨을 더 명확히**(현재도 "보조 자료(Smith Bible Dictionary)" 안내문 있음 [2차 Q8]) + 답변 하단에 별도 "참고 사전" 섹션(citation card 아님, 단순 목록)으로 volume/page 표시. OCR 경고 배지.
- **C: isolated / feature-flag PoC**: `SMITH_REFERENCE_PANEL` 뒤에서 B. citation card 모델은 손대지 않음.
- **Required validation evidence**: `nae_ref_v1` rights 필드 확보 계획(PB-09) + Smith가 답변 품질에 기여하는지 정량(P1-3 PoC).
- **Decision owner**: HQ (citation 모델·NAE 경계) + C1 Review.
- **Decision status**: **HOLD** — B(별도 참고 패널, Citation 무변경)만 APPROVE FOR POC 후보. Smith를 정식 Citation으로 만드는 것은 PB-09 해소 전까지 HOLD.

## CON-007 — subset 정답축과 chunk-level ground truth 부재

- **Proposal requirement**: P1-1. subset 판정에 "알려진 정답 청크가 top-k에 존재" 축 사용.
- **Current pipeline evidence**: `gold_queries.json`에 chunk/document ID 필드 없음, `expected_documents`는 자연어 [2차 Q13/V10]. `output/eval/*` chunk ID가 현재 corpus에 0/8 [2차 Q14]. → chunk 단위 정답을 담은 파일이 현재 없음.
- **Conflict type**: COMPATIBILITY_CONSTRAINT — subset이 새 아티팩트(청크 단위 정답)를 필요로 하며 기존 자산으로는 못 만든다.
- **Reproduction status**: CONFIRMED [2차 Q13/Q14].
- **Affected components**: `tests/gold_queries.json`(불변), 신규 `tests/mat_subset_ground_truth.json`, `scripts/run_rag_eval.py`(대조 로직).
- **Data and compatibility impact**: additive. 기존 gold/eval 불변. 위험: 정답 청크를 사람이 지정 → 지정 편향.
- **Existing ADR or policy relation**: eval 계약 관련 ADR UNKNOWN → CON-012. [메모리: dataset_registry / DatasetRegistry 계획] 참고.
- **A: retain current behavior**: `expected_books`만으로 대조(현행 gold 스키마). 위험: A2류(정확 문구 누락)를 subset이 못 잡음 → P0-1 검증 불가.
- **B: minimal reinforcement**: MAT subset 13±건에 대해 **사람이 정답 청크 1~3개씩 지정**한 sidecar ground-truth 파일 + 지정 근거(원문 인용) 기록. `expected_books`와 병용.
- **C: isolated / feature-flag PoC**: subset·ground-truth를 별도 파일로 만들고, 현행 legacy 경로 baseline을 측정해 subset이 flag on/off를 변별하는지 먼저 확인(S1).
- **Required validation evidence**: subset baseline 측정 + 변별력(같은 질의에 대해 flag on/off가 다른 판정을 내는가).
- **Decision owner**: CUE (eval subset 저작) + HQ 승인(평가 계약).
- **Decision status**: **HOLD** — ground-truth 파일 저작은 진행 가능(APPROVE FOR POC), P0-1 기본값 전환의 근거로 쓰는 것은 변별력 확인(S1) 후.

## CON-008 — fail-soft 배지와 UI 집행 — **RESOLVED (2026-09-10)**

- **Proposal requirement**: P1-4(C안). ClaimGuard 예외 시 답변에 "자동 검증 실패" 배지(차단 아님).
- **Current pipeline evidence**: **관측 완료(2026-09-10)** — 기본 모델 대신 `llama3.1:8b`로 생성을 완료시켜 DOM 수준에서 확인했다(`docs/audit/DBMA-NAE-2ND-VERIFICATION-2026-09-09.md` 부록 B).
  - 유도 질의로 `risk_level="high"`, `matched_terms=["유일"]`, `absolute_claim_blocked=true` 실제 발생.
  - assistant 메시지 DOM 출현 순서: 아바타 → **답변 본문 3단락(트리거 문장 포함)** → 저신뢰 caption → `주장 검증: 전체 코퍼스 비교 불가 — '최초/유일' 주장 차단 (no_full_corpus_comparison_exists)` → 출처 expander.
  - 즉 **차단하지 않는다.** `ui/pages/chat.py`가 `st.write_stream()`으로 답변을 전부 출력한 **뒤** `to_result()`로 판정을 읽고 `_render_claim_guard_warning()`이 `st.caption` 1줄을 덧붙이는 구조이며, 답변을 가로채거나 재생성하는 경로가 없다.
  - `dev/dbma-engine` tip(`5146fa7`)의 `ui/pages/chat.py:557-566`에서 동일 구조를 재확인했다.
  - **부수 관측**: 라이브 경로는 `absolute_claim_blocked or scope_qualifier_required` 조건을 걸지만 히스토리 재생 경로(`chat.py:657-658`)는 **조건 없이** caption을 그린다. `risk_level="none"`·`reason=""` 턴이 복원되면 내용 없는 `주장 검증:` 줄이 표시된다.
  - `_run_claim_guard`의 판정 자체와 fail-open(예외 시 `RiskLevel.NONE`)은 종전대로 CONFIRMED [2차 Q15].
- **Conflict type**: **RESOLVED** (구 UNVERIFIED_CONFLICT) — 현행 처리 방식이 확정됐다. 남는 것은 설계 판단이다: 현행이 이미 caption 1줄을 표시하므로 (C)의 "배지"는 **신설이 아니라 기존 caption의 문구·시인성 변경**으로 재정의해야 이중 표시를 피한다.
- **Reproduction status**: 판정·fail-open CONFIRMED; **UI 집행 CONFIRMED** (2026-09-10 재현 절차와 DOM 덤프가 `docs/audit/DBMA-NAE-2ND-VERIFICATION-2026-09-09.md` 부록 B에 기록됨).
- **Affected components**: `core/generation.py::_run_claim_guard`, `ui/pages/chat.py`(답변 렌더), `ClaimGuardResult` 소비부.
- **Data and compatibility impact**: 데이터 불변. UX 영향 평가 가능 — 현행은 답변 아래 caption 1줄이므로, 배지 추가 시 **동일 정보가 두 번** 표시될 수 있다.
- **Existing ADR or policy relation**: ClaimGuard 정책 관련 ADR UNKNOWN → CON-012. [메모리: RAG Security Pre-Deploy].
- **A: retain current behavior**: fail-open, 무배지(현행). 위험: 가드 실패가 사용자에게 안 보임(PB-07).
- **B: minimal reinforcement**: 우선 **관측만** — P0-3 audit 채널에 `claimguard_error` 이벤트를 남겨 실패율을 측정(사용자 UI 무변경). 배지 여부는 그다음.
- **C: isolated / feature-flag PoC**: `CLAIMGUARD_FAIL_POLICY` 3옵션을 플래그로 둔다. ~~선행 과제였던 렌더 관측~~은 완료됐으므로 S5 선행조건이 해제된다. 단 설계는 "배지 신설" 대신 **기존 caption 경로 재사용**을 전제로 다시 작성해야 한다.
- **Required validation evidence**: ~~UI 렌더 관측~~ 충족(2026-09-10). 남은 것은 P0-3 채널의 `claimguard_error` 실패율뿐.
- **Decision owner**: HQ (안전 정책).
- **Decision status**: **UI 집행 관측 조건 해제됨.** B(audit-only 관측)는 P0-3에 포함해 진행. 배지 설계는 "기존 caption 재사용" 전제로 재작성 필요. **차단 정책 자체는 여전히 HOLD** — 기술적 미지가 아니라 HQ 안전 정책 판단 사항이다.

## CON-009 — feature flag 토글의 프로세스 반영 가정

- **Proposal requirement**: P0-1/P0-2/P0-3이 신규 플래그를 프로세스 수준에서 켜고 끄면 즉시 반영된다고 가정.
- **Current pipeline evidence**: `get_shared_query_processor()`는 processor를 캐시하고 `tsu_manifest.json`의 `dataset_sha256`가 바뀔 때만 재생성한다 [2차 §"query→답변"]. `hybrid_candidate_pipeline.is_enabled()`는 `os.environ`을 호출 시점에 읽는다 [2차 §활성경로판정]. `core/feature_flags.py`에는 모듈 상수 `SPRINT2_FEATURES = True`도 있다 [1차 §3.3].
- **Conflict type**: COMPATIBILITY_CONSTRAINT — 어떤 플래그는 호출 시점 조회(반영 즉시), 어떤 값은 모듈 로드 시 상수(재기동 필요), 캐시된 processor는 플래그 변경을 모를 수 있다. 제안이 이 차이를 다루지 않음.
- **Reproduction status**: 캐시 동작 CONFIRMED [2차]. 플래그 전파 갭은 PROBABLE(미실험).
- **Affected components**: `ui/state/query_processor.py::get_shared_query_processor`, `core/feature_flags.py`, 각 제안의 플래그 게이트 지점.
- **Data and compatibility impact**: 데이터 불변. 위험: 플래그를 켜도 캐시된 processor 때문에 다음 dataset 변경·재기동까지 반영 안 됨 → "롤아웃했는데 안 바뀜"·"롤백했는데 안 돌아옴" 혼란.
- **Existing ADR or policy relation**: feature flag 구조 관련 ADR UNKNOWN → CON-012.
- **A: retain current behavior**: 플래그를 `is_enabled()`처럼 **호출 시점 조회**로만 구현하고, processor 재생성 조건에 flag 상태를 포함하지 않음. 위험: processor 내부에 캐시된 로직은 안 바뀜.
- **B: minimal reinforcement**: 각 신규 플래그를 **요청마다 조회**하도록 설계(모듈 상수·`__init__` 캐시 금지). `get_shared_query_processor`의 fingerprint에 `flag_state`를 추가 제안(별도 승인). acceptance에 "플래그 토글 후 재기동 없이 다음 질의부터 반영" 명시.
- **C: isolated / feature-flag PoC**: S2/S3 테스트에 "flag on → 질의 → flag off → 질의"가 재기동 없이 각각 다른 결과/로그를 내는지 검증 추가.
- **Required validation evidence**: 플래그 토글 → 즉시 반영 테스트(재기동 없이).
- **Decision owner**: CUE (구현 세부).
- **Decision status**: **APPROVE FOR POC** — B(요청마다 조회)를 설계 원칙으로 채택하고 S2/S3에 토글 테스트 포함. fingerprint 변경은 별도 승인.

## CON-010 — bench_dir 앵커링과 미감사 스크립트

- **Proposal requirement**: P1-5. 상대 `bench_dir`을 `BASE_DIR` 기준으로 재해석.
- **Current pipeline evidence**: `DEFAULT_BENCH_DIR` cwd 상대는 CONFIRMED [2차 §실행위치]. `scripts/` 97개·`.automation/` 8,277 파일 중 cwd 상대 동작에 의존하는 것이 있는지 미확인 [1차 U3/U15].
- **Conflict type**: UNVERIFIED_CONFLICT — 앵커링이 어떤 스크립트를 깨는지 확인할 수 없다.
- **Reproduction status**: 관측된 파손 없음(모든 검증이 `os.chdir` 후 수행).
- **Affected components**: `core/config.py:72`, `DEFAULT_TSU_DATASET_PATH`·`DEFAULT_SEARCH_TELEMETRY_PATH` 등 파생 상수, 이를 쓰는 모든 스크립트.
- **Data and compatibility impact**: 앵커링이 옳게 되면 무결성 **개선**(잘못된 위치 쓰기 방지). 잘못되면 의도적으로 cwd 상대를 쓰던 스크립트가 다른 파일을 봄.
- **Existing ADR or policy relation**: 없음 추정 → CON-012.
- **A: retain current behavior**: cwd 상대 유지, 운영 규약으로 "항상 `/Users/David/DBMA`에서 실행"을 문서화. 위험: 규약 위반 시 조용한 오작동.
- **B: minimal reinforcement**: 앵커링을 `BENCH_DIR_ANCHOR_BASE`(기본 off) 뒤에 두고, 켜기 전에 `grep -rn "bench_dir\|output/bench\|DEFAULT_BENCH_DIR\|DEFAULT_TSU_DATASET_PATH" scripts/ .automation/`로 의존 스크립트 목록을 만든 뒤 개별 확인.
- **C: isolated / feature-flag PoC**: 플래그 on 상태로 `os.chdir('/tmp')` 후 전체 테스트 + 핵심 스크립트(`build_tsu_dataset.py`, `run_rag_eval.py`) 실행이 올바른 경로를 쓰는지 확인.
- **Required validation evidence**: `scripts/`·`.automation/` 경로 의존성 grep 결과 + 플래그 on 회귀.
- **Decision owner**: CUE (구현) + HQ(스크립트 영향 승인).
- **Decision status**: **DEFER** — `scripts/` 감사가 현재 세션 범위 밖(1차 U15). 감사 후 재등록.

## CON-011 — sidecar에 권리 상태 단정

- **Proposal requirement**: P0-2 초안. sidecar에 `rights: {copyright_status, usage_permission}` 포함.
- **Current pipeline evidence**: 매튜 풀 EPUB DC `rights=[]`(빈 값) [1차 §3.4]. 상업 출판물(크리스챤다이제스트, ISBN 978-89-447-8472-9). `tsu_dataset.jsonl`에 rights 필드 없음 [1차 §3.4]. 프로젝트는 권리 미확인 자료를 `citation_policy_status = AUTHORITATIVE_SOURCE_MISSING`으로 표시하는 관례가 있음(`nae_tsu_v1` 3,319건 100%) [2차 Q10].
- **Conflict type**: CONFIRMED_CONFLICT — 근거 없는 권리 상태를 sidecar가 단정하면, 저작권이 살아있는 상업 번역서를 특정 사용 권한이 있는 것처럼 표시할 수 있다. 프로젝트 관례(`AUTHORITATIVE_SOURCE_MISSING`)와도 배치.
- **Reproduction status**: CONFIRMED [1차 §3.4, 2차 Q10].
- **Affected components**: (신규) sidecar 스키마, `CitationBuilder`, citation card 표시.
- **Data and compatibility impact**: 저작권 정확성 위험(가장 큼). rollback = sidecar에서 rights 키 제거.
- **Existing ADR or policy relation**: ADR-021(works.yaml Option C, `works: []`) [1차 §1.7], 권리/인용 정책 ADR UNKNOWN → CON-012. [메모리: RAG Security Pre-Deploy, ADR-030 governance].
- **A: retain current behavior**: rights 미표시(현행). 위험: 사용자가 인용 시 권리 상태를 모름 — 그러나 **틀린 정보를 주는 것보다 안전**.
- **B: minimal reinforcement**: sidecar에 rights를 넣되 값은 항상 `copyright_status: "unknown"`, `citation_policy_status: "AUTHORITATIVE_SOURCE_MISSING"`(프로젝트 관례 그대로) + `publisher`/`isbn`만 사실로 표시. "권리 상태 미확인 — 인용 전 확인 필요" 문구.
- **C: isolated / feature-flag PoC**: rights 없이 서지(title/author/publisher/isbn)만 fill하는 것이 제안서 첫 slice. rights는 별도 항목.
- **Required validation evidence**: 이 EPUB의 실제 라이선스/사용 허가 문서(현재 없음) — 확보 전까지 rights 단정 금지.
- **Decision owner**: HQ (저작권 정책).
- **Decision status**: **REJECT** — sidecar에 임의 rights 값을 넣는 설계는 기각. 제안서 첫 slice는 이미 rights를 제외함. 필요 시 B(관례 그대로 `AUTHORITATIVE_SOURCE_MISSING` 표기)로 별도 제안.

## CON-012 — ADR 본문 미확인 상태에서의 retrieval/citation/telemetry/NAE 변경

- **Proposal requirement**: 제안서 전체(P0-1 retrieval, P0-2 citation, P0-3 telemetry, P1-3 NAE 경계)가 코드 변경을 전제.
- **Current pipeline evidence**: `docs/architecture/ADR-001` ~ `ADR-033` 33건이 존재하나, 1차·2차 점검은 **개수와 일부 번호(ADR-003 legacy 격리, ADR-013 Qdrant 분리, ADR-021 works.yaml)만 확인**하고 본문은 판독하지 않았다 [1차 §1.2, §1.7]. retrieval 스코어링·citation 모델·telemetry·NAE 경계를 규율하는 Approved ADR이 있는지, 있다면 그 조항이 무엇인지 알 수 없다.
- **Conflict type**: UNVERIFIED_CONFLICT — Architecture Freeze Rule(Approved ADR은 새 Amendment/Revision 없이 우회 금지)의 적용 대상이 있는지 확인 불가.
- **Reproduction status**: N/A (문서 판독 미수행).
- **Affected components**: 제안서의 모든 P0/P1.
- **Data and compatibility impact**: 미확인. Approved ADR과 충돌하는 변경을 구현하면 거버넌스 위반.
- **Existing ADR or policy relation**: **이 항목 자체가 그 관계를 확인하라는 것.** CUE Operating Policy: "작업 명령서와 Approved ADR이 충돌하는 것을 발견하면 구현을 중단하고 확인을 받는다."
- **A: retain current behavior**: ADR 판독 없이 진행하지 않음 — 어떤 P0/P1도 구현 착수 전 관련 ADR 확인.
- **B: minimal reinforcement**: 착수 전 `docs/architecture/ADR-*.md`에서 retrieval / citation / query parsing / telemetry / feature flag / NAE bridge / Smith / ClaimGuard 키워드로 관련 ADR을 식별하고, 각 P0/P1의 "Existing ADR relation" 칸을 실제 조항으로 채운다. 충돌 시 새 ADR(supersedes 관계 명시) 초안.
- **C: isolated / feature-flag PoC**: N/A — 이건 문서 검토 과제.
- **Required validation evidence**: ADR-001~033 중 관련 문서의 Status(Approved/Proposed)와 해당 조항.
- **Decision owner**: HQ + C1 (아키텍처 거버넌스).
- **Decision status**: **HOLD (blocking)** — 이 항목이 해소되기 전에는 어떤 P0/P1도 구현 착수 불가. 제안서·본 Register는 계속 진행 가능(계획 산출물).

---

# Decisions Deferred

> 구현 전에 추가 확인이 필요한 항목. 확인 주체와 필요한 증거를 함께 기록한다.

| 항목 | 필요한 확인 | 주체 | 근거 |
|------|-------------|------|------|
| **CON-012 선결**: retrieval/citation/telemetry/NAE 경계를 규율하는 Approved ADR 식별 및 조항 대조 | ADR-001~033 본문 판독, 각 P0/P1의 ADR relation 실제 조항 기입 | HQ + C1 | 1차 §1.2 (본문 미판독) |
| **S0 재현**: 2차 보고서 수치(A2 `chunk_00280` top-5 누락, citation `['문서']`, 생성 미완료)가 현재 환경에서 재현되는가 + worktree ↔ live 코드 동일성 | 읽기 전용 재실행 | CUE | 1차 §5.3, 2차 전반 |
| **CON-001 → P0-1 기본값 전환**: `_tokenize` 2-gram keyword가 BM25 문서 통계와 어떻게 상호작용하며, EN·scripture 질의를 회귀시키지 않는가 | P1-1 subset 구축(CON-007) → S3 A/B | HQ 결정 / CUE 측정 / C1 검토 | 2차 §BM25, 1차 §3.3 |
| **CON-003 → verse_mapping locator**: `verse_mapping` 생성 경로와 오매핑률 | 정제/색인 단계 코드 판독 + 표본 대조 | CUE | 2차 Q4/Q5 |
| **CON-005 → 생성 timeout/재시도**: first-token vs total generation 분리 수치, Ollama 동시 요청 큐잉 동작 | P0-4 하니스(측정 전용) | HQ (UX) / CUE (측정) | 2차 D-절, V2 |
| **CON-006 → Smith citation**: `nae_ref_v1` rights 필드 확보 계획, Smith가 답변 품질에 기여하는지 | PB-09 governance + P1-3 PoC | HQ + C1 | 2차 Q8/Q10 |
| **CON-008 → ClaimGuard 배지/차단**: 생성 완료 환경에서 현행 UI가 `absolute_claim_blocked`를 어떻게 렌더하는가 | S5 선행 관측 | HQ (안전) | 2차 V3 |
| **CON-010 → bench_dir 앵커링**: `scripts/`·`.automation/`의 cwd 상대 경로 의존 목록 | 경로 의존성 grep + 개별 확인 | CUE | 1차 U15/U3 |
| **PB-04 원인**: 지연이 load / retrieval / first-token / decode 중 어느 단계인가 | P0-4 하니스 (모델 교체·튜닝은 이 결과 전까지 Deferred) | CUE 측정 / HQ 판단 | 2차 V2 |
| **NAE 미색인 4,441건**: 어느 파이프라인 단계가 `review_status != verified`를 필터했는가 | `NAE/review/`·`NAE/pipeline/` 판독 | CUE | 2차 V9 |
| **D안(대규모 교체) 전체**: vector DB 전환, NAE bridge 기본 활성화, 전체 재청킹·재색인, 생성 모델 교체, LoRA | 위 확인들이 모두 끝나고, 최소 변경(P0/P1)으로 해결 불가함이 정량적으로 입증된 뒤에만 D안으로 재상정 | HQ | Conflict Protocol §5 (D안은 현 권고 아님) |

---

## 요약

- **등록된 충돌 12건** (2026-09-10 갱신): CONFIRMED_CONFLICT 4 (CON-003, CON-005, CON-006, CON-011) / COMPATIBILITY_CONSTRAINT 5 (CON-001, CON-002, CON-004, CON-007, CON-009) / UNVERIFIED_CONFLICT 2 (CON-010, CON-012) / **RESOLVED 1 (CON-008)**. 종전 표기는 COMPATIBILITY_CONSTRAINT를 4로 적고 5건을 나열해 합이 맞지 않았으므로 함께 정정한다.
- **즉시 구현 대상 없음.** 제안서의 "첫 vertical slice"(P0-2 축소판)조차 CON-002 검증(S4)과 CON-012(ADR 확인) 선결이 필요하다.
- **차단(blocking) 항목**: CON-012 — 관련 Approved ADR을 확인하기 전에는 어떤 P0/P1도 착수 불가.
- **제안서에서 이미 반영된 완화**: CON-003(verse_mapping locator)·CON-011(rights 필드)은 첫 slice에서 제외됨.
- **APPROVE FOR POC**(플래그·격리 범위 내 검증 착수 가능, 기본값 전환은 별도): CON-002, CON-004, CON-009.
- **HOLD**: CON-001, CON-003, CON-005, CON-006, CON-007, CON-008, CON-012.
- **REJECT**: CON-011(sidecar 임의 rights 단정).
- **DEFER**: CON-010.

*본 문서는 충돌 등록·분석이며, 어떤 코드·설정·데이터·인덱스·서비스·플래그도 변경하지 않았다.*
