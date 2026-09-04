# C1 Independent Cross-Verification Report
## CORPUS-FACTORY-INTEGRATION-PILOT-001

**Task Order:** C1-TASK-ORDER-CFI-PILOT-001-CROSS-VERIFICATION
**Auditor:** C1 (Independent Forensic Auditor)
**Date:** 2026-08-17
**Status:** NOT VERIFIED — 3개 항목 중 2개에서 실제 결함 발견

---

## Gate 판정: NOT VERIFIED

C1은 CUE gate를 스스로 PASS로 선언하지 않는다. 아래 발견 사항을 CUE에 제출한다.

---

## 검증 1: Namespace 격리

### CUE의 주장
> `(task_type, scope.namespace)` 조합과 `task_id` prefix를 둘 다 강제해서, corpus-factory-pilot task가 control-plane-pilot 리소스에 접근하거나 그 반대가 불가능하다.

### 실제 테스트 명령
```python
# pilot_executor.py :: check_isolation_contract() 직접 호출 테스트
from pilot_executor import check_isolation_contract

# Test 1a: CONTROL-PLANE-PILOT task_id + corpus-factory-pilot namespace
test_1a = {
    'task_id': 'CONTROL-PLANE-PILOT-NS-BYPASS-001',
    'task_type': 'corpus_pilot_echo',
    'scope': {'namespace': 'corpus-factory-pilot'},
    'production_mutation': False,
}
check_isolation_contract(test_1a)  # → NAMESPACE_VIOLATION ✓

# Test 1b: CORPUS-FACTORY-PILOT task_id + control-plane-pilot namespace
test_1b = {
    'task_id': 'CORPUS-FACTORY-PILOT-NS-BYPASS-001',
    'task_type': 'pilot_echo',
    'scope': {'namespace': 'control-plane-pilot'},
    'production_mutation': False,
}
check_isolation_contract(test_1b)  # → NAMESPACE_VIOLATION ✓
```

### 코드 근거 (pilot_executor.py line 265-290)
```python
def check_isolation_contract(data: dict) -> str | None:
    task_id = data.get("task_id", "")
    task_type = data.get("task_type")
    scope = data.get("scope") or {}
    namespace = scope.get("namespace")
    production_mutation = data.get("production_mutation")

    if (task_type, namespace) not in ALLOWED_COMBINATIONS:
        return "TASK_TYPE_NOT_AUTHORIZED"
    expected_prefix = next(
        (p for p, ns in TASK_ID_PREFIX_NAMESPACE.items() if ns == namespace), None
    )
    if not expected_prefix or not task_id.startswith(expected_prefix):
        return "NAMESPACE_VIOLATION"
    ...
```

### ✅ 논리 검증: 통과
`check_isolation_contract()` 자체는 `(task_type, namespace)` 조합과 `task_id` prefix를 모두 검증하여 namespace 격리를 올바르게 강제한다.

### ❌ 파일시스템 레벨 발견 (중요)
**heartbeat와 evidence가 namespace별로 분리되지 않음:**

```python
# pilot_executor.py line 46-47
PILOT_EVIDENCE_DIR = EVIDENCE_DIR / "night-shift" / "control-plane-pilot"
HEARTBEAT_DIR = PROJECT_ROOT / ".automation" / "night-shift" / "heartbeats"
```

실제 파일 시스템 확인:
```
$ ls .automation/night-shift/heartbeats/
CONTROL-PLANE-PILOT-010-BASE.json    ← control-plane-pilot
CONTROL-PLANE-PILOT-040-REGRESSION.json  ← control-plane-pilot
CORPUS-FACTORY-PILOT-001.json         ← corpus-factory-pilot (섞여 있음!)

$ ls .automation/evidence/night-shift/control-plane-pilot/
CONTROL-PLANE-PILOT-001-*              ← control-plane-pilot
CORPUS-FACTORY-PILOT-001-*             ← corpus-factory-pilot (섞여 있음!)
```

**판정:** 논리적 격리는 통과하지만, 파일시스템 레벨에서 namespace가 분리되지 않음. 두 namespace의 heartbeat와 evidence가 같은 디렉터리에 섞여 저장됨. 이는 "namespace 분리" 주장을 파일시스템 레벨에서 약화시킨다.

---

## 검증 2: CLI-driver Boundary

### CUE의 주장
> `corpus_pilot_echo` task_type은 항상 `subprocess.run([...])`로 `.automation/control-plane/fixtures/corpus_pilot_driver.py`를 호출하며, executor 코드 안에 그 로직이 인라인되어 있지 않다.

### 실제 grep 결과 (매치된 줄 전체 읽음)

**pilot_executor.py — import 관련 줄:**
```
Line 11: - NEVER import NAE.pipeline.* / core.retrieval / any production module.  ← 주석
Line 12: - NEVER invoke NAE/pipeline/registration/cli_driver.py or any other       ← 주석
Line 33: from __future__ import annotations                                         ← 실제 import
Line 35: import argparse                                                              ← 실제 import
Line 36: import json                                                                  ← 실제 import
Line 37: import subprocess                                                            ← 실제 import
Line 38: import time                                                                  ← 실제 import
Line 39: from datetime import datetime, timezone                                      ← 실제 import
Line 40: from pathlib import Path                                                     ← 실제 import
```
→ NAE, core.retrieval, cli_driver 관련 **실제 import 없음**. 주석만 존재.

**corpus_pilot_driver.py — import 관련 줄:**
```
Line 3: cli_driver.py *pattern* only ...  ← 주석
Line 8: Zero imports from NAE.* or core.*  ← 주석
Line 16: from __future__ import annotations  ← 실제 import
Line 18: import argparse                     ← 실제 import
Line 19: import sys                           ← 실제 import
Line 20: from datetime import datetime, timezone  ← 실제 import
```
→ NAE, core 관련 **실제 import 없음**.

### run_pilot_command() dispatch 로직 (line 166-181)
```python
def run_pilot_command(task_type: str, task_id: str) -> tuple[int, str, str]:
    if task_type == "pilot_echo":
        cmd = ["/bin/echo", f"PILOT_OK {now()}"]
    elif task_type == "corpus_pilot_echo":
        cmd = ["python3", str(CORPUS_PILOT_DRIVER), "--task-id", task_id]
    else:
        raise RuntimeError(f"run_pilot_command: no dispatch defined for task_type={task_type!r}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.returncode, result.stdout, result.stderr
```

### 코드 경로 분석
1. `task_type`으로만 분기 — task 데이터의 다른 필드가 명령어 구성에 영향 없음
2. `corpus_pilot_echo`일 때 고정된 `CORPUS_PILOT_DRIVER` 경로 + `--task-id` 인자만 전달
3. `task_id`가 `--task-id` argparse 인자로 전달되므로 shell injection 불가
4. `check_isolation_contract()`가 `(task_type, namespace)`를 먼저 검증하므로, 허용된 task_type 외에는 이 함수에 도달할 수 없음

### ✅ CLI-driver boundary: 통과
subprocess 우회 경로 없음. corpus_pilot_driver.py는 minimal import만 사용.

---

## 검증 3: authorized_by_task_order 검증

### CUE의 주장
> 이 필드가 비어있거나 없으면 게이트웨이가 `VALIDATION_FAILED`로 거부한다.

### 실제 테스트 결과

#### n8n Gateway ("Code — Schema Validation" node, phase-e.json)
```javascript
const required = [
  'schema_version','task_id','title','owner','state','phase',
  'requires_human_approval','production_mutation','evidence','audit'
];
// authorized_by_task_order는 REQUIRED 필드에 없음!
```

**테스트 결과 (모두 valid=True):**
| 값 | n8n Gateway 판정 |
|---|---|
| `'CORPUS-FACTORY-INTEGRATION-PILOT-001'` (유효값) | ✅ valid=True |
| `''` (빈 문자열) | ✅ valid=True ← **뚬림** |
| `'   '` (공백) | ✅ valid=True ← **뚬림** |
| `null` | ✅ valid=True ← **뚬림** |
| `0` (숫자) | ✅ valid=True ← **뚬림** |
| 필드 자체 없음 | ✅ valid=True ← **뚬림** |

#### Python task_contract.py (`validate_task_schema`)
```python
REQUIRED_FIELDS_BY_PHASE["PILOT"] = [
    "schema_version", "task_id", "title", "owner", "state",
    "phase", "task_type", "scope", "authorized_by",  # authorized_by만 있음!
    "production_mutation", "constraints", "automation",
]
# authorized_by_task_order는 REQUIRED 필드에 없음!
```

#### pilot_executor.py
```bash
$ grep -n "authorized_by_task_order" .automation/night-shift/pilot_executor.py
(결과 없음 — 전혀 읽지 않음)
```

### ❌ authorized_by_task_order 검증: **실패** (실제 결함)

**발견:**
1. n8n gateway의 schema validation에서 `authorized_by_task_order`를 REQUIRED 필드로 포함하지 않음
2. Python `task_contract.py`에서도 `authorized_by_task_order`를 검증하지 않음 (`authorized_by`만 있음)
3. `pilot_executor.py`에서 이 필드를 전혀 읽지 않음
4. **CUE의 주장 "이 필드가 비어있거나 없으면 게이트웨이가 VALIDATION_FAILED로 거부한다"는 거짓**

**결함 심각도:** HIGH — authorization 필드가 실제로 검증되지 않으므로, 어떤 값(또는 없음)으로도 task가 VALIDATION_PASSED를 통과할 수 있음.

---

## 종합 판정

| 항목 | 논리 검증 | 파일시스템/실제 검증 | 판정 |
|---|---|---|---|
| 1. Namespace 격리 | ✅ 통과 | ⚠️ heartbeat/evidence 섞임 | **NOT VERIFIED** |
| 2. CLI-driver boundary | ✅ 통과 | ✅ 통과 | **PASS** |
| 3. authorized_by_task_order | ❌ 주장 거짓 | ❌ 전혀 검증 안 됨 | **FAIL (실제 결함)** |

### Gate: NOT VERIFIED

**이유:**
1. 검증 1: 논리적 격리는 통과하지만 파일시스템에서 namespace가 분리되지 않음 — "namespace 분리" 주장을 약화
2. 검증 3: CUE의 주장과 달리 `authorized_by_task_order`가 gateway/executor 모두에서 전혀 검증되지 않음 — **실제 보안 결함**

---

## 발견된 결함 목록

### 결함 1 (HIGH): authorized_by_task_order 무검증
- **위치:** n8n workflow phase-e.json ("Code — Schema Validation" node), task_contract.py, pilot_executor.py
- **현상:** `authorized_by_task_order` 필드가 빈 문자열, 공백, null, 숫자, 누락 모두 VALIDATION_PASSED 통과
- **영향:** authorization 필드가 실제로 기능하지 않음
- **근거:** phase-e.json line 3-8 (required list에 없음), task_contract.py line 51-62 (REQUIRED_FIELDS_BY_PHASE에 없음), pilot_executor.py grep 결과 없음

### 결함 2 (MEDIUM): Namespace heartbeat/evidence 파일시스템 미분리
- **위치:** pilot_executor.py line 46-47
- **현상:** `PILOT_EVIDENCE_DIR`와 `HEARTBEAT_DIR`가 namespace별로 동적으로 분리되지 않고 고정 경로에 저장
- **영향:** corpus-factory-pilot와 control-plane-pilot의 heartbeat/evidence가 같은 디렉터리에 섞여 저장됨
- **근거:** 실제 파일 시스템 확인 — `.automation/night-shift/heartbeats/`에 두 namespace heartbeat가 공존, `.automation/evidence/night-shift/control-plane-pilot/`에 두 namespace evidence가 공존

---

## 완료 후

C1은 CUE gate를 스스로 PASS로 선언하지 않는다. 발견 사항을 그대로 제출하고 STOP한다.

**STOP**
