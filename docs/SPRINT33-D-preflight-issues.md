# Pre-SPRINT33-D Preflight — Issue Resolution

상태: 고정(fixed). SPRINT33-D 착수 전 ADR-007 선행 조건 재검토 결과.

## 1. TinyFragment × Heading Interaction

```text
Status: Deferred / Won't-fix at Boundary Score Layer
Owner:  pdf_structure_detector calibration
Impact: No SPRINT33-D blocker
```

### 조사 근거

heading feature가 매칭된 409건 중 105건(25.7%)이 동시에 tiny(<80자) —
Phase 5 Preflight가 지적한 문제가 무시할 수 없는 규모임을 확인했다.

30건 원문 대조 결과, 정확히 반반으로 구성됨을 확인:

```text
진짜 짧은 제목(legitimate):
  "Explanation"
  "Form/Structure/Setting"          (WBC 표준 섹션 라벨)
  "요 18:15-27 베드로가 예수를부인하다"
  "마가복음 3:7-19 열두제자를임명하시다"

OCR 잡음(garbage):
  "화"  "욕"  "캔 익"  "샘 마"  "떠 。 r} 써"  "써써 때 면 듀 뺀"
```

### 결정 근거

현재 Boundary Score 계층이 candidate에 대해 관측하는 정보는 다음
5가지뿐이다:

```text
candidate length / heading 여부 / scripture reference 여부 /
sentence boundary 여부 / paragraph 여부
```

이 정보만으로는 위의 "정상" 그룹과 "비정상" 그룹을 구분할 수 없다 —
두 그룹의 feature vector가 동일하므로 score도 동일하며, weight나
threshold를 아무리 조정해도 한쪽만 선택적으로 억제하는 것은 원리적으로
불가능하다. 이는 semantic boundary scoring의 문제가 아니라, PDF
extraction → heading candidate 품질 → OCR noise filtering 단계의
문제다(SPRINT32-F에서 이미 "pdf_structure_detector calibration은
범위 밖"으로 명시적으로 분리된 이슈와 동일 계열).

### 처리

SPRINT33-D 착수 조건에서 제외한다. pdf_structure_detector calibration이
별도로 착수될 때 함께 다룬다.

---

## 2. PageHeaderArtifact

```text
Feasibility:    PASS
Evidence:       2 Kings Vol.13, repeat interval median 25 candidates,
                majority range 9~56 candidates, window 60~100 가능성 확인
Implementation: NOT APPROVED
Architecture:   Separate ADR required
```

### 조사 근거

"2 Kings, Volume 13"에서 동일 성구 참조가 반복 등장하는 간격(candidate
순번 기준)을 실측: min=9, median=25, max=1609(이상치, 우연한 재언급
추정), 대부분 9~56 구간에 분포. "최근 W개 candidate 이내에 동일
참조가 이미 boundary로 판정된 적 있는가"를 판별하는 stateful feature가
기술적으로 타당함(window ≈ 60~100).

### 결정 근거

기존 5개 feature는 전부 candidate 1개만으로 판단 가능한 stateless
구조였다(heading feature의 cursor조차 provider가 준 순서 정보를
소비할 뿐, 스스로 이력을 축적하지 않음). PageHeaderArtifact는
"최근 등장 이력"을 스스로 누적해야 하는 최초의 stateful feature로,
추가되는 것이 단순 feature 하나가 아니라 "Boundary Detector + State
Management Layer"라는 구조적 확장이다. 이는 ADR 수준의 설계 변경으로
판단, 별도 세션에서 다룬다.

### 처리

SPRINT33-D 설계에 직접 포함하지 않는다. Feasibility는 확인되었으므로
후속 ADR 후보로 유지한다.

---

## 3. SPRINT33-D Scope Boundary

```text
목표: Hierarchical Chunk Builder Prototype

목적: Semantic Boundary Detector가 실제 chunk reconstruction에서
어느 정도 개선을 주는지 측정.

포함:
  candidate boundary ranking
        ↓
  hierarchical split proposal
        ↓
  shadow chunk generation
        ↓
  D-5 metrics 측정

금지:
  ❌ production chunking_optimizer.py 변경
  ❌ 기존 chunk 데이터 교체
  ❌ PageHeaderArtifact 구현
  ❌ OCR heading correction 구현
  ❌ Retrieval Engine 연결
```

---

## 4. Known Limitations (SPRINT33-D 착수 시점 기준)

```text
- ADR-007 §1(minimum improvement threshold) / §2(orphaned acceptance
  range) 수치는 여전히 미확정 — SPRINT33-D 시제품 결과로 재산정 예정.
- TinyFragment×Heading으로 인한 heading-matched candidate의 약 25.7%
  (그 중 절반은 OCR 잡음)가 여전히 boundary로 판정됨 — Hierarchical
  Chunk Builder의 shadow 결과 해석 시 이 잡음이 섞여 있음을 감안해야
  한다.
- PageHeaderArtifact 미구현으로, running-header 반복 패턴(Phase 4-C/
  6-B에서 확인된 "2 Kings, Volume 13"의 주요 오탐 원인)이 여전히
  D-5 metrics에 섞여 들어갈 수 있다.
- pdf_structure_detector 자체의 calibration은 SPRINT32-F 이후 계속
  범위 밖으로 유지되고 있다 — SPRINT33-D 결과 해석 시 detector 신뢰도
  편차(문서별 heading 매칭 밀도 차이)가 여전히 근본 변수로 남는다.
```

## 최종 상태

```text
SPRINT33-C                    CLOSED
Pre-SPRINT33-D Preflight      CLOSED
TinyFragment×Heading          Won't-fix at Boundary Layer
PageHeaderArtifact            Separate ADR candidate
SPRINT33-D                    APPROVED TO START
```
