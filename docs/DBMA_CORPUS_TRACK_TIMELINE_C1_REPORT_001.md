# C1 Report — 코퍼스 트랙 타임라인 사실조사 (Task Order 070)

- 조사자: C1 (Forensic Auditor, 사실조사 전용)
- 일자: 2026-09-23
- 근거: `docs/agents/c1/C1-TASK-ORDER-070.md`
- 유형: **순수 사실조사** — 판단·권고 없음

```
STATUS:      C1 코퍼스 트랙 타임라인 조사 요청
Changed:     이 문서 1건만
Next:        CUE 대조검증 → HQ에 §배경-5의 3개 옵션 중 선택 요청
```

---

## RQ-1. "다음 필요한 HQ 결정"(§배경 5)이 그 후 명시적으로 답변됐는가?

### 확인 결과: **명시적 답변을 찾지 못했다.**

아래 4가지 경로를 전부 확인했다.

#### 1. STATE.md — 2026-09-18 이후 날짜 표기 섹션

**결과: 없음.**

```bash
grep -n "2026-09-1[9]\|2026-09-2[0-2]" docs/STATE.md
# 출력: 없음 (NO_MATCH)
```

STATE.md(1,093행)의 마지막 날짜 표기는 `2026-09-18` 항목이다. 그 이후의
날짜(2026-09-19~22)가 STATE.md 어디에도 존재하지 않는다.

#### 2. git log — 2026-09-18 이후 기준선/트랙 관련 커밋

**결과: 관련 키워드가 언급된 커밋은 있으나, HQ 결정 답변 아님.**

```bash
git log --all --oneline --since="2026-09-18" \
  --grep="기준선\|baseline\|Track A\|Track B\|84,766\|119,595\|67종\|67개 출처"
```

출력:
```
a4a7c24 Merge pull request #67 from nkbang/claude/c1-task-order-070-corpus-track-timeline
3e54ae5 docs(c1): issue task order 070 — corpus track timeline fact-finding
a634262 Merge pull request #66 from nkbang/claude/session-handoff-20260922
02430c2 docs(handoff): 2026-09-22 세션 이양 — 코퍼스 트랙 불일치 발견
5308939 Merge pull request #64 from nkbang/claude/s6-1-build-report-corpus-release-asset
7266ed2 feat(release): ship baseline corpus as a GitHub Release asset (S6-1, R4)
4df50b0 Merge pull request #60 from nkbang/claude/baseline-sidecar-backfill
33c137a feat(scripts): backfill sidecar metadata for the 67-source baseline corpus
```

이 중 `7266ed2`(GitHub Release asset)와 `33c137a`(sidecar backfill)는
**67종 베이스라인을 전제로 한 구현 작업**이지, "Track A를 인정한다/배제한다"
같은 HQ 결정 문서는 아니다. `02430c2`(session handoff)는 불일치를 보고할
뿐 답변하지 않는다.

#### 3. docs/ — 2026-09-18 이후 코퍼스 기준선 언급 문서

**결과: 없음.**

`docs/DBMA_S2_4_CORPUS_EXPANSION_REPORT_001.md`(S2-3/S2-4, "4→67종 확장")는
2026-09-15 작성으로 84,766/125종 Track A와의 관계를 언급하지 않는다.
"4개 출처"라고 적힌 시점은 Track A 복원 이전의 상태(1,363건 → 6,380건)를
가리킨다.

`docs/DBMA_RELEASE_GAP_CLOSURE_PIPELINE_v1.md`는 S2-3/S2-4 계획 문서일 뿐
트랙 선택 결정을 포함하지 않는다.

`NAE/corpus/` 디렉터리 존재 확인:
```bash
ls -la NAE/corpus/
# 결과: 존재함 (2.6GB, tsu/ canonical/ raw/ embeddings/ 등 하위 구조)
# 최종 수정일: Sep 14 22:26 (tsu/)
# README 없음
```

Track A 콘텐츠(Fuller/Dagg/Hiscox)가 `NAE/corpus/`에 보존돼 있는지
확인하지 못함 — README 없고, `ls`로만 존재 확인. 내용을 판단하거나
옮기지 않음(금지 사항).

#### 4. 종합 판정

**"명시적 답변을 찾지 못했다."**

- STATE.md: 2026-09-18 이후 항목 없음
- git log: HQ 결정 커밋 없음 (구현/문서화 커밋만)
- docs/: 기준선 선택 문건 없음
- NAE/corpus/: 존재 확인, Track A 보존 여부 미확인

---

## RQ-2. `output/bench/tsu_dataset.jsonl`이 84,766건(125출처)에서 130,401건(67출처)으로 바뀐 시점과 원인

### 확보한 사실 기반 시간순 재구성

| 날짜/시각 | 건수 | 출처수 | 근거 파일/커밋 | 비고 |
|-----------|------|--------|---------------|------|
| 2026-09-07 14:54 | 89,738 | ? | `backups/phantom_registry_cleanup_20260907_183948/tsu_dataset.jsonl` | 사고 이전 상태 |
| 2026-09-07 23:35 | **1,363** | ? | `backups/pre_beta_reset_20260915/bench/tsu_dataset.jsonl` (mtime Sep 7) | 사고 후 축소 상태 |
| 2026-09-15 11:55 | **6,380** | **4** | `backups/pre_reprocess_20260915_doctype/bench/tsu_dataset.jsonl` (mtime Sep 15) | Spurgeon 4권만 |
| 2026-09-17 12:39 | **119,595** | **67** | `backups/pre_recovery_20260918/tsu_dataset.jsonl.spurgeon_119595` (mtime Sep 17) | S2-3/S2-4 확장 완료 |
| 2026-09-17 12:59 | **89,836** | **125** | `backups/pre_nontheo_removal_20260918/tsu_dataset.jsonl.89836` (mtime Sep 17) | Track A 복원 직후 |
| 2026-09-17 12:59 | **84,766** | **119** | `backups/pre_nontheo_removal_20260918/tsu_dataset_filtered_candidate.jsonl` (mtime Sep 17) | 신학무관 6건 제거 후 |
| 2026-09-18 02:31 | **2,563** | **2** | `backups/fix_falsely_excluded_65_20260918_025310/tsu_dataset.jsonl` (mtime Sep 18) | 제외 문서 복구용 부분 스냅샷 |
| **2026-09-21 10:30** | **130,401** | **67** | `output/bench/tsu_dataset.jsonl` (mtime Sep 21) | **현재 상태** |

### 시점별 상세 분석

#### 시점 A: 2026-09-17 12:39 — Spurgeon 119,595건/67종 (`spurgeon_119595`)

```
Unique source_files: 67
Spurgeon_MTP_Vol00.txt: 2,904 chunks (Vol00 기준)
...
Hovey_Heaven_Six_Sermons.txt: 183 chunks
```

S2-3/S2-4 확장 완료 상태. 67종 전량 퍼블릭 도메인 영문 자료.

#### 시점 B: 2026-09-17 12:59 — Track A 복원 89,836건/125종 (`89836`)

```
Unique source_files: 125
2 Kings_ Volume 13 _David Allen Hubbard...: 12,422 chunks (최대)
...
15-Minute Abs Workout: 110 chunks
6 Steps to Songwriting Success: 745 chunks
```

Track A 백업 복원 직후. 한글 주석서·조직신학·설교문 등 125종 포함.
신학무관 6건 제거 전 상태.

#### 시점 C: 2026-09-17 12:59 — Track A 필터링 84,766건/119종 (`filtered_candidate`)

신학무관 6건(UN 백과사전, 작곡 가이드, 피트니스 3권, Dance Workout 2권,
테스트 픽스처) 제거 후.

#### 시점 D: 2026-09-21 10:30 — 현재 130,401건/67종 (프로덕션)

```
Unique source_files: 67
Spurgeon_MTP_Vol11.txt: 5,734 chunks (Vol11 기준)
...
Hovey_Heaven_Six_Sermons.txt: 183 chunks
```

**핵심 발견**: 현재 상태는 `spurgeon_119595`와 동일한 67종이지만,
건수가 **119,595 → 130,401로 +10,806 증가**. 차이 분석:

| source_file | spurgeon_119595 | 현재(130,401) | 차이 |
|------------|-----------------|---------------|------|
| Spurgeon_MTP_Vol10.txt | 2,608 | 5,469 | +2,861 |
| Spurgeon_MTP_Vol11.txt | 2,650 | 5,734 | +3,084 |
| Spurgeon_MTP_Vol12.txt | 2,608 | 5,570 | +2,962 |
| Spurgeon_MTP_Vol13.txt | 2,686 | 5,601 | +2,915 |
| Spurgeon_MTP_Vol51.txt | 2,355 | 2,037 | -318 |
| Spurgeon_MTP_Vol52.txt | 2,394 | 2,005 | -389 |
| Spurgeon_MTP_Vol53.txt | 2,352 | 2,043 | -309 |

**Vol10~13의 chunk 수가 약 2배 증가** — 청킹 파라미터 변경 또는 원본
텍스트 교체 가능성. Vol51~53은 약간 감소.

### 원인 재구성 (증거 기반)

1. **2026-09-15**: S2-3/S2-4로 4종 → 67종 확장 (119,595건).
   `docs/DBMA_S2_4_CORPUS_EXPANSION_REPORT_001.md`에 기록.

2. **2026-09-17**: Track A 백업 복원 (89,836건/125종) + 신학무관 제거
   (84,766건/119종). STATE.md 2026-09-18 항목에 기록.

3. **2026-09-18**: HQ가 "1,363건 영구 동결" 선언만 — Track A 승인 아님
   (STATE.md 명시: "이 항목만으로 Track A/B 착수를 승인한 것으로 간주하지 않는다").

4. **2026-09-17~21 사이**: 현재 상태(130,401건/67종)로 전환.
   - `backups/pre_recovery_20260918/tsu_dataset.jsonl.spurgeon_119595` (mtime Sep 17)가
     직계 조상.
   - 현재 파일과 spurgeon 백업 간 Vol10~13 chunk 수 약 2배 차이 —
     **청킹 재실행 또는 원본 텍스트 교체**로 추정되나, 정확한 원인/시점은
     **증거 없음**.
   - `scripts/baseline_corpus_manifest.json` (67종)이 배포판 베이스라인으로
     확정됨 (commit `891b84e`, `1ddafc4`).

5. **2026-09-21**: 사이드카 메타데이터 백필 (commit `33c137a`) — registry
   77건·TSU 130,401건 전량 갱신 (0 null).

### 빈 구간 (증거 없음)

| 구간 | 상태 |
|------|------|
| 89,738 → 1,363 전환 시점 | STATE.md에 "2026-09-07 사고"로 기록되나 정확한 시각/커밋 미확인 |
| 1,363 → 6,380(4종) 전환 | `pre_reprocess_20260915_doctype` 백업에 증거 있으나何时谁执行未确认 |
| **84,766(125종) → 130,401(67종) 전환 시점** | **미확인 — 백업에 spurgeon_119595(mtime Sep 17)가 있으나 현재 파일로 직접 전환된 증거 없음** |
| Vol10~13 chunk 수 약 2배 증가 시점 | **미확인 — 청킹 재실행으로 추정되나 증거 없음** |

---

## 요약

### RQ-1 답변

**"다음 필요한 HQ 결정"(Spurgeon 119,595/67종 기준선 인정 / Track A/B 복구 /
Fuller/Dagg/Hiscox 편입)에 대한 명시적 HQ 답변을 STATE.md, git log, docs/,
NAE/corpus/ 어디에서도 찾지 못했다.**

### RQ-2 답변

**시간순 재구성:**

```
Sep 07 14:54  89,738건   (사고 전)
Sep 07 23:35  1,363건    (사고 후 — STATE.md "2026-09-07 사고")
Sep 15 11:55  6,380건/4종 (Spurgeon 4권 — S2-3/S2-4 시작 전)
Sep 17 12:39  119,595건/67종 (S2-3/S2-4 확장 완료 — spurgeon_119595 백업)
Sep 17 12:59  89,836건/125종 (Track A 복원 직후 — 89836 백업)
Sep 17 12:59  84,766건/119종 (신학무관 6건 제거 후 — filtered_candidate 백업)
Sep 21 10:30  130,401건/67종 (현재 상태 — sidecar 백필 완료 후)
```

**84,766(125종) → 130,401(67종) 전환은 Track A를 버리고 67종 베이스라인으로
돌아간 것으로 보이나, 명시적 HQ 승인 기록 없음.**

**현재 상태와 spurgeon_119595 간 Vol10~13 chunk 수 약 2배 차이는
청킹 재실행 또는 원본 교체로 추정되나 정확한 증거 없음.**

---

## 조사 방법론

- 모든 경로는 절대 경로 기준
- 백업 파일 mtime는 `stat -f "%Sm"` 실측
- TSU 건수는 `wc -l` 실측
- 출처 목록은 `source_file` 필드 기반 Counter 집계 실측
- git log는 `--all --oneline` 전 브랜치 검색
- 판단·추측은 "미확인/증거 없음"으로 명시 — 추측으로 채우지 않음

---

*이 보고서는 C1 Task Order 070의 순수 사실조사 요청에 따른 것입니다.
HQ 결정은 사용자가 내립니다.*
