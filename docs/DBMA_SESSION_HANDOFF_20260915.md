# 세션 이양 문서 — 2026-09-15

- 작성자: CUE (이양하는 세션)
- 대상: 이 작업을 이어받는 다음 세션
- 브랜치: `dev/dbma-engine` · 이양 시점 HEAD `2f642f12`
- **읽는 순서:** §1 → §5(함정) → §4(대기 중 결정) → 나머지

---

## 1. 지금 어디에 있는가

한 문장: **프로덕션 코퍼스를 의도적으로 비운 뒤 퍼블릭 도메인 자료로 최소 재구성했고,
그 과정에서 드러난 파이프라인 결함 3건을 고쳤으며, 무료 배포와 기능 격차 타개를 위한
설계안 2건이 HQ 결정을 기다린다.**

이 세션은 "DBMA/NAE가 상업 제품 대비 적절한가"라는 질문에서 시작해 다음 순서로 진행했다.

```
상업 제품 벤치마킹
  → 코퍼스가 사실상 비어 있음을 발견 (1,363 TSU / 출처 1권)
  → 복구 계획 수립 → HQ가 영구 취소(CANCELLED) 결정
  → 전체 데이터 리셋 (배포 전 상태로)
  → 퍼블릭 도메인 기본 코퍼스 적재 (스펄전 4종)
  → 적재 중 결함 발견 → 수정 3건
  → 무료 배포 방안 + 기능 격차 타개 설계
  → HQ 원칙 지시(예화 생성 금지) 반영
```

---

## 2. 검증된 현재 상태 (VERIFIED)

### 2.1 코퍼스

```
output/bench/tsu_dataset.jsonl   6,380 TSU / 출처 4건
  설교 | 2,637 | Spurgeon_Metropolitan_Tabernacle_Pulpit_Vol02.txt
  설교 | 2,601 | Spurgeon_Metropolitan_Tabernacle_Pulpit_Vol01.txt
  설교 |   609 | Spurgeon_Till_He_Come.txt
  기타 |   533 | Spurgeon_Lectures_to_My_Students.txt   ← 설교학, 올바른 분류
```

전량 **퍼블릭 도메인**(C.H. Spurgeon, 1834-1892). 출처는
`~/NAE_CORPUS_RAW/raw/archive_org/sermons/`(로컬 기보유, 신규 다운로드 없음).
같은 경로에 즉시 추가 가능한 퍼블릭 도메인 자료 **63종**이 더 있다(MTP 40여 권,
NPSP 6권, Maclaren *Expositions* 17권, Whitefield 4권, Broadus, Dargan, Keach).

**메타데이터는 여전히 비어 있다** — `.txt`라 내장 메타데이터가 없다(§4.1 참조).

### 2.2 보존 자산 (건드리지 말 것)

| 자산 | 크기 | 비고 |
|---|---:|---|
| `NAE/corpus/` | 2.6G | Dagg·Fuller 8권·Hiscox·Smith 4권 정경화 + 인간 검토 승격분. **다른 세션이 지금도 작업 중** |
| `backups/` | 15G | 사고 전 TSU 89,737건 유일본 포함 |
| `~/Library/…/Library_Calibre` | 115G | 원본 장서 6,114파일 |
| `~/NAE_CORPUS_RAW` | 43G | archive.org 수집분 |

### 2.3 런타임

- **Streamlit 앱 정지 상태** (이양 시점). 재시작:
  `cd /Users/David/DBMA && /Users/David/envs/dbma311/bin/streamlit run dbma_ui.py --server.headless true --server.port 8501`
- Ollama 정상, `bge-m3:latest` · `llama3.1:8b` 존재
- 작업트리 깨끗 (무관한 로컬 초안 1건만 untracked)

---

## 3. 이번 세션에 바꾼 것

| 커밋 | 내용 | 왜 |
|---|---|---|
| `2f642f12` | 설교 프롬프트의 **예화 생성 요구 제거** | HQ 절대 규칙. §5.1 참조 |
| `9af2b980` | 설교 산출물 파이프라인 설계 v1 | 매트릭스 ❌ 5개의 공통 뿌리 해소안 |
| `b1604449` | `backfill_doc_type.py` `--reclassify` 모드 | 분류 규칙 개선을 기존 문서에 반영할 경로가 없었음 |
| `82e9c0d3` | **설교 유형 영어 키워드 추가** (`sermons`/`pulpit`/`homily`) | 5개 유형 중 설교만 영어 키워드 0개 |
| `6dadcc21` | doc_type 영향 목록 + `scripts/doctype_impact_report.py` | C1 조건 C3 산출물 |
| `6b5ef9a0` | C1 재요청 001 | 미답변 Q1 + Q2 잔여 |
| `3fedb4c0` | C1 결과 접수 + **CUE 대조 검증** | C1 조건 1건 오진 반박 |
| — | EPUB/HTML 메타데이터 추출 결함 수정 | PDF·DOCX만 구현돼 있었음 |
| — | 기본 코퍼스 적재 · 전체 데이터 리셋 | |

데이터 변경(코퍼스·registry·색인)은 **`.gitignore` 범위라 커밋되지 않는다**
(`data/`, `output/`, `chroma_db/`). 커밋 이력만 보면 데이터 상태를 알 수 없으니
§2를 실제로 확인할 것.

---

## 4. 대기 중인 결정 — 이양의 핵심

### 4.1 C1 재요청 회신 대기 (진행 중)

`docs/DBMA_SIDECAR_METADATA_C1_REREQUEST_001.md` — HQ가 C1에 전달 완료, 회신 대기.

- **RQ-1**: 사이드카 3키 스키마가 "Metadata Model 변경"인가 "Model 무변경 + 새 데이터
  소스"인가. 후자면 이번 C1 Review 트리거 자체가 과잉이었는지도 판정 요청.
- **RQ-2**: 비어 있지 않은 **쓰레기 내장 값**(`Untitled`, 제작 도구명, mojibake)이
  정확한 사이드카를 이기는 경우 처리 방침.

회신 오면 → 설계 확정 → HQ 승인 → 구현. **그 전까지 스텁·스키마·데이터 포함
선행 구현 금지**(Evidence Before Promotion Rule).

이것이 풀려야 인용 메타데이터(⚠️ 행)가 해소되고, 예화 검색의 출처 표시가 의미를 갖는다.

### 4.2 무료 배포 — HQ 결정 4건

`docs/NAE_FREE_DISTRIBUTION_PLAN_v1.md` §8.

1. **한글 성경 본문 경로** — 대한성서공회 허락 문의 / 공개 번역본 / 사용자 직접 투입
2. **서명** — 무서명 유지(0원) / Apple Developer(연 $99)
3. **동봉 서재** — NAE 퍼블릭 도메인 트랙 포함 여부
4. **지원 정책** — as-is + 단일 비동기 채널

배포 차단 항목 5건 중 **B-1(빈 코퍼스에서 근거 없는 설교 생성)** 이 여전히 미해결이다.
현재 코퍼스가 비어 있지는 않으나, **자료 0건일 때 생성을 막는 로직 자체가 없다.**

### 4.3 파이프라인 설계 — HQ 결정 4건

`docs/DBMA_SERMON_ARTIFACT_PIPELINE_DESIGN_v1.md` §10.

1. 설계 방향(설교 1급 객체화 → 파생) 승인 여부
2. §7 "하지 않을 것" 동의 — 특히 **설교 영상 클립 포기**
3. P1 착수 전 C1 Review 여부 (새 Architecture Layer에 해당)
4. **P2(강단 전달 모드)를 먼저 빼서 단독 출시할지** ← CUE 권고안

### 4.4 별건 백로그

- `주석` 유형의 영어 키워드가 `commentary` 하나뿐 — 다른 유형 커버리지 점검
- 설교 경로도 `_GROUNDING_DIRECTIVE` 수준 근거 강제 필요. 단 생성 출력 전반을
  바꾸므로 **groundedness 베이스라인 재측정 동반** 필요
- Maclaren *Expositions* 17권의 본문 기반 doc_type 재현율 확인(적재 시)

---

## 5. 함정 — 모르면 사고 난다

### 5.1 예화 생성은 절대 금지 (HQ 원칙)

> **"예화는 절대 생성하지 않아야 한다. 없으면 없는대로 설교 원고를 신앙양심대로
> 작성해야 한다."** (HQ, 2026-09-15)

설계 선택이 아니라 **제약**이다. 특히:

- 예화 검색 결과 0건은 **오류가 아니라 정상 종료 상태**다. **생성으로 폴백하지 마라.**
- "예화 자리가 비어 보인다"는 이유로 채우지 마라.
- 지어낸 예화는 목회자가 회중 앞에서 사실로 전달하게 되므로 되돌릴 수 없다.

`core/generation.py::_NO_FABRICATED_ILLUSTRATION_DIRECTIVE`가 개요·확장 두 프롬프트에
배선돼 있고, `tests/test_sermon_no_fabricated_illustration.py` 8건이 지킨다.
**이 테스트를 우회하거나 완화하지 마라.**

### 5.2 코퍼스 작업 전 반드시 앱을 정지시킬 것

`core/background_index_builder.py`가 **5초 주기**로 `reconcile_pending()`을 호출하며
registry와 TSU 데이터셋을 쓴다. 앱이 떠 있는 채로 코퍼스/registry를 건드리면 경쟁이
발생해 오염된다 — **2026-09-07에 실제로 발생한 사고**다
(`cleanup_phantom_registry_entries.py` 주석에 기록).

```bash
ps aux | grep streamlit | grep -v grep     # 먼저 확인
```

### 5.3 `register_document()`는 기존 레코드를 갱신하지 않는다

`core/identity_registry.py:131` — 이미 등록된 `document_id`를 만나면 **기존 레코드를
그대로 반환**한다. 콘텐츠 해시가 같으면 `force_rechunk`로 재처리해도 registry
메타데이터(`doc_type` 등)는 바뀌지 않는다.

실측: 재처리 로그는 "유형 구분 완료: 설교"인데 registry는 `기타` 유지.

→ 분류 규칙을 바꾼 뒤 기존 문서에 반영하려면:
```bash
PYTHONPATH=/Users/David/DBMA ~/envs/dbma311/bin/python scripts/backfill_doc_type.py \
  data/제련완성본/registry/documents.json data/제련완성본 --reclassify        # dry-run
```
`--apply`를 붙이면 반영(저장 전 자동 백업). **기본 백필은 `doc_type=None`만 채우므로
`기타`는 건너뛴다.**

### 5.4 공식 venv는 `~/envs/dbma311`

시스템 `python3`에는 PyYAML이 없어 `core.config` import가 실패한다. 일부 `scripts/`는
`PYTHONPATH=/Users/David/DBMA`도 필요하다(`backfill_doc_type.py` 확인됨).

### 5.5 기존 실패 테스트 2건 — 당신 잘못이 아니다

```
tests/test_m2_source_registry_governance.py::test_raw_path_checksum_target_files_exist
tests/test_m2_source_registry_governance.py::TestValidatorIntegration::test_int_01_validator_passes
```

`NAE/corpus/raw/`가 `.gitignore` 대상이라 일부 원본이 이 머신에 없는 **환경 갭**이다.
`git stash` 대조로 사전 존재 확인 완료. 새 실패를 판단할 때 이 2건을 빼고 세라.

### 5.6 C1 보고를 검증 없이 믿지 말 것

이번 세션에서 실측된 C1 오류 2종:

- **오진**: 최우선 조건으로 "빈 문자열 → `None` 강등 필요"를 제시했으나, 이미 7개 지점
  전부 `.strip() or None`으로 구현돼 있었다. **호출부만 읽고 함수 본문을 안 읽은** 것.
  인용한 행 번호는 전부 정확했으므로 저장소 오인과는 다른 유형이다.
- **질문 치환**: 요청서 Q1(거버넌스 질문)에 D-1(설계 항목)로 답하고 GREEN을 줬다.

→ 번호 붙인 질문을 냈으면 **답변이 그 질문에 대응하는지 1:1로 대조**하고, "이 코드가
X를 안 한다"는 주장은 **함수 본문을 직접 열어** 확인할 것.

### 5.7 브랜치를 다른 세션과 공유 중

`dev/dbma-engine`에 다른 세션이 NAE 인간 검토 배치(`batch_0033~0035`)를 계속 커밋하고
있다. 착수 전 `git pull` 하고, 건드릴 파일이 origin에서 이미 바뀌지 않았는지 확인할 것.

이번 세션에 실제로 겪은 사고: 다른 세션이 커밋한 파일
(`docs/DBMA_SAAS_DEPLOYMENT_PROPOSAL_v1.md`)이 작업트리에서 삭제된 상태로 나타나
`git checkout HEAD --`로 복원했다.

### 5.8 데이터는 커밋되지 않는다

`.gitignore`가 `data/`, `output/`, `chroma_db/`를 덮는다. 코퍼스·registry·색인 상태는
**커밋 이력으로 추적 불가**하며 이 머신의 실제 파일이 유일한 진실이다. 되돌릴 지점은
`backups/` 안의 타임스탬프 디렉터리다.

---

## 6. 하지 말 것

| 금지 | 이유 |
|---|---|
| 예화 LLM 생성 (§5.1) | HQ 절대 규칙 |
| 앱 켠 채 코퍼스/registry 조작 (§5.2) | 리컨사일러 경쟁 → 오염 |
| `NAE/corpus/`, `backups/` 삭제·정리 | 재생성 불가 자산, 다른 세션 작업 중 |
| 상용 전자책을 기본 코퍼스에 적재 | 무료 배포 시 저작권 침해 |
| 사이드카 메타데이터 선행 구현 | C1 GREEN + HQ 승인 전 금지 |
| 복구 계획 v1 재개 | HQ가 **영구 취소** 결정 |
| `core/retrieval.py` 변경 | ADR-001 — 검색은 사후 필터로 해결 |

---

## 7. 다음에 할 일 (권고 순서)

1. **C1 회신 처리** — 오면 대조 검증(§5.6) 후 설계 확정
2. **B-1 안전장치** — 자료 0건일 때 설교 생성 차단. 배포 차단 항목이며 C1과 무관하게 진행 가능
3. **P2 강단 전달 모드** — LLM 불필요, 순수 렌더링, 매트릭스 1행 즉시 이동. 단 P1(artifact 저장) 선행 필요
4. 기본 코퍼스 확장 여부 결정 (퍼블릭 도메인 63종 대기)

---

## 8. 문서 지도

| 문서 | 내용 |
|---|---|
| `DBMA_SERMON_ARTIFACT_PIPELINE_DESIGN_v1.md` | **기능 격차 타개 설계 — 가장 중요** |
| `NAE_FREE_DISTRIBUTION_PLAN_v1.md` | 무료 배포 방안 + 배포 차단 5건 |
| `DBMA_SIDECAR_METADATA_C1_REREQUEST_001.md` | C1 재요청 (회신 대기) |
| `DBMA_SIDECAR_METADATA_C1_REVIEW_VERIFICATION_001.md` | C1 오진 반박 근거 |
| `DBMA_DOCTYPE_SERMON_KEYWORDS_REPORT_001.md` | 영어 키워드 선정 실측 |
| `DBMA_DOCTYPE_IMPACT_REPORT_001.md` | doc_type 영향 분석 + 언어 비대칭 발견 |
| `DBMA_LECTURES_PDF_TEXT_QUALITY_MEASUREMENT_001.md` | PDF 재적재 기각 근거 |
| `DBMA_METADATA_EXTRACTION_FIX_REPORT_001.md` | EPUB/HTML 추출 결함 수정 |
| `DBMA_BASELINE_CORPUS_LOAD_REPORT_001.md` | 기본 코퍼스 적재 기록 |
| `DBMA_CORPUS_RECOVERY_PLAN_v1.md` | **영구 취소됨** — 사고 경위 기록용으로만 |

도구:
- `scripts/doctype_impact_report.py` — doc_type 변경 영향 산출(읽기 전용)
- `scripts/backfill_doc_type.py --reclassify` — 분류 규칙 변경을 기존 문서에 반영
- `scripts/reset_for_beta.py` — 배포 전 데이터 초기화(삭제 전 자동 백업)
