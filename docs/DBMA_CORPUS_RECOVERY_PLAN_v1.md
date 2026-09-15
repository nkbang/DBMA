# DBMA Production Corpus Recovery Plan v1

**작성일:** 2026-09-15
**대상:** `output/bench/tsu_dataset.jsonl` (ADR-001 Production Retrieval Authority)
**성격:** 계획 문서 — 실행 전 HQ 승인 필요 (CLAUDE.md §예외: "Corpus 전체 Migration", "Production Registry 대량 변경")
**진행률:** 0%

> **상태: 영구 취소 (CANCELLED, 2026-09-15)** — HQ(사용자) 결정으로 본 복구 계획은
> 영구 취소되었다. Phase 0~4 어느 것도 착수하지 않는다. 이 문서는 사고 경위·원인 사슬·
> 백업 위치 기록용으로만 보존한다. 재개하려면 새 결정과 새 계획이 필요하다.

---

## 1. 상황 확정

### 1.1 소실 규모 (VERIFIED)

| 항목 | 사고 전 | 현재 | 감소 |
|---|---|---|---|
| TSU 레코드 | 89,737 | 1,363 | **-98.5%** |
| 출처 문서 | 122 | 3 (실질 1) | **-97.5%** |
| 데이터셋 크기 | 652 MB | 3.4 MB | -99.5% |
| Registry 문서 | ~107 | 4 | -96% |

현재 `data/RAW`에는 파일이 1개(`매튜 풀 ... 마태복음.epub`)뿐이며, Registry 4건 중
2건(`THEOLOGY_OF_GRACE.txt`, `은혜에_의한_구원_설교.md`)은 테스트 픽스처다.
**실질 프로덕션 코퍼스는 주석서 1권이다.**

### 1.2 원인 사슬 (VERIFIED — 코드·백업·커밋 교차 확인)

```
[1] ui/pages/processing.py::_render_ingestion_form()
    폴더 후보에 파이프라인 출력 폴더(data/제련완성본)가 포함됨
         ↓  2026-09-07 14:20 처리 실행
[2] 산출물(_pdf.md, _chunks.txt, _chunks_meta.json)이 신규 "문서"로 registry 등록
    → 유령 문서 98건 (대시보드 "정리된 자료 200 > 보유 문서 107")
         ↓
[3] core/index_orchestrator.py::reconcile_pending()이 ingest_status=="EXCLUDED"를
    무시 → 5초 주기 리컨사일러가 제외된 레코드를 데이터셋에 계속 재삽입
         ↓  cleanup_phantom_registry_entries.py / sync_tsu_dataset_to_registry.py
[4] 정리 작업 연쇄 실행 → 89,737 → 51,013 → 1,363
```

**중요:** [4]의 정리 스크립트 자체는 설계가 견실하다(2중 조건 판별, `registry_lock()`
내 직렬화, 실행 전 자동 백업). 이 백업들이 있었기에 현재 복구가 가능하다.
문제는 정리의 정확성이 아니라 **정리 후 정본 재구축이 수행되지 않은 채 방치된 것**이다.

### 1.3 실제 데이터 손실: **0건**

| 자산 | 위치 | 상태 |
|---|---|---|
| 사고 전 TSU 전량 | `backups/phantom_registry_cleanup_20260907_183948/tsu_dataset.jsonl` | ✅ 89,737건 / 652MB 보존 |
| 추출 텍스트·청크 | `backups/excluded_documents_20260907/` | ✅ 630파일 / 157MB 보존 |
| **원본 장서** | `~/Library/Application Support/David_Bang_Ministry_Archive/Library_Calibre` | ✅ 6,114파일 / 115GB |
| 보조 원본 | `~/NAE_CORPUS_RAW` | ✅ 1,832파일 / 43GB |
| 삭제된 RAW | `backups/deleted_raw_2026090{2,4,7}/` | ✅ 보존 |

**백업 TSU의 출처 122건을 라이브러리와 대조한 결과 122/122 전량 원본 확보.**
복구 불가 자산은 존재하지 않는다.

### 1.4 재발 방지 상태 (VERIFIED — 이미 조치됨)

| 근본 원인 | 수정 위치 | 상태 |
|---|---|---|
| 출력 폴더가 처리 후보에 포함 | `ui/pages/processing.py:246` `_blocked_dirs` + 산출물 서명 탐지 | ✅ 수정됨 |
| 리컨사일러가 EXCLUDED 무시 | `core/index_orchestrator.py:236` 필터 추가 | ✅ 수정됨 |

두 가드가 모두 살아 있으므로 **복원 직후 재오염되지 않는다.** 이것이 복구 착수의 전제조건이며, 충족되었다.

---

## 2. 전략 — 2트랙 하이브리드

단일 경로로 가지 않는 이유:

**백업 TSU를 그대로 되돌리면 안 되는 이유** — 백업 89,737건의 메타데이터 충족률:

| 필드 | 채워진 건수 | 비율 |
|---|---|---|
| `title` | 23,714 | 26% |
| `author` | 15,085 | 17% |
| `provenance` | 17,172 | 19% |

즉 사고 전 상태로 되돌려도 **인용 표기의 74~83%가 여전히 비어 있다.** 사고 전 상태는
"정상"이 아니라 "덜 나쁜 상태"였다. 또한 백업에는 동일 서적이 이름만 다르게 중복
등록된 항목(예: `2 Kings, Volume 13`이 두 형태로 12,422 + 10,409건)이 섞여 있다.

**반대로 전량 재처리만 고집하면** 122권(OCR PDF 다수) 재추출·청킹에 수일~수주가 걸려
그동안 시스템이 사용 불가 상태로 남는다.

### 결론: Track A로 가용성을 즉시 회복하고, Track B로 문서 단위 점진 대체

```
        현재 (1,363 TSU / 1권)
              │
    Track A ──┤  백업 복원 + 중복 통합        [수 시간]
              │  → ~75,000 TSU / ~110권, 메타데이터 부분
              │     ※ 검색·설교 생성 즉시 재가동
              │
    Track B ──┤  Calibre 원본 → 최신 파이프라인 재처리  [주 단위]
              │  → 문서 단위로 A를 대체, 메타데이터 100%
              ▼
         정본 코퍼스
```

Track B는 A를 **한 문서씩 교체**한다 — 전체 스왑이 아니므로 언제 중단해도 시스템은
동작 상태를 유지한다.

---

## 3. 실행 계획

### Phase 0 — 동결 및 검증 (착수 전 필수) · 예상 1시간

- [ ] Streamlit 앱 정지 확인 — `background_index_builder`가 5초 주기로 데이터셋을 쓰므로
      복원 중 경쟁이 발생하면 재오염된다. **이 단계 생략 시 전체 계획 무효.**
- [ ] 현재 상태 스냅샷: `output/bench/`, `data/제련완성본/registry/` → `backups/pre_recovery_20260915/`
- [ ] 백업 무결성 검증: `phantom_registry_cleanup_20260907_183948/tsu_dataset.jsonl`
      전 줄 JSON 파싱 + `dataset_sha256` 대조
- [ ] 출처 122건 ↔ 라이브러리 원본 매칭표 확정 (`docs/recovery/source_crosswalk_v1.csv`)
      — 파일명 정규화(NFC) 기준, 중복 후보는 수동 판정
- [ ] 디스크 여유 확인 (최소 20GB)

**게이트:** 매칭표에 미해결 항목이 남아 있으면 Phase 1로 진행하지 않는다.

### Phase 1 — Track A 복원 · 예상 3~5시간

- [ ] `scripts/dedupe_tsu_dataset.py` 기반 중복 통합 규칙 확정
      (동일 서적 이명 등록 → `document_id` 단일화, 청크 수 많은 쪽 채택)
- [ ] 백업 TSU → 중복 통합 → 신규 정본 데이터셋 생성 (**dry-run 먼저**)
- [ ] Registry 재구성: 통합 후 `document_id` 기준, `ingest_status=ACTIVE`,
      `pipeline_state=INDEXED`
- [ ] 색인 전체 재빌드: tantivy 후보 색인 + `bible_index.sqlite3`
- [ ] `tsu_manifest.json` 재작성 (`dataset_sha256`, `registry_sha256`, `build_commit`)
- [ ] 임베딩 캐시 워밍업: `scripts/rebuild_embedding_cache.py`
      — 임베딩은 TSU에 저장되지 않고 `EmbeddingCache`가 지연 충전되므로
        **재임베딩은 복구의 필수 경로가 아니다.** 체감 속도 개선용 사후 작업.

**검증 기준:**
- [ ] TSU ≥ 70,000, 출처 ≥ 100
- [ ] `RetrievalEngine.book_coverage()`가 66권 중 40권 이상에 자료 표시
- [ ] 회귀: `tests/` 전량 PASS
- [ ] 스모크: 설교문 작성에서 로마서·요한복음·히브리서 각 1건 개요 생성 성공

**롤백:** Phase 0 스냅샷 복원 (단일 디렉터리 교체)

### Phase 2 — 재발 방지 고정 · 예상 2시간

- [ ] 회귀 테스트 추가: 출력 폴더가 처리 후보에서 제외되는지 (`_blocked_dirs`)
- [ ] 회귀 테스트 추가: `reconcile_pending()`이 `EXCLUDED` 문서를 재삽입하지 않는지
- [ ] 코퍼스 건전성 가드: TSU 수가 직전 대비 **50% 이상 감소하면 경고 후 중단**
      (스크립트 공통 프리플라이트) — 이번 사고의 조기 탐지 지점
- [ ] Monitor 페이지에 `source_document_count` / `tsu_count` 상시 노출

**이 Phase가 계획의 핵심이다.** 코퍼스를 복원해도 감시 장치가 없으면 같은 일이 반복된다.

### Phase 3 — Track B 정본 재처리 · 예상 주 단위 (점진)

우선순위 순으로 문서 단위 재처리 후 A 레코드를 교체한다.

| 우선순위 | 대상 | 근거 |
|---|---|---|
| P1 | 설교 사용 빈도 높은 주석 (로마서·요한복음·시편·히브리서) | 설교 생성 품질 직결 |
| P2 | 조직신학·교의학 | 교리 필터·ClaimGuard 근거 |
| P3 | 나머지 주석 | |
| P4 | 사전·백과 | Smith 참조 계층과 역할 중복 |

각 문서 처리 절차:
- [ ] Calibre 원본 → `data/RAW` 배치 (**복사, 원본 이동 금지**)
- [ ] 최신 파이프라인 처리 (추출 → 정제 → 청킹 → TSU)
- [ ] 메타데이터 충족 검증 — `title`·`author` **필수**, 미충족 시 승격 보류
- [ ] 프론트매터/판권 페이지가 `quality_score 1.0`으로 통과하지 않는지 확인
      (현행 데이터셋 `chunk_00000`이 출판사 저작권 고지문인 회귀 사례)
- [ ] A 레코드 교체 후 검색 스모크

**제외 대상 명시:** `A Concise Encyclopedia of the United Nations`(4,027 TSU)처럼
신학 코퍼스와 무관한 항목은 재처리하지 않고 A에서도 제거한다.

### Phase 4 — 승격 및 기록

- [ ] ADR 작성: 본 복구의 아키텍처 귀속 + 코퍼스 건전성 가드 정책
- [ ] C1 독립 검토 (CLAUDE.md §C1 Review 시점: "Production 승격 직전")
- [ ] Build Report 작성 → commit → push
- [ ] `docs/STATE.md` 진행률 갱신

---

## 4. 저작권 경계 (계획에 포함해야 하는 제약)

복구 대상 122권은 상용 전자책·스캔 PDF를 포함한다. 본 복구는 **개인 사적 이용 범위의
로컬 시스템 복원**을 전제로 한다. 다음은 본 계획의 범위 밖이며 별도 판단이 필요하다:

- 코퍼스를 포함한 배포·패키징
- 다중 사용자 서비스 제공
- 원문 청크를 그대로 반환하는 외부 API

상업화 경로는 **NAE 트랙(Fuller·Dagg·Hiscox·Smith·신앙고백서 — 전량 퍼블릭 도메인)**
이며, 본 복구와 분리해 유지한다.

---

## 5. 요약 체크포인트

```md
- [ ] Phase 0  동결·검증          (1h)    게이트: 매칭표 완결
- [ ] Phase 1  Track A 복원       (3~5h)  게이트: TSU ≥ 70,000 + 회귀 PASS
- [ ] Phase 2  재발 방지 고정     (2h)    게이트: 건전성 가드 동작 확인
- [ ] Phase 3  Track B 재처리     (주)    점진 — 중단 가능
- [ ] Phase 4  승격·기록          (2h)    게이트: C1 검토
진행률: 0%
```

**가장 중요한 두 가지**
1. Phase 0의 앱 정지 — 생략하면 리컨사일러 경쟁으로 복원이 오염된다(2026-09-07 1차 시도에서 실제 발생).
2. Phase 2의 건전성 가드 — 이번 사고는 "코퍼스가 98% 사라졌는데 아무도 몰랐다"는 점이 본질이다.

---

## 6. 승인 요청 사항

CLAUDE.md §예외 조항에 따라 아래는 실행 전 HQ 승인이 필요하다:

- Production Registry 대량 재구성 (Phase 1)
- Corpus 전체 Migration (Phase 1·3)

승인 시 Phase 0부터 착수한다.
