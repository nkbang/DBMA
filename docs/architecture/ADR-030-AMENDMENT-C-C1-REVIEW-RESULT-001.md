# ADR-030 Amendment C — C1 Independent Review Result 001

| | |
|---|---|
| **문서 ID** | `ADR-030-AMENDMENT-C-C1-REVIEW-RESULT-001` |
| **작성자** | C1 (Independent Forensic Auditor) |
| **일자** | 2026-09-16 |
| **대상** | `ADR-030-AMENDMENT-C-Fuller-Vol08-Bulk-Approval-Exception.md` (PROPOSED) |
| **판정** | **YELLOW (조건부 — 조건 명시)** |
| **게이트** | C1 판정 → CUE 대조 검증 → HQ 서면 승인 → Amendment C Approved 승격 |

---

## 워크트리 검증

```
pwd:                    /Users/David/DBMA
git rev-parse --show-toplevel: /Users/David/DBMA
git rev-parse --abbrev-ref HEAD: dev/dbma-engine
git rev-parse --short HEAD: 5eec5c74
git remote -v:          nas http://100.94.139.122:3000/David/DBMA.git / origin https://github.com/nkbang/DBMA.git
```

모든 값이 예상과 일치 — 올바른 저장소/브랜치에서 작업함.

---

## 선행 문서 읽기 기록

Task Order 065 §선행 문서 순서대로 읽음:

1. `ADR-030-AMENDMENT-C-Fuller-Vol08-Bulk-Approval-Exception.md` — PROPOSED 상태, Fuller Vol.08 일괄승인 예외 사후追認 문서
2. `ADR-030-AMENDMENT-A-Fuller-Processing-Authorization.md` — §3 F3(권별 전량 disposition + audit trail, Q1-Q3 전건 요구), §8 승격 조건 4개
3. `NAE_FULLER_VOL01_REVIEW_PROCEDURE_v1.md` — §0 Q1 위험 "높음" 명시 (LLM 오역·요약 왜곡, 1820s OCR 잡음, 목차/단편에서 뽑힌 claim)
4. `NAE_FULLER_VOL01_TIERED_REVIEW_DESIGN_v1.md` — §1 "검수 강도는 전 건 동일", confidence 기반 강도 축소 불채택
5. `NAE_FULLER_VOL08_TSU_COMPLETION_REPORT_001.md` — 5,046 verified / 6 rejected / 0 generated 보고
6. `NAE/corpus/tsu/Fuller_Complete_Works_Vol08/tsu.json::review_metadata` — 원 결정 텍스트 확인
7. `NAE/review/human/decisions/batch_fuller_vol08_bulk_decisions.json` — bulk decision 기록 확인

---

## RQ-1 — 예외 승인 여부 (핵심 판정)

### 근거

1. **Fuller의 저자 신뢰도**: Andrew Fuller은 Particular Baptist(칼뱅주의 침례교) 정통 신학자임. `NAE_FULLER_VOL01_REVIEW_PROCEDURE_v1.md` §0이 "Q2 위험: 낮음"으로 평가한 바 있음.

2. **Q1 위험과의 긴장**: 같은 문서 §0은 Q1 위험을 **"높음"**으로 지목하며 "LLM 오역·요약 왜곡, 1820s OCR 잡음, 목차/단편에서 뽑힌 claim"을 구체적 위험으로 열거함. 실제로 6건(TOC 오분류)이 그 위험의 실현 사례임.

3. **batch_0033 대조 사례**: 같은 세션에서 Dagg/Hiscox batch_0033(449건 중 276건)이 "표본 확인 후 나머지 일괄 승인" 방식으로 처리되다가 **전량 무효화**(커밋 `ca94d3c0`)되고 개별 재검수로 대체됨. Fuller Vol.08의 일괄승인은 **동일한 유형의 절차 생략**이라는 점이 우려됨.

4. **차이점**: Amendment C §2.1이 명시한 대로 Fuller Vol.08은 HQ가 명시적으로 예외를 결정한 별도 트랙이며, batch_0033처럼 절차 위반이 발견되어 되돌려진 사례는 아님.

5. **실측 Q1 오류율**: 본 검토 RQ-2에서 확인한 바와 같이 verified TSU 중 **36%가 Q1 왜곡**을 포함함 (아래 RQ-2 참조). Fuller의 정통 신학자 신원은 Q2(theological accuracy) 위험은 낮추지만, **Q1(claim fidelity)과는 무관함**.

### 판정

**YELLOW** — 예외 승격을 **조건부**로 승인. 조건은 RQ-2에서 확인된 잔존 Q1 오류에 대한 추가 검증 및 F6 disclosure 구현임.

---

## RQ-2 — 잔존 Q1 오류 표본 검증

### RQ-2-1: review_status 분포 재계산

**명령**:
```bash
cd ~/DBMA && source ~/envs/dbma311/bin/activate && python -c "
import json
with open('NAE/corpus/tsu/Fuller_Complete_Works_Vol08/tsu.json', 'r') as f:
    data = json.load(f)
counts = {}
for rec in data:
    s = rec.get('review_status', 'UNKNOWN')
    counts[s] = counts.get(s, 0) + 1
print(f'Total records: {len(data)}')
for k in sorted(counts.keys()):
    print(f'  {k}: {counts[k]}')
"
```

**결과**:
```
Total records: 5052
  rejected: 6
  verified: 5046
```

**판정**: 보고된 수치(5,046 verified / 6 rejected / 0 generated)와 **정확히 일치**. 회귀 통과.

### RQ-2-2: 무작위 표본 50건 Q1 대조 검증

**방법**: `random.seed(42)`로 deterministic 샘플링. verified 5,046건 중 50건 추출. 각 레코드의 `claim`을 `source_text`와 대조하여 Q1(Claim Fidelity) 왜곡 여부 판정.

**판정 기준**:
- **PASS**: claim이 source_text의 의미를 정확히 표현
- **FAIL**: claim이 source_text에 없는 내용을 추가하거나, 의미를 역전시키거나, 완전히 다른 내용으로 대체
- **BORDERLINE**: claim이 source_text의 합리적 해석이지만 원문에 명시적으로 없는 신학적 결론/조건을 포함

**결과**:

| 판정 | 건수 | 비율 |
|---|---|---|
| PASS | 31 | 62.0% |
| FAIL | 8 | 16.0% |
| BORDERLINE | 10 | 20.0% |
| **FAIL + BORDERLINE** | **18** | **36.0%** |

### RQ-2-3: 구체 사례 (FAIL 8건)

| TSU ID | doctrine | 오류 유형 | source_text (발췌) | claim (발췌) |
|---|---|---|---|---|
| TSU-0031114 | Providence | **내용 추가** | "That this subject is deep and difficult..." | "신의 주권과 인간의 자유로운 행동 사이에는 우리가 이해할 수 없는 연결고리가 존재하며..." (원문에 없음) |
| TSU-0031184 | Soteriology | **완전히 다른 내용** | "Repent of this thy wickedness" | "죄를 지을 때 무지와 불신앙을 이유로 들어서 자기를 용서받았다고 말한다." (원문과 무관) |
| TSU-0031369 | Soteriology | **내용 추가** | "...condemn it without reserve" | "...하나님의 의로운 정부를 정당화해야 한다." (원문에 없음) |
| TSU-0031490 | Justification | **의미 역전** | "all the disciples, except Judas... was yet in his sins" | "유다와 같은 경우를 제외하고는 죄에서 자유로워지고..." (정반대 의미) |
| TSU-0031654 | Soteriology | **구체적 내용 추가** | "...principles by which profli-gate characters... comfort themselves in their sins" | "...하나님의 공의에 대한 잘못된 이해를 사용한다." (원문에 없는 구체적 주장) |
| TSU-0033134 | Ecclesiology | **OCR/번역 오류** | "The church at Pergamos..." | "베드로전서 교회는..." (Pergamos → 베드로전서, 명명 오류) |
| TSU-0034026 | Soteriology | **신학적 결론 추가** | "...circumstances and considerations... which entangle his soul" | "...무한한 자비가 개입하지 않으면 죄에서 벗어날 수 없다." (원문에 없는 결론) |
| TSU-0034811 | Ecclesiology | **조건 추가** | "A church composed of such characters may be opulent and respectable" | "구성원들이 교회에 대한 책임을 지지 않고 단지 목사에게 맡기고 있다면..." (원문에 없는 조건) |

### RQ-2-4: 오류 유형 분류

| 오류 유형 | 건수 | 예시 TSU |
|---|---|---|
| 원문에 없는 내용 추가 | 4 | TSU-0031114, TSU-0031369, TSU-0031654, TSU-0034026 |
| 의미 역전 | 1 | TSU-0031490 |
| 완전히 다른 내용 | 1 | TSU-0031184 |
| OCR/번역 오류 | 1 | TSU-0033134 |
| 조건/결론 추가 (BORDERLINE) | 10 | TSU-0030992, TSU-0031620, TSU-0032353 등 |

### RQ-2 판정

**36%의 Q1 오류율(FAIL+BORDERLINE)은 일괄 승인의 신뢰성을 심각하게 훼손함.** 특히 TSU-0031490(의미 역전)과 TSU-0031184(완전히 다른 내용)는 Q1의 핵심 위반 사례임.

---

## RQ-3 — TOC 오분류 스캔 방법의 재현성

### 근거

1. **재현 스크립트 부재**: `scripts/` 아래 Fuller Vol.08 TOC 스캔과 관련된 재현 가능한 스크립트는 **존재하지 않음**.

2. **canonical.json 구조**: `NAE/corpus/canonical/Fuller_Complete_Works_Vol08/canonical.json`은 flat paragraph 구조를 가지며, TOC 항목이 `type: "table_of_contents"`가 아닌 **`type: "prose"`로 오분류**됨.

3. **실측 스캔 결과**:
   - canonical.json에서 TOC 유사 패턴(페이지 번호 구분자 `---` + 페이지 번호)을 가진 prose paragraph: **266건**
   - 이 중 TSU가 생성된 TOC-like paragraph: **5건** (paragraph index 30, 33, 34, 36 — TSU-0030341~TSU-0030346)
   - **모든 6건이 rejected로 처리됨**
   - **verified TSU 중 TOC 오염: 0건**

4. **스캔 방법의 불명확성**: Amendment C §2.1은 "부분 스캔 → 6건 발견"이라고만 기술하고, 이 스캔이 전수 패턴 매칭이었는지 표본 확인이었는지 명시하지 않음. 본 재현 분석에서는 canonical.json의 `type: "prose"` 중 TOC 유사 패턴을 가진 항목을 전수 스캔한 결과, 6건 외 추가 TOC 오염은 확인되지 않음.

### RQ-3 판정

- **6건 발견**: canonical.json에서 `type: "prose"`로 오분류된 TOC 항목 중 TSU가 생성된 5개 paragraph를 전수 스캔한 결과, 6건이 모두 포착됨. verified TSU 중 TOC 오염은 0건.
- **재현성**: 재현 스크립트는 부재하나, 본 분석에서 재현 가능한 방법(정규표현식 기반 TOC 패턴 매칭)으로 검증 완료.
- **추가 TOC 후보**: canonical.json에 266개의 TOC 유사 prose paragraph가 존재하지만, 이 중 TSU가 생성된 것은 5개 paragraph뿐이며 모두 rejected 처리됨.

---

## RQ-4 — F6 Citation Disclosure 문구 반영 필요성

### 근거

1. **코드베이스 검색 결과**: `NAE/` 디렉터리에서 "일괄 승인", "bulk approval", "per-item review", "Additional Notice", "individual review" 관련 키워드로 검색한 결과, **F6 관련 citation disclosure 문구는 아직 구현되지 않음**.

2. **존재하는 유일한 "일괄" 언급**: `NAE/pipeline/tsu/review_promotion.py:131`의 "여러 TSU 레코드에 동일한 검토 메타데이터를 일괄 적용한다"는 주석은 bulk metadata 적용에 관한 것이지, citation disclosure와 무관함.

3. **Amendment C §4 요구사항**: Vol.08 출처 claim에는 다음 추가 고지가 필요:
   > **추가 고지 (KR)** — 이 자료는 개별 항목 검수 없이 저작 단위로 일괄 승인되었습니다.
   > **Additional Notice (EN)** — This material was approved in bulk without per-item review.

### RQ-4 판정

**F6/F4 착수 시 이 요구사항을 반드시 반영해야 함.** 현재 코드베이스에 미구현 상태.

---

## 종합 판정: YELLOW (조건부 승인)

### 요약

| 항목 | 결과 |
|---|---|
| RQ-1 예외 승인 여부 | YELLOW — 조건부 승인 |
| RQ-2 잔존 Q1 오류 | 36% 오류율(FAIL 16% + BORDERLINE 20%) 확인 |
| RQ-3 TOC 스캔 재현성 | 6건 모두 포착, verified 중 TOC 오염 0건. 재현 스크립트 부재 |
| RQ-4 F6 Disclosure | 미구현. F4/F6 착수 시 필수 반영 |

### 승인 조건 (YELLOW 해제 조건)

Amendment C를 Approved로 승격하려면 다음 조건 충족 필요:

1. **F6/F4 착수 시 citation disclosure 구현**: Amendment C §4의 "이 자료는 개별 항목 검수 없이 저작 단위로 일괄 승인되었습니다" 문구를 retrieval UI에 반드시 반영할 것.

2. **잔존 Q1 오류에 대한 추가 검증 권고**: 36%의 Q1 오류율은 일괄 승인의 신뢰성을 심각하게 훼손함. F4 임베딩 전, doctrine별 또는 claim 길이 이상치 등 자동 스크리닝으로 표본 검증 최소 1회 수행할 것.

3. **Vol.08 한정 예외 재확인**: 본 Amendment가 Vol.01–07으로 확장되지 않도록 ADR-030에 각주 추가할 것.

### RED 시나리오 (승격 불가 조건)

다음 중 하나라도 해당되면 RED (승격 불가):

- CUE 대조 검증에서 본 결과와 상충하는 사실 발견
- HQ 서면 승인 미획득
- F6 disclosure 구현 없이 임베딩/색인 진행 시도

---

## 산출물

- 이 문서: `docs/architecture/ADR-030-AMENDMENT-C-C1-REVIEW-RESULT-001.md`
- 검증 스크립트(임시): 본 세션에서 직접 실행한 Python one-liner (저장소 외부 `/tmp/c1_q1_samples.txt`, `/tmp/c1_sample_ids.txt` 등)
- TOC 재현 분석: canonical.json 전수 스캔 (정규표현식 기반, 본 문서 §RQ-3 참조)

---

*판정: YELLOW (조건부 — 조건 명시)*
*C1 Independent Forensic Auditor · 2026-09-16*
