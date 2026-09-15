# C1 Review 요청 — ADR-030 Amendment A (Fuller Processing Authorization)

- 요청자: CUE
- 일자: 2026-09-08
- 유형: **C1 Review** (독립 검토 — 구현 아님)
- 트리거: CLAUDE.md CUE Operating Policy "C1 Review 요청 시점: 새 ADR 작성"
- 대상: `docs/architecture/ADR-030-AMENDMENT-A-Fuller-Processing-Authorization.md` (PROPOSED, `8bed14f`)

---

## 1. 배경

ADR-030 §12 N-9 는 Fuller Vol.01–08 을 ADMITTED / PROCESSING HOLD 로 둔다.
Amendment A 는 그 HOLD 를 명시 조건 하 해제하고 provenance 한계 수용·citation
disclosure·인용 locator 를 고정한다. Evidence Before Promotion Rule 상
Proposed → Approved 4조건 중 하나가 **C1 독립 검토**.

---

## 2. 검토 질문

1. **범위 적정성** — Amendment §3 F0–F6 인가 표가 ADR-030 §4(TSU Track 순서)·
   §11(human-review 필수)·§13(Migration)·§14(Production Safety)·§16(Scale)
   중 우회·약화하는 것이 있는가?
2. **Freeze 완전성** — §7 이 3,319 baseline / ADR-013 / ADR-024 / M2 SSOT /
   엔진을 빠짐없이 보호하는가? F5 "additive upsert" 가 3,319 무접촉을
   **구조적으로** 보장하는 조건이 §3·§8 에 충분히 걸려 있는가?
3. **Provenance 수용 타당성** — §4 가 `authority_class: historical_witness`
   범위에서 `page_count=1` / uncalibrated confidence / OCR 잔여오차를
   수용하는 논거가 ADR-030 §7.2 와 정합하는가?
4. **Disclosure 정책** — §6 이 B-1/B-2 이후 상태(성구 0→1,000 정상화)를
   정확히 반영하는가? pre-B2 "대부분 누락" 철회가 타당한가? admission
   record rationale(lines 7–14)와 모순 없는가?
5. **Locator 규칙** — §5 `work_id + heading_path + paragraph_index` 가
   `page_count=1` 조건에서 재현 가능한 인용 식별자로 충분한가?
6. **승격 게이트** — §8 "4조건 전 F2/F3 는 HQ 지시 하 선행, F4/F5/F6 는
   Approved 후" 분리가 Production Safety 관점에서 안전한가?
7. **ADR-029 정합** — Fuller 처리가 ADR-029 Pipeline Lock 의 현재 PHASE 와
   리소스·순서 충돌하는가? (P-4 C1 Review 는 Vol.01 한정으로 GREEN 판정했음
   — Vol.02–08 확장 시 재평가)

---

## 3. 요청 형식

- 판정: GREEN / YELLOW(조건부) / RED
- 조건부·RED 시 구체 findings + 해소 방안 + Amendment 수정 제안
- 산출물: `docs/NAE_FULLER_AMENDMENT_A_C1_REVIEW_RESULT_001.md`
- C1 은 이 검토에서 **구현하지 않는다** (문서 검토 + 코드 read-only).
- 보고 첫 줄: `git rev-parse HEAD` / `git remote -v` / `--show-toplevel`.

## 4. 승격 경로

C1 Review GREEN(또는 조건 해소) + F2–F6 구현 + 회귀 통과 + HQ 승인
→ Amendment A Status PROPOSED → Approved.
