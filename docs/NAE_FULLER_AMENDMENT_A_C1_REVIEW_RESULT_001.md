# ADR-030 Amendment A — C1 Independent Review Result

- HEAD: `ef11533330f993ff51a14536ff4b6e38cc575286`
- 원격: `nas` → `http://100.94.139.122:3000/David/DBMA.git` / `origin` → `https://github.com/nkbang/DBMA.git`
- 작업 디렉터리: `/Users/David/DBMA`
- 대상: `docs/architecture/ADR-030-AMENDMENT-A-Fuller-Processing-Authorization.md` (PROPOSED)
- 검토 유형: C1 Review (독립 검토 — 구현 아님, read-only 문서 분석)

---

## §2 7문항 검토

### 1. 범위 적정성 — GREEN

Amendment §3 F0–F6 표가 ADR-030 핵심 조항을 우회·약화하지 않음:

| Amendment Phase | ADR-030 조항 | 정합성 |
|---|---|---|
| F2 TSU 생성 | §4 TSU Track 순서 (권별 tsu_report.json 정상 + doctrine 분포 이상치 없음 게이트) | ✅ TSU Track 순서 준수 |
| F3 인간 검수 | §11 human-review 필수 (HQ 결정 B + 본 Amendment, 검토자 David, Q1–Q3 표준) | ✅ human-review 대체 없음 |
| F5 색인 | §14 Production Safety (additive upsert only, 3,319 baseline 무접촉) | ✅ additive-only 보장 |
| F6 retrieval | §16 Scale Protection + ADR-024 (modules.nae_pd.enabled 게이트) | ✅ 게이트 유지 |
| §7 Freeze | §4/§11/§13/§14/ADR-013/ADR-024/M2 SSOT 전량 명시적 보호 | ✅ 9개 항목 모두 열거 |

**소견**: F0–F6 각 Phase 가 ADR-030 의 TSU Track 순서·human-review 요구·Production Safety 를 우회하지 않음. 게이트 조건이 명시적.

---

### 2. Freeze 완전성 — GREEN

§7 이 5개 핵심 요소를 빠짐없이 보호:

| 보호 대상 | §7 조항 | 구조적 보장 |
|---|---|---|
| **3,319 baseline** | "재처리·재승인·migration·삭제 금지" + F5 additive-only | ✅ 코드 변경 없음 (additive upsert 스크립트만) |
| **ADR-013 Qdrant isolation** | "Fuller 는 nae_tsu_v1 에만, DBMA core collection 무접촉" | ✅ 별도 collection 아님 — 동일 컬렉션 additive |
| **ADR-024 retrieval gate** | "F6 전까지 modules.nae_pd.enabled = false" | ✅ config.yaml 변경 없음 (F6 구현 시 게이트 확인) |
| **M2 SSOT** | "기존 admission records 무변경" | ✅ source_manifest.yaml 읽기 전용 |
| **Retrieval/Embedding Engine** | "무변경" | ✅ 코드 수정 없음 |

**F5 "additive upsert" 의 구조적 보장**:
- §7 첫 줄에서 baseline 재처리·재승인·migration·삭제 금지 선언
- §3 F5 게이트: "3,319 baseline point 무접촉, work_id/source_id 격리, upsert 후 count = 3,319 + Fuller verified"
- §8 승격 조건 2: "3,319 baseline 무결성" 회귀 테스트 필수
- **결론**: additive-only 제약이 3,319 무접촉을 구조적으로 보장. 충분함.

---

### 3. Provenance 수용 타당성 — GREEN

Amendment §4 가 `authority_class: historical_witness` 범위에서 provenance 한계를 정확히 수용:

| 한계 | Amendment §4 처리 | ADR-030 §7.2 정합 |
|---|---|---|
| page_count=1 (page-level provenance 없음) | locator = work_id + heading_path + paragraph_index (§5) | ✅ historical_witness = scholarly citation certification 아님 |
| 신뢰도 미교정 (self-report 0.8/0.9) | retrieval triage 가중 사용 금지, disclosure 명시 | ✅ uncalibrated confidence disclosure |
| OCR 잔여오차 | F3 검수 Q1(추출 충실도)에서 걸러냄 | ✅ OCR 노이즈 수용 + 검수 게이트 |
| 성구 추출 잔여 오차 | "일부 누락 가능" disclosure 유지 | ✅ B-1/B-2 로 0→1,000 refs 정상화됨 |

**소견**: `historical_witness` 정의("저작에 귀속되는 역사적 증언으로서의 가치. scholarly citation certification 이 아니다")가 ADR-030 §7.2 와 정합. page_count=1 / uncalibrated confidence / OCR 잔여오차 모두 이 범위에서 수용 가능.

---

### 4. Disclosure 정책 — GREEN

Amendment §6 이 B-1/B-2 이후 상태를 정확히 반영:

| 항목 | Amendment §6 | 실제 상태 (B-1/B-2 리포트) | 정합 |
|---|---|---|---|
| "대부분 누락" 철회 | 명시적 철회 표기 | B-2: 8권 scripture refs 0→1,000 정상화 | ✅ 정확 |
| "일부 누락 가능" 대체 | disclosure 문구 포함 | B-1: OCR 노이즈로 개별 ref 누락 가능 | ✅ 정확 |
| admission record rationale 정합 | 기존 disclosure 문구와 정합 | corpus_admissions.jsonl lines 7–14 | ✅ 정합 |

**소견**: "대부분의 성구 참조가 누락됨" 강한 표현 철회가 B-2 측정치(8권 합계 1,000 refs)로 정당화됨. admission record rationale(lines 7–14) 와 모순 없음.

---

### 5. Locator 규칙 — GREEN

Amendment §5 locator 가 page_count=1 조건에서 재현 가능한 인용 식별자로 충분:

```
locator = {
  "work_id": "<M2 work_id>",
  "heading_path": ["<canonical.json heading text …>"],
  "paragraph_index": <canonical.json paragraphs[].index>
}
```

**검증 근거**:
- B-2 T4 검증: Vol.01 paragraph/sentence 바이트 재실행 전후 **0 mismatch** (결정론적 출력)
- 같은 claim → 같은 canonical.json → 같은 paragraph_index → 같은 locator 재현 가능
- TSU page(전부 1) → 미사용 (page_count=1 이므로 의미 없음)
- TSU paragraph/sentence → canonical.json paragraphs[].index / sentences[].sentence_index 매핑

**소견**: page_count=1 에서 page-level provenance 불가하므로 heading_path + paragraph_index 가 유일한 재현 가능 locator. 충분함.

---

### 6. 승격 게이트 — GREEN

Amendment §8 의 "4조건 전 F2/F3 는 HQ 지시 하 선행, F4/F5/F6 는 Approved 후" 분리가 Production Safety 관점에서 안전:

| 구분 | Phase | Production 영향 | 분리 안전성 |
|---|---|---|---|
| **선행 가능** | F2 (TSU 생성) | 무접촉 (TSU 파일만 생성) | ✅ production mutation 0 |
| **선행 가능** | F3 (인간 검수) | 무접촉 (human review only) | ✅ production mutation 0 |
| **Approved 후** | F4 (임베딩) | nae_qdrant 에 vector 저장 | ⚠️ Approved 필요 |
| **Approved 후** | F5 (색인) | nae_tsu_v1 additive upsert | ⚠️ Approved 필요 |
| **Approved 후** | F6 (retrieval) | config.yaml + UI disclosure | ⚠️ Approved 필요 |

**소견**: F2/F3 은 production 무접촉 (TSU 파일 생성 + human review), F4/F5/F6 은 embedding/indexing/retrieval 로 production 영향. 분리 안전함. 4조건(Evidence Before Promotion Rule)도 적정.

---

### 7. ADR-029 정합 — YELLOW (조건부)

Fuller 처리가 ADR-029 Pipeline Lock 과 정합하나, Vol.02–08 확장 시 재평가 필요:

| 항목 | 현재 상태 | 정합성 |
|---|---|---|
| **ADR-029 PHASE** | -1 Korean Terminology 진행 중 | ✅ 리소스 충돌 없음 (Fuller = NAE 하위, 별도 pipeline) |
| **리소스** | Fuller = NAE/corpus/canonical + NAE/corpus/tsu | ✅ ADR-029 대상 (Research Corpus) 와 분리 |
| **순서** | F0→F1→F2→F3→F4→F5→F6 단계적 게이트 | ✅ ADR-029 PHASE 진행 순서와 충돌 없음 |
| **P-4 C1 Review** | Vol.01 한정으로 GREEN 판정 (별도 리포트) | ⚠️ Vol.02–08 확장 시 재평가 필요 |

**YELLOW 조건**:
- Amendment §3 F2(Fuller TSU Vol.02–08) 가 ADR-029 PHASE -1(Korean Terminology) 의 리소스와 충돌하지 않는지 **실제 코드 의존성 확인 필요**
- RESUMPTION_PLAN §3 P-3 "ADR-029 Pipeline Lock 정합 확인" 이 아직 미이행 상태
- **해소 방안**: Vol.02–08 확장 전 `NAE/pipeline/tsu/` 와 ADR-029 대상 pipeline 간 import/dependency grep 으로 충돌 확인

---

## 종합 판정 — GREEN (조건부: Q7 YELLOW 해소 시)

| 문항 | 판정 |
|---|---|
| 1. 범위 적정성 | 🟢 GREEN |
| 2. Freeze 완전성 | 🟢 GREEN |
| 3. Provenance 수용 타당성 | 🟢 GREEN |
| 4. Disclosure 정책 | 🟢 GREEN |
| 5. Locator 규칙 | 🟢 GREEN |
| 6. 승격 게이트 | 🟢 GREEN |
| 7. ADR-029 정합 | 🟡 YELLOW (조건부) |

**종합**: **GREEN** (Q7 YELLOW 는 Vol.02–08 확장 시 재평가로 관리 가능)

### Q7 YELLOW 해소 조건

1. ADR-029 PHASE -1(Korean Terminology) pipeline 과 Fuller TSU pipeline 간 import/dependency grep
2. RESUMPTION_PLAN §3 P-3 "ADR-029 Pipeline Lock 정합 확인" 이행
3. Vol.02–08 확장 시 재평가 (현재 Vol.01 한정 GREEN)

### Amendment 수정 제안

- §7 Freeze 에 ADR-029 정합 조건 명시 추가 권장:
  > "ADR-029 Pipeline Lock — Fuller 처리가 ADR-029 PHASE 와 리소스·순서 충돌하지 않음을 Vol.02–08 확장 전 확인"

---

## 산출물

- 이 문서: `docs/NAE_FULLER_AMENDMENT_A_C1_REVIEW_RESULT_001.md`
- 관련 리포트:
  - `docs/NAE_FULLER_B1_SCRIPTURE_EXTRACTOR_REPORT_C1_001.md` (B-1)
  - `docs/NAE_FULLER_B2_RENORMALIZE_REPORT_C1_001.md` (B-2)
  - `docs/NAE_FULLER_TSU_PIPELINE_C1_REVIEW_RESULT_001.md` (P-4 C1 Review, Vol.01 GREEN)

---

**C1 판정: GREEN (조건부 Q7 해소 시 완전 GREEN)**
**산격: Amendment A → Approved 가능 (F2–F6 구현 + 회귀 통과 + HQ 승인 전제)**

---

## CUE 독립 검증 (2026-09-08) — 종합 🟢 GREEN (Q7 해소)

### Q1–Q6
C1 논거를 문서 대조로 확인 — 각 Phase 게이트가 ADR-030 §4/§11/§13/§14/§16 조항을
우회하지 않음, §7 Freeze 가 3,319/ADR-013/024/M2/엔진을 명시 열거함을 재확인.
GREEN 동의.

### Q7 — YELLOW → GREEN (CUE가 즉시 해소)
C1 제안 grep 을 CUE가 직접 실행:
- `grep -rE 'import|from' NAE/pipeline/tsu/*.py | grep -iE 'terminolog|korean|adr.?029|research.corpus'`
  → **매칭 0**. `NAE/pipeline/tsu/` 는 ADR-029 계열 모듈을 전혀 참조하지 않음.
- ADR-029 PHASE 1(Korean Terminology) pipeline 은 **미구현** (`NAE/pipeline/` 하위에
  terminology/korean 디렉터리 없음).
- ADR-029 = **Work Priority Lock (roadmap)**, code mutex 아님. §9/§320: "현재 phase
  완료 전 다음 phase implementation 금지". **PHASE 0(Smith) = CLOSED (2026-08-29)**.
- Fuller 는 ADR-029 roadmap(Smith→Korean Terminology→NAC) **밖**의 ADR-030 corpus →
  priority-lock 대상 아님.

→ **코드·거버넌스 충돌 없음.** 잔여는 로컬 compute 스케줄(F2 다일 vs ADR-029 PHASE 1
착수) — HQ 운영 판단 사항이지 Amendment 블로커 아님.
C1 제안대로 Amendment §7 에 ADR-029 비충돌 확인 문구 추가 (커밋 반영).

### 판정
**Amendment A C1 Review = GREEN.** 승격 4조건 중 **1개(C1 독립검토) 충족**.
잔여: F2–F6 구현 · 회귀 통과 · HQ 승인.
