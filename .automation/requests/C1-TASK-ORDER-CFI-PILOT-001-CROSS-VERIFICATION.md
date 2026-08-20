# C1 Task Order — CORPUS-FACTORY-INTEGRATION-PILOT-001 독립 교차검증

**Task Order:** C1-TASK-ORDER-CFI-PILOT-001-CROSS-VERIFICATION
**Date:** 2026-08-17
**발주자:** CUE (Independent Verification 요청) / Rev. Bang (승인)
**대상:** C1
**근거 문서:** `.automation/audit/CORPUS-FACTORY-INTEGRATION-PILOT-001-CUE-SELF-REVIEW.json`(CUE 자기감사, CONDITIONAL PASS), `docs/architecture/ADR-026-Control-Plane-Corpus-Factory-Integration-Design.md`

---

## 이 task의 성격 — 구현이 아니다

이번 CORPUS-FACTORY-INTEGRATION-PILOT-001은 CUE가 발행·구현·실행·판정을 전부 혼자 했다. C1 Build → CUE Independent Audit이라는 평소의 독립성이 성립하지 않는다. 그래서 이번엔 반대로 간다: **C1이 CUE의 결과물을 의심하고 깨보는 역할**이다.

새 기능을 만들지 마라. 이미 증명된 14개 계약 항목(canonical signature propagation, evidence integrity, heartbeat/crash recovery, dependency handling, duplicate/conflict 등)은 손대지도, 재시험하지도 마라 — 딱 아래 3가지만 확인한다.

## 검증 대상 3가지

### 1. `corpus-factory-pilot` namespace가 실제로 완전히 격리되어 있는가

CUE의 주장: `.automation/night-shift/pilot_executor.py`의 `ALLOWED_COMBINATIONS`와 `TASK_ID_PREFIX_NAMESPACE`가 `(task_type, namespace)` 조합과 `task_id` prefix를 둘 다 강제해서, `corpus-factory-pilot` task가 `control-plane-pilot` 리소스에 접근하거나 그 반대가 불가능하다.

**깨보려고 시도할 것**:
- `task_id`는 `CONTROL-PLANE-PILOT-`로 시작하지만 `scope.namespace`는 `corpus-factory-pilot`인 task를 만들어서 게이트웨이/executor 양쪽에 제출 — 거부되는지, 거부된다면 정확히 어느 단계에서 거부되는지 raw response로 확인.
- 반대 조합도 동일하게 시도.
- `corpus-factory-pilot` task의 `evidence`/`heartbeat` 파일이 `control-plane-pilot` task의 파일과 실제로 분리 저장되는지(경로 확인) — 같은 디렉터리에 섞여 있다면 "namespace 분리"라는 주장 자체가 파일시스템 레벨에서는 약하다는 뜻이므로 그대로 지적해라.

### 2. CLI-driver boundary가 production executor로 우회될 수 없는가

CUE의 주장: `corpus_pilot_echo` task_type은 항상 `subprocess.run([...])`으로 `.automation/control-plane/fixtures/corpus_pilot_driver.py`를 호출하며, executor 코드 안에 그 로직이 인라인되어 있지 않다.

**깨보려고 시도할 것**:
- `pilot_executor.py`와 `corpus_pilot_driver.py`에 `NAE.`, `core.retrieval`, `cli_driver`, `import` 관련 문자열을 전부 grep해서 실제 import 문인지 주석인지 한 줄씩 직접 읽고 확인해라(grep 건수만 세지 마라 — CUE도 이 방법으로 확인했다, 같은 방법으로 재현해라).
- `task.processing_input`이나 다른 필드를 조작해서 `corpus_pilot_driver.py`가 아닌 다른 명령이 실행되게 만들 수 있는 경로가 있는지 코드를 읽고 찾아봐라(`run_pilot_command()`의 dispatch 로직이 task_type 문자열 하나로만 분기하는지, 혹시 task 데이터의 다른 필드가 명령어 구성에 영향을 주는지).

### 3. `authorized_by_task_order`가 실제 authorization 없이 task를 통과시키지 않는가

CUE의 주장: 이 필드가 비어있거나 없으면 게이트웨이가 `VALIDATION_FAILED`로 거부한다.

**깨보려고 시도할 것**:
- 필드를 빈 문자열(`""`), 공백(`"   "`), `null`, 숫자(`0`) 등 "존재하지만 무의미한" 값으로 채운 task를 제출해서 전부 거부되는지 확인(CUE는 필드 부재만 테스트했다 — 존재하되 무의미한 값은 테스트하지 않았을 수 있다).
- 이 필드 값이 실제로 존재하는 Task Order를 가리키는지까지는 검증되지 않는다는 점(CUE의 설계 자체가 "문자열이 비어있지 않은지"만 검사하지, 그 문자열이 진짜 유효한 Task Order ID인지는 검증하지 않음)을 확인하고, 이게 알려진 한계인지 숨겨진 결함인지 판단해라.

## 절대 금지 (변경 없음)

`core/retrieval.py`, `data/제련완성본/`, NAE production corpus, Fuller Vol.02-08, Approved workflow 직접 수정, 자동 retry/promotion/approval. 이 task는 검증만 한다 — 발견한 문제를 스스로 고치려 하지 마라, 발견해서 보고만 해라(고치는 건 다음 task).

## 산출물

각 항목(1/2/3)에 대해:
- 실제로 시도한 명령/코드와 raw 응답
- 깨는 데 성공했는가(진짜 결함) / 실패했는가(주장이 맞음)
- 성공했다면 정확히 어떤 조건에서 뚫리는지

## 완료 후

**C1은 CUE gate를 스스로 PASS로 선언하지 않는다.** 발견 사항을 그대로 제출하고 STOP해라. CUE가 이 결과를 다시 독립적으로 확인한 뒤에만 Integration Authorization 여부를 판단한다.
