# C1 Task Order 070 — 코퍼스 트랙 결정 미해결 여부 확인 (사실조사)

- 발주자: CUE
- 일자: 2026-09-22
- 유형: **C1 조사 — 파일·로그 대조 확인 (판단·설계 아님, 순수 사실조사)**
- 근거: `docs/DBMA_SESSION_HANDOFF_20260922.md` §2, `docs/STATE.md` (2026-09-18
  항목, "다음 필요한 HQ 결정" 3개 옵션 — 아래 §1 재인용)

---

## 배경 (이미 확인된 사실 — 재조사 불필요)

`docs/STATE.md`(2026-09-18 항목, 파일 상단)에 이미 아래가 기록돼 있다:

1. 2026-09-07 사고로 코퍼스 89,737건(122출처)→1,363건(1권)으로 축소
2. 2026-09-15 "복구 영구 취소" HQ 결정 — 그런데 **같은 날(2026-09-15
   15:23)** `output/bench/tsu_dataset.jsonl`이 이미 119,595건/67출처
   (Spurgeon MTP 시리즈 전량)로 **미문서화 상태로 교체**돼 있었음(STATE.md
   자신이 "STATE.md 어디에도 기록되지 않은 미문서화 변경"이라고 명시)
3. 2026-09-18 CUE가 이 불일치를 발견해 보고 → HQ가 "1,363건 영구 동결"
   선언만 해지, **Track A(84,766건/125출처 복원)를 새 기준선으로 승인한
   것은 아님**(STATE.md: "이 항목만으로 Track A/B 착수를 승인한 것으로
   간주하지 않는다")
4. 그런데도 2026-09-18 같은 날 Track A 백업 복원이 실행됨(89,836→84,766,
   125출처, 신학무관 6건 제거)
5. STATE.md가 명시한 **"다음 필요한 HQ 결정"**(2026-09-18 시점, 미해결로
   기록):
   - (1) Spurgeon 119,595건/67출처 상태를 새 기준선으로 인정할지
   - (2) Track A/B 중 하나로 별도 복구를 진행할지
   - (3) Fuller/Dagg/Hiscox를 별도 편입(임베딩)할지
6. **지금(2026-09-22) 실측**: `output/bench/tsu_dataset.jsonl` =
   130,401건 / 67출처(전부 archive.org 영문 공개도메인:
   Spurgeon·Maclaren·Whitefield·Broadus·Dargan·Keach·Hovey) — Track A의
   125출처·한글 자료·Fuller/Dagg/Hiscox는 현재 하나도 없음. 즉 옵션 (1)
   방향으로 흘러간 것처럼 보이나, **명시적 HQ 승인 기록을 찾지 못함**.

이 배경 자체를 재검증하라는 요청이 아니다 — 위 6개 사실은 CUE가 이미
`docs/STATE.md`를 직접 읽어 확인했다. **이 Task Order가 요청하는 것은
아래 RQ 두 가지뿐이다.**

---

## 질의 사항

### RQ-1. "다음 필요한 HQ 결정"(§배경 5)이 그 후 어딘가에서 명시적으로
답변됐는가?

확인 방법 — 아래를 **전부** 확인할 것(하나만 보고 결론 내지 말 것):

1. `docs/STATE.md` 전체(1,092행)에서 2026-09-18 이후 날짜
   (`2026-09-19`~`2026-09-22`) 표기 섹션이 있는지 — `grep -n "2026-09-1[9]\|2026-09-2[0-2]" docs/STATE.md`로 확인.
2. `git log --all --oneline` 전체(모든 브랜치)에서 커밋 메시지에
   "기준선"·"baseline"·"Track A"·"Track B"·"84,766"·"119,595"·"67종"·
   "67개 출처" 등이 언급된 2026-09-18 이후 커밋이 있는지.
3. `docs/` 아래 2026-09-18 이후 날짜가 파일명·본문에 있는 문서 중
   코퍼스 기준선을 언급하는 것이 있는지(`docs/DBMA_RELEASE_GAP_CLOSURE_PIPELINE_v1.md`,
   `docs/DBMA_S2_4_CORPUS_EXPANSION_REPORT_001.md` 등 이미 아는 문서
   포함 — 이 문서들이 "4→67종 확장"을 다룰 뿐 84,766/125종 Track A와의
   관계를 언급하는지 다시 읽어 확인).
4. `NAE/corpus/`(2.6GB, `docs/DBMA_SESSION_HANDOFF_20260915.md`가 "보존
   자산, 다른 세션이 작업 중"이라고 적은 디렉터리)에 README나 상태 문서가
   있는지, Track A 콘텐츠(Fuller/Dagg/Hiscox)가 지금도 거기 보존돼
   있는지(`ls NAE/corpus/`, 하위 구조 확인 — 내용을 판단하거나 옮기지
   말고 존재 여부·최종 수정일만 확인).

**답변 형식**: "명시적 답변을 찾았다"면 그 문서·커밋·날짜를 정확히
인용. "찾지 못했다"면 어디까지 확인했는지(위 1~4 각각의 결과)와 함께
"확인 불가"로 명시. 추정하지 말 것.

### RQ-2. `output/bench/tsu_dataset.jsonl`이 84,766건(125출처, Track A)에서
지금의 130,401건(67출처)으로 바뀐 시점과 원인을 시간순으로 재구성할 수
있는가?

확인 방법:

1. `backups/` 아래 타임스탬프 있는 폴더 중 코퍼스 크기를 알 수 있는 것
   전부 나열하고 건수순으로 정렬 — 특히
   `backups/pre_nontheo_removal_20260918/tsu_dataset.jsonl.89836`,
   `backups/pre_recovery_20260918/tsu_dataset.jsonl.spurgeon_119595`
   두 파일의 정확한 생성 시각(`stat -f "%Sm" <path>` 또는
   `ls -la --time-style=full-iso`)을 확인 — "spurgeon_119595" 백업이
   84,766건 상태보다 시간상 **이전인지 이후인지**가 핵심.
2. `docs/DBMA_S2_4_CORPUS_EXPANSION_REPORT_001.md`(S2-3/S2-4, "4→67종
   확장" 작업 보고서)를 다시 읽고, 이 작업이 **어떤 상태에서 시작했다고
   적혀 있는지**(4개 출처라고 적혀 있다면, 그 "4개"가 84,766건/125출처
   상태의 일부였는지 아니면 완전히 별도의 출발점이었는지) 확인.
3. `scripts/baseline_corpus_manifest.json`의 git 커밋 이력
   (`git log --all --follow -- scripts/baseline_corpus_manifest.json`)에서
   이 파일이 처음 생긴 시점과, 그 시점에 `output/bench/tsu_dataset.jsonl`
   실측 건수가 얼마였는지(가능하면 근접한 날짜의 backups/ 폴더와 대조).
4. `scripts/reset_for_beta.py`(특히 `reseed_baseline()`, PR #45)가 실행된
   기록이 있는지 — 실행 로그·커밋 메시지·STATE.md 어디든.

**답변 형식**: 확보한 사실만으로 시간순 표를 만들 것(날짜/시각 | 건수 |
출처수 | 근거 파일). 빈 구간(증거 없음)은 "증거 없음"으로 명시 — 추측으로
메우지 말 것.

---

## 금지 사항

- **판단·권고 금지**: "어느 트랙을 기준선으로 삼아야 하는가"는 이
  Task Order의 범위가 아니다(HQ 결정 사항). RQ-1/RQ-2의 사실관계만
  보고한다.
- 코드·데이터·registry·백업 파일 수정 금지(읽기 전용 조사).
- `git checkout` 금지, `NAE/corpus/` 내용물 이동·삭제 금지.
- 범위 확장 금지(book_coverage 미달 원인 등 STATE.md의 다른 미해결
  항목은 이번 범위 아님).

## 출력 형식

`docs/DBMA_CORPUS_TRACK_TIMELINE_C1_REPORT_001.md`로 작성, RQ-1/RQ-2
각각 별도 절. 사용자가 CUE에게 붙여넣으면 CUE가 대조검증 후 HQ 결정
요청으로 이어간다.

```
STATUS:      C1 코퍼스 트랙 타임라인 조사 요청
Changed:     이 문서 1건만
Next:        C1 보고서 작성 → CUE 대조검증 → HQ에 §배경-5의 3개 옵션
             중 선택 요청(§2 문서, DBMA_SESSION_HANDOFF_20260922.md 참고)
```
