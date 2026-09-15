# CUE 독립 검증 — F1 산출물 + C1 Review 결과

- 검증자: CUE / 2026-09-08
- 대상: `NAE_FULLER_CANONICAL_VERIFICATION_001.md` (F1), `NAE_FULLER_TSU_PIPELINE_C1_REVIEW_RESULT_001.md` (P-4)
- 재실측: `/Users/David/DBMA` @ `dev/dbma-engine` `e38a810`, venv `~/envs/dbma311`

---

## 종합 판정

| 문서 | 판정 |
|---|---|
| **F1 canonical 검증** | 🟢 GREEN — 전 항목 CUE 재실측 일치. **T3 결함이 심각**(범위: 전 8권) |
| **C1 Review (P-4)** | 🟡 CONDITIONAL — Q2/Q4/Q6 GREEN 동의, Q3 YELLOW 동의, **Q5는 CUE가 YELLOW로 하향** |

**F3(David 검수)는 착수 가능. F4/F5는 HQ 결정 2건 필요** (§4).

---

## 1. F1 검증 — 🟢 GREEN

| 항목 | CUE 재실측 | 일치 |
|---|---|---|
| repo | HEAD `e38a810`, `git status` = 신규 리포트 2개만 | ✅ |
| T1 canonical 8/8 | 8권 canonical.json 파싱 OK, status=ok, paragraph_count 일치 | ✅ |
| T2 집계표 | 8권 normalize_report 전 필드 CUE 직접 재읽기 — **완전 일치** (page_count=1 전권, footnotes=0 전권, scripture Vol01=2/02=3/03=0/04=3/05=1/06=1/07=0/08=1, heading 137/144/184/395/284/359/77/163) | ✅ |
| T3 원인 규명 | **CONFIRMED** — 아래 §1.1 | ✅ |
| T4 locator | `work_id + heading_path + paragraph_index` — page_count=1 조건에서 타당. heading 품질 편차(Vol04=395)는 C1도 명시 | ✅ |
| T5 disclosure | admission rationale와 정합, 새 주장 없음 | ✅ |
| Mutation | 0 | ✅ |

### 1.1 T3 — scripture 추출기 결함 CUE 재확인 (심각도 상향)

C1 주장을 CUE가 코드·데이터로 재확인:

- `NAE/pipeline/canonical/annotate.py`:
  - `_ROMAN_MAP` = **"xxviii"(28)에서 잘림** — `Ps. xl`(40), `Ps. cxviii`(118),
    `Rom. xix` 등은 regex는 매칭되나 `.get()` → None → **폐기**. (직접 확인)
  - `_LEGACY_REF`/`_ARABIC_REF` book = `[A-Z][a-z]+` → **한글 성서명·전대문자 미지원**. (직접 확인)
- `canonical/Fuller_Complete_Works_Vol01/canonical.json`: 2,250 문단 중
  `scripture_refs` 보유 = **0**. 결함이 canonical 구조까지 전파됨.
- CUE grep(`[A-Z][a-z]{1,4}\. [ivxlcdm]+\. [0-9]+`): Vol01=269 / Vol03=88 /
  Vol07=47 매칭 — regex 차이로 C1 수치와 다르나 **결론 동일**: 리포트값
  (2/0/0)은 실제와 자릿수가 다름.

**CUE 평가**: 이것은 "Vol.03/07이 0" 수준의 국소 문제가 아니라 **전 8권에
걸친 체계적 추출 실패**다. C1 F1 판정("추출기 누락")은 정확하나, **심각도가
provenance 각주 한 줄로 덮을 수준이 아니다.** → §2 Q5, §4.

---

## 2. C1 Review 검증

### 동의
- **Q2 ADR 정합 GREEN** — TSU Track 순서·§11.4 3,319 무접촉·ADR-013/024/029 격리 논거 타당. 단 Qdrant `work_id` 격리는 **F5 미구현** — "설계 타당, 구현 미검증"으로 이해.
- **Q4 baseline 보호 GREEN** — 구조적 격리 논거 타당. C1 스스로 "F5 구현 시 코드 리뷰" 단서. 동의.
- **Q6 ADR-029 충돌 GREEN** — Fuller(TSU Track) ↔ Korean Terminology(별도 layer) 격리. 동의.
- **Q3 검수 방식 YELLOW** — 동의. 단 **사실 오류 1건**: "배치 파일은 디렉터리가 다르지만"은 틀림 — `fuller_v01_batch_*`와 `batch_00*`는 **같은 디렉터리** `NAE/review/human/requests/`, 접두어로만 구분(C1 Phase 2에서 이미 확인한 사실). YELLOW 결론 자체는 유지.

### CUE 이견 — Q5 provenance: GREEN → **YELLOW**

C1 Q5는 scripture 결함을 "`historical_witness`는 scholarly citation이 아니므로
허용, disclosure로 고지"로 처리. **F1 T3와 상충**:
- F1이 방금 밝힌 것은 **전 8권 체계적 추출 실패**(§1.1). "일부 누락"이 아니다.
- 이 상태로 F5 색인하면 Fuller에 대한 **성구 기반 retrieval/교차참조가 조용히
  미작동**. disclosure 문구 "일부 성구 참조 누락"은 실상(대부분 누락)을 축소.
- claim 본문 retrieval에는 영향이 제한적이나, scripture 메타데이터는 신뢰 불가.

→ **Q5 = YELLOW**: claim 텍스트 노출은 수용 가능하나, scripture 메타데이터
결함은 F0 re-normalize 결정 전 또는 명시적 HQ 수용 없이는 F5로 넘기지 않는다.

### 독립성 한계 (참고)
C1은 Phase 2 배치를 **직접 생성한 실행자**이면서 이번 파이프라인 진입을
검토했다. 완전한 독립 감사가 아니다. Q1(거버넌스 권한)에서 C1이 근거로 든
`RESUMPTION_PLAN §9.3`은 CUE가 쓰고 HQ가 승인한 문서 — 순환 인용에 가깝다.

---

## 3. 게이트 현황

| Phase | 상태 |
|---|---|
| F1 | 🟢 완료 (T3 결함 기록됨) |
| C1 Review (P-4) | 🟡 GREEN(조건부) — Q5 CUE 하향, Q3 YELLOW |
| F3 David 검수 | **착수 가능** (검수는 claim 품질 판정 — scripture 메타데이터 결함과 무관) |
| F4 임베딩 / F5 색인 | **보류** — §4 HQ 결정 필요 |

---

## 4. HQ 결정 요청 (F4/F5 착수 전)

1. **ADR-030 Amendment (P-2)** — C1 Review는 "Vol.01 한정 F3–F5는 결정 B로
   충분, Amendment는 Vol.02–08 확장에만 필요"로 판단. **F5는 production
   `nae_tsu_v1` 색인**이므로 CUE는 HQ의 명시적 확인을 권고: 결정 B로 F5까지
   진행 승인인가, 아니면 최소한 citation disclosure·provenance 한계를 고정하는
   처리 지시서/Amendment 선행인가?
2. **scripture 추출기 / re-normalize** — F1 T3: 전 8권 체계적 결함. 택1:
   - (a) `annotate.py` 수정(로마자 맵 확장 + 한글 성서명 + OCR 노이즈 내성)
     → Vol.01 canonical re-normalize → 그 위에서 F3–F5. **정확하나 지연.**
   - (b) 현 canonical 그대로 F3–F5 진행, scripture 메타데이터가 불완전함을
     disclosure에 **강한 표현으로** 명시("대부분의 성구 참조가 자동 추출에서
     누락됨"), 추출기 수정은 별도 트랙. **빠르나 품질 부채.**
   - CUE 권고: Vol.01 파일럿은 (b)로 진행하되 (a)를 F0 백로그로 명시 등록,
     Vol.02–08 확장 전 (a) 완료를 조건화.

---

## 5. 산출물 상태

- `NAE_FULLER_CANONICAL_VERIFICATION_001.md` — 검증 GREEN, 커밋 대상
- `NAE_FULLER_TSU_PIPELINE_C1_REVIEW_RESULT_001.md` — 검증 CONDITIONAL, 커밋 대상 (본 문서가 Q5 하향·독립성 한계 첨부)
- 본 문서 — 커밋 대상

---

## 6. HQ 결정 (2026-09-08)

- **§4-2 = 옵션 (b)**: Vol.01 파일럿은 현 canonical 그대로 F3–F5 진행.
  scripture 메타데이터 불완전을 **강한 disclosure**로 명시(문구: RESUMPTION_PLAN §10).
- **추출기 수정 = F0 백로그 B-1** 등록 (`NAE_FULLER_PROCESSING_RESUMPTION_PLAN_v1.md` §10).
  Vol.02–08 확장(F2) 착수 전 완료 필수. B-2(re-normalize)는 B-1 BLOCKED.
- **§4-1 (ADR-030 Amendment P-2)**: HQ "(b)로 진행" 을 Vol.01 파일럿 F3–F5
  진행 승인으로 간주(C1 Review Q1 GREEN 근거). P-2 Amendment 정식 문서는
  **Vol.02–08 확장 전** 작성 — 그때까지 formally OPEN.

### 게이트 갱신

| Phase | 상태 |
|---|---|
| F1 | 🟢 완료 (B-1 백로그 등록) |
| C1 Review P-4 | 🟢 조건부 GREEN (Q3/Q5 YELLOW, 향후 해소) |
| F3 David 검수 | **착수 가능** (일정 = HQ 신호) |
| F4 임베딩 / F5 색인 | Vol.01 한정 진행 승인 (F3 완료 후) — strong disclosure 조건 |
| F2 Vol.02–08 | B-1 완료 + P-2 Amendment 전까지 BLOCKED |
