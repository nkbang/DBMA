---
title: "SESAME — C1 작업 순서 초안 (비승격 계획 메모)"
category: architecture-note
status: DRAFT — 비승격 계획 메모 (ADR 아님, 결정 기록 아님)
based_on:
  - docs/architecture/ADR-032-SESAME-Sermon-Style-Engine.md (§11 Work Sequence, §13 C1 Triggers, §15 Immediate Disposition)
  - CLAUDE.md > CUE Operating Policy v1.0 (C1 = 독립 검토, 구현 없음)
created: 2026-09-05
author: CUE
scope_modified: docs/architecture/notes/ only — 코드·데이터·코퍼스·config·ADR 미수정
---

# SESAME — C1 작업 순서 초안 (ADR-032 §11 대응)

> **이 문서는 ADR이 아니며 결정 기록이 아니다.** ADR-032 §11의 Work Sequence 골격에
> C1 독립 검토 라운드를 대응시킨 **계획 메모**다. 어떤 구현·본안 확장도 수행하지 않는다.

---

## 0. 발동 전제 (ADR-032 §0 · §15)

- 현재 SESAME는 **동결 보존(frozen)** 상태다. `docs/STATE.md`(2026-09-05) 및 ADR-032 §0
  HQ Decision에 따라 production mutation 및 SESAME 선행 구현(스텁·스키마·데이터 포함)이
  금지된다.
- 이 작업 순서는 HQ가 **현재 Release 배포 완료 이후 착수를 지시한 시점부터** 유효하다.
  그 전까지:
  - **C1**: 대기 (§15).
  - **CUE**: 이 골격을 보존만 한다. 본안 확장·P2 자산 재고·스텁·스키마·데이터 등
    SESAME 선행 작업을 일절 수행하지 않는다.
- 착수 지시 확인 방법: HQ 문서로 동결 해제 + Release 배포 완료 전제 충족을 확인한다.

## 0.1 C1 역할 한정 (CUE Operating Policy v1.0)

- C1은 **독립 검토(Audit)** 만 수행하고 **구현하지 않는다.**
- 아래 각 라운드의 유일한 산출물은 **C1 Review Report / 확인 메모**다.
- C1 Review 필수 트리거(정책): 새 ADR 작성 · 새 Architecture Layer 추가 ·
  Metadata Model 변경 · Validator 추가 · Migration 정책 변경 · Production 승격 직전 ·
  TSU Pipeline 진입 직전.

## 0.2 판정 코드

| 코드 | 의미 |
|---|---|
| `PASS` | 통과 — 다음 단계 진행 |
| `CONDITIONAL` | 조건부 통과 — 명시된 조건 해소 후 다음 단계 |
| `BLOCK` | 진행 중단 — HQ 회부 |

---

## 1. C1 라운드 개요

| 라운드 | 대응 §11 단계 | 성격 | 게이트 |
|---|---|---|---|
| C1-R0 | P0 이전 | 착수 전 상태 점검 | 동결 해제 미확인 시 `BLOCK` |
| C1-R1 | P1 | 본안 아키텍처 리뷰 ★필수 트리거 | `PASS` 없이 P2 불가 |
| C1-R2 | P2 | 자산 재고 감사 (읽기 전용) | `PASS` 없이 P4 불가 |
| C1-R3 | P3 | Style Corpus 요건 / Admission 절차안 리뷰 | `PASS` / `CONDITIONAL` |
| C1-R4 | P4 | `style_profile` 스키마 확정안 리뷰 ★Metadata Model 변경 | `PASS` 없이 P5 불가 |
| C1-R5 | P5 | 프로토타입 코드 배치 점검 (경량) | `PASS` / `CONDITIONAL` |
| C1-R6 | P6 | 독립 검증 ★C1 주도 | 재현성 미달 시 P4 회귀 |
| C1-R7 | P7 | 승격 게이트 확인 (4조건 중 ③) | 4조건 미충족 시 Proposed 유지 |
| C1-R8 | P8–P9 | 구현 통합 감사 | `PASS` / `CONDITIONAL` |
| (상시) | P10 | Voice/TTS 감시 | 별도 ADR 없이 등장 시 `BLOCK` |

---

## 2. 라운드 상세

### C1-R0 — 착수 전 상태 점검 (§11 P0 이전)

| 항목 | 내용 |
|---|---|
| 트리거 | HQ 착수 지시 접수 |
| C1 행동 | 동결 해제가 HQ 문서로 확인되는지, Release 배포 완료 전제가 충족되었는지 확인 |
| 검토 범위 | ADR-032 §0 / §15 조건, `docs/STATE.md` 프리즈 항목 해제 여부 |
| Gate | 동결 해제 미확인 시 `BLOCK` — 이후 전 단계 정지 |
| 산출물 | C1-R0 확인 메모 (1p) |

---

### C1-R1 — 본안 아키텍처 리뷰 ★필수 트리거 (§11 P1 / §13)

| 항목 | 내용 |
|---|---|
| 선행 | CUE가 §11 P0 완료 — ADR-032 골격 → 본안 확장 (명명·귀속·종속 계약·OUT-OF-SCOPE 확정, §15 재검토 대상 4건 반영) |
| 트리거 근거 (§13) | 새 ADR 작성 ✔ / 새 Architecture Layer(TLI Style Engine 구체화) ✔ / Metadata Model 변경(`style_profile` 신설) ✔ |
| C1 검토 범위 | ① 명명·아키텍처 귀속 (§2, §4) — TLI 범위 안 / 형제 계층(O-1)이 HQ 결정으로 확정됐는지 |
| | ② 종속 계약 (§5) — ADR-002 단방향 참조 / ADR-009 SIL 대칭축("how") / ADR-012 DBMA-SEQ 라우팅 / ADR-030 Admission 경유 / ADR-001 무변경 |
| | ③ OUT-OF-SCOPE (§3) — Voice·TTS 전면 제외(§3.1), few-shot 축소 금지(§3.2), 신규 Retrieval 경로 금지(§3.3), CLEAN 코퍼스 동결(§3.4) |
| | ④ `style_profile` 후보 스키마 (§6) — "동결하지 않음"이 명시됐는지 |
| | ⑤ Provenance 요건 (§7), Verification Principle (§8) |
| | ⑥ Open Questions O-1~O-5 중 HQ 회부 필요 항목이 남았는지 |
| 리스크 대조 | R-2(TSU/retrieval 은근한 결합), R-4(Voice 범위 오염), R-5(Proposed 근거 조기 구현), R-7(TLI 배치 표류) |
| Gate | `PASS` 없이는 §11 P2 진행 불가. `CONDITIONAL` 시 조건 목록을 CUE 반영 후 재검토 |
| 산출물 | **C1 Independent Review Report — ADR-032 본안** |

---

### C1-R2 — 자산 재고 감사 (§11 P2, 읽기 전용)

| 항목 | 내용 |
|---|---|
| 선행 | CUE가 `sermon_corpus/analyzer/` (frequency · keywords · book_themes · corpus_statistics) 커버리지 vs §4 A~F 도메인 갭 조사 (읽기 전용) |
| C1 검토 범위 | ① 조사가 **읽기 전용**으로 수행됐는지 (코드·데이터·config 무변경 확인) |
| | ② 신규 top-level 패키지 없음, 확장 지점이 `sermon_corpus/analyzer/style/` 하위로 한정됐는지 (§9) |
| | ③ 이미 존재하는 통계를 재정의 없이 참조하는 설계인지 (R-1 재발명 차단) |
| Gate | `PASS` 없이는 P4(스키마) 진행 불가 — §11 "P2를 P4보다 반드시 먼저" |
| 산출물 | C1-R2 감사 메모 + 갭 목록 검증 |

---

### C1-R3 — Style Corpus 요건 / Admission 절차안 리뷰 (§11 P3)

| 항목 | 내용 |
|---|---|
| C1 검토 범위 | ① ADR-030 Admission Decision (`NAE/governance/corpus_admissions.jsonl`, append-only) 절차 준수 |
| | ② Track 분리 — Style Corpus가 TSU Track / Reference Track과 별개로 취급되는지 |
| | ③ rights 필드 포함 (R-6 저작권) |
| | ④ O-2(단일 설교자 코퍼스로 시작) / O-4(기존 `sermon_corpus/` 수집물 = 신규 Admission 기록, 소급 승인 아님) HQ 기본값 반영 |
| Gate | `PASS` / `CONDITIONAL` |
| 산출물 | C1-R3 Review Report |

---

### C1-R4 — `style_profile` 스키마 확정안 리뷰 ★Metadata Model 변경 (§11 P4)

| 항목 | 내용 |
|---|---|
| C1 검토 범위 | ① §6 원칙 — analyzer 출력의 rollup/consumer로 정의, **중복 필드 신설 금지** (ADR-030 F-1 준용) |
| | ② `profile_id`가 SESAME 자체 네임스페이스이며 TSU `document_id`와 무관한지 |
| | ③ `corpus_scope.sermon_ids`가 **참조만** (ADR-002 단방향), 역방향 결합 없음 |
| | ④ provenance 블록이 NAE 레코드와 동일 형식 (§7), `content_style_separation: true` |
| | ⑤ 각 축(structure / rhetoric / language / illustration / application / transition / conclusion) 내부 필드가 P6 검증 전까지 **후보**로만 표기됐는지 |
| 리스크 대조 | R-2(결합), R-3(유사도 % 남발 — 자연어 서술 강제) |
| Gate | `PASS` 없이는 P5 프로토타입 착수 불가 |
| 산출물 | **C1 Independent Review Report — style_profile 스키마** |

---

### C1-R5 — 프로토타입 코드 배치 점검 (§11 P5, 경량)

| 항목 | 내용 |
|---|---|
| 선행 | CUE가 대표 설교 3~5편으로 `sermon_corpus/analyzer/style/` 확장 프로토타입 |
| C1 검토 범위 | ① 코드 배치가 §9 표 준수 (`sermon_corpus/analyzer/style/`, 신규 top-level 금지) |
| | ② `core/generation.py::SermonDraftService` **최소 변경**, `style_examples` fallback 유지 |
| | ③ 스타일 어휘·임계값이 코드 하드코딩이 아니라 리소스/데이터 (§4) |
| | ④ `RetrievalEngine` 신규 의존 없음 (§5.5) |
| Gate | `PASS` / `CONDITIONAL` |
| 산출물 | C1-R5 점검 메모 |

---

### C1-R6 — 독립 검증 ★C1 주도 (§11 P6)

| 항목 | 내용 |
|---|---|
| C1 행동 | DBMA-SEQ harness (ADR-012 골든셋 패턴) 재사용하여 프로파일 **재현성·안정성** 측정 |
| 판정 기준 (§8) | `반복 관찰 + 통계적/질적 유의미 + 다수 설교에 걸쳐 안정 + 설교 소통에 의미` 4요소 동시 충족 특성만 유효 |
| 금지 확인 | 백분율 유사도 점수 산출 금지 (§5.3), "확실하지 않음" 그대로 노출, 최종 판단은 목회자 |
| Gate | 재현성 미달 축은 스키마에서 제거 권고. `BLOCK` 시 P4로 회귀 |
| 산출물 | **C1 검증 리포트 — 프로파일 재현성/안정성** (자연어 서술) |

---

### C1-R7 — 승격 게이트 확인 (§11 P7 / §14)

| 항목 | 내용 |
|---|---|
| C1 행동 | ADR-032 Proposed → Approved 4조건 중 **③ C1 독립 리뷰 완료** 확인서 발행 |
| 확인 범위 | C1-R1 · R4 · R6 모두 `PASS`, 회귀 테스트 PASS 첨부, ADR Conflict 재확인 (ADR-001 / 002 / 009 / 012 / 030) |
| Gate | 4조건(구현 완료 / 회귀 PASS / C1 완료 / HQ 승인) 중 하나라도 미충족 시 Proposed 유지 |
| 산출물 | C1 승격 확인서 |

---

### C1-R8 — 구현 통합 감사 (§11 P8–P9)

| 항목 | 내용 |
|---|---|
| 선행 | P8 `core/tli/style_engine.py` 인터페이스 + 프로파일 조회 / P9 `SermonDraftService` 통합 (`style_examples` → `style_profile` 승격, fallback 유지) |
| C1 검토 범위 | ① 어댑터 인터페이스 뒤 배치 (§4), 구현체가 리소스/데이터 기반 |
| | ② 프롬프트에서 신학 근거 영역과 스타일 영역이 분리됐는지 (ADR-009 대칭축 유지, SIL 대체 아님) |
| | ③ 기존 `style_examples` 경로 회귀 테스트 PASS |
| | ④ Retrieval · TSU · Embedding · RAW 무변경 |
| Gate | `PASS` / `CONDITIONAL` |
| 산출물 | C1-R8 통합 감사 리포트 |

---

### P10 — Voice / TTS (C1 상시 감시)

- ADR-032 §3.1 전면 제외 항목. **별도 HQ 승인 + 별도 ADR 없이** 스키마·인터페이스·스텁이
  등장하면 즉시 `BLOCK` (R-4).

---

## 3. 의존 관계 요약

```text
C1-R0 ─ C1-R1(필수/게이트) ─ C1-R2 ─ C1-R3 ─ C1-R4(필수/게이트) ─ C1-R5 ─ C1-R6(C1주도/게이트) ─ C1-R7(승격) ─ C1-R8
                                    └─ P2는 반드시 P4보다 먼저 ─┘
```

---

## 4. 참고 — 착수 시 재검토 대상 (ADR-032 §0 지시)

- DBMA-TLI "Style Engine" 슬롯 (`DBMA-TLI-Architecture-Vision-v1.md` §4)
- `sermon_corpus/analyzer/` 커버리지 및 확장 지점
- ADR-002 (내용/스타일 분리 패턴) · ADR-009 (SIL 통합 지점) ·
  ADR-012 (DBMA-SEQ 평가) · ADR-030 (Sermon Corpus Governance)

---

*본 메모는 `docs/architecture/notes/`만 대상으로 작성되었다. 어떤 코드·데이터·코퍼스·config·ADR도
수정하지 않았다. ADR-032 §15 동결이 해제되기 전까지 이 문서는 참고용으로만 보존된다.*
