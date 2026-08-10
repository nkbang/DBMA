# C1 Task Order 038 — Evidence Package 도구 구현 (`scripts/evidence/`)

**상태**: 승인됨 — 즉시 착수 가능
**우선순위**: P1 (Evidence Package Standard v1.1이 문서로만 존재하고 실행 가능한 검증 도구가 없음 — 표준 자체가 "manifest는 수동 입력 금지, 생성 스크립트로 작성"을 요구하므로 도구가 없으면 표준을 지킬 방법이 없음)
**대상 파일 (신규)**: `scripts/evidence/build_manifest.py`, `scripts/evidence/verify_manifest.py`, `scripts/evidence/build_seal.py`, `scripts/evidence/verify_package.py`, `tests/test_evidence_tools.py`
**참고 파일 (읽기 전용, 규격 원본)**: `docs/agent_governance/EVIDENCE_PACKAGE_STANDARD_v1.1.md`
**모드 제약**: 이번 작업은 **도구 구현만** 한다. 실제 Evidence Package를 만들어 제출하는 것은 다음 Task Order(039, dogfooding 검증용)에서 별도로 진행한다.

---

## 1. 배경

`docs/agent_governance/EVIDENCE_PACKAGE_STANDARD_v1.1.md`가 HQ 승인으로 확정되었다. 이 표준은 C1이 CUE에 제출하는 모든 Evidence Package가 `manifest.json`/`seal.json`을 통해 Git 커밋 두 개(payload commit E, seal commit S)로 봉인되도록 요구하지만, 그 봉인·검증을 수행하는 스크립트는 아직 존재하지 않는다. 이 Task Order는 표준 §6(Manifest 생성기 고정)과 §7(`verify_package.py` 필수 검사 항목)을 그대로 구현한다.

## 2. 작업 범위

### TASK 1 — `build_manifest.py`

```
python -m scripts.evidence.build_manifest --package evidence/<TASK-ID>/<PACKAGE-ID>
```

- `<PACKAGE_ROOT>` 하위 모든 파일을 재귀 탐색한다. **제외 대상**: `manifest.json`, `seal.json`, `.DS_Store`(제외 사유와 함께 `excluded_paths`에 기록).
- 각 파일의 SHA256(64자 소문자 hex), 크기(bytes), media type(확장자 기반 추정으로 충분: `.md`→`text/markdown`, `.json`→`application/json`, `.txt`/`.csv`/기타→`text/plain`)을 계산한다.
- 표준 §"manifest.json 규격"의 스키마 그대로 출력한다 (`schema_version`, `package_id`, `generated_at_utc`, `hash_algorithm`, `files[]`, `excluded_paths[]`).
- `package_id`는 `--package` 인자의 마지막 경로 세그먼트를 기본값으로 쓰되 `--package-id`로 override 가능하게 한다.
- 동일 SHA256이 서로 다른 두 개 이상의 파일 경로에 나타나면 stderr에 경고를 출력한다(차단하지는 않음 — 표준상 "예외 사유 기록"은 사람이 판단할 몫).

### TASK 2 — `verify_manifest.py`

```
python -m scripts.evidence.verify_manifest --package evidence/<TASK-ID>/<PACKAGE-ID>
```

- `manifest.json`을 읽고, 그 안의 모든 `files[].path`가 실제로 존재하며 size/sha256이 일치하는지 확인한다 (표준 §7 항목 9-b).
- `<PACKAGE_ROOT>` 하위 실제 파일 중 `manifest.json`/`seal.json`/`excluded_paths`에 없는데 manifest에도 없는 파일이 있으면 실패로 보고한다 (표준 §7 항목 9-a, 양방향 검사).
- 종료 코드: 전부 일치하면 0, 하나라도 불일치하면 1이고 stdout에 사람이 읽을 수 있는 불일치 목록을 출력한다 (표준의 `BLOCKED — MANIFEST PAYLOAD SET MISMATCH` 형식 참고).

### TASK 3 — `build_seal.py`

```
python -m scripts.evidence.build_seal --package evidence/<TASK-ID>/<PACKAGE-ID> \
  --payload-commit <SHA> --payload-tree <SHA>
```

- `manifest.json`의 SHA256을 계산하고, 표준 §"seal.json 규격"에 맞춰 `seal.json`을 생성한다.
- `--payload-commit`/`--payload-tree`는 호출자(사람 또는 상위 셸 스크립트)가 `git rev-parse HEAD`/`git write-tree` 결과를 넘겨준다 — 이 스크립트 자체가 커밋을 만들지 않는다 (git 커밋 생성은 사람/CI가 표준 §5 절차에 따라 별도로 수행).
- `sealed_at_utc`는 실행 시각(UTC, ISO-8601)으로 채운다. `seal_commit_sha`는 아직 S 커밋이 생성되기 전이므로 `null`로 둔다.

### TASK 4 — `verify_package.py`

```
python -m scripts.evidence.verify_package --package evidence/<TASK-ID>/<PACKAGE-ID> \
  --payload-commit <E-SHA> --seal-commit <S-SHA>
```

표준 §7의 10개 항목을 **순서대로, 실패해도 계속 진행하며 전체 결과를 모아서** 검사한다 (하나 실패해도 나머지 항목도 다 보고해야 사람이 한 번에 고칠 수 있다):

1. E 커밋 존재 (`git cat-file -e <E>`)
2. S 커밋 존재
3. S의 직접 부모가 E인가 (`git rev-parse <S>^` == E)
4. `git diff --name-status <E> <S>`가 정확히 한 줄, `A\t<PACKAGE_ROOT>/seal.json`인가
5. (4와 동일 검사에 포함되므로 4의 상태 문자가 `A`인지로 확인)
6. `seal.json.payload_commit_sha == E`
7. `seal.json.payload_tree_sha == git rev-parse <E>^{tree}`
8. `seal.json.manifest_sha256` == E 커밋 시점 `manifest.json`의 실제 SHA256 (`git show <E>:<path>/manifest.json | sha256`)
9. manifest 양방향 완전성 (`verify_manifest.py`의 로직을 재사용하되, **워킹 디렉터리가 아니라 E 커밋 시점의 tree**를 대상으로 검사 — `git ls-tree -r <E> -- <PACKAGE_ROOT>` 사용)
10. `seal.json`/`manifest.json`의 package_id 및 package root 문자열 일치

**중요**: 항목 9는 워킹 디렉터리 파일이 아니라 `git show`/`git ls-tree`로 E 커밋 내부 상태를 직접 읽어야 한다. 워킹 디렉터리 검사(TASK 2)와 커밋 검사(TASK 4)를 혼동하면 "커밋 후 워킹 디렉터리만 몰래 고친 것"을 못 잡는다 — 이게 이 도구의 존재 이유다.

출력 형식은 표준의 "상태 및 보고 문구" 절 그대로:
- 성공: `PACKAGE SEAL VERIFIED` 블록
- 실패: `BLOCKED — INVALID SEAL COMMIT SCOPE` 또는 `BLOCKED — MANIFEST PAYLOAD SET MISMATCH` (실패한 항목 번호와 사유 나열)

종료 코드: 10개 항목 모두 통과 시 0, 하나라도 실패 시 1.

### TASK 5 — 테스트

`tests/test_evidence_tools.py`에서 임시 디렉터리(`tmp_path`)와 임시 git repo(`git init`)를 이용해:
- `build_manifest.py`가 알려진 파일 집합에 대해 올바른 해시/크기를 생성하는지
- `verify_manifest.py`가 (a) 정상 케이스 통과 (b) 파일 누락 (c) 해시 불일치 (d) manifest에 없는 미신고 파일 세 가지 실패 케이스를 각각 잡아내는지
- `build_seal.py`가 올바른 seal.json을 생성하는지
- `verify_package.py`가 (a) 정상 봉인 체인 통과 (b) S가 E의 직접 부모가 아닌 경우 (c) S 커밋에 seal.json 외 파일이 섞인 경우 (d) seal.json의 payload_commit_sha가 실제 E와 다른 경우 를 각각 `BLOCKED`로 잡아내는지

최소 하나의 end-to-end 테스트(더미 payload 생성 → manifest → 커밋(E) → seal → 커밋(S) → verify_package 통과)를 포함한다.

## 3. 완료 보고 형식

```
STATUS: PASS / BLOCKED

TASK 1 — build_manifest.py:
(실행 예시와 출력 manifest.json 샘플)

TASK 2 — verify_manifest.py:
(정상/실패 케이스 각각의 실행 예시와 출력)

TASK 3 — build_seal.py:
(실행 예시와 출력 seal.json 샘플)

TASK 4 — verify_package.py:
(정상 봉인 체인 e2e 실행 로그, 그리고 4가지 실패 케이스 각각의 BLOCKED 출력)

TEST RESULTS:
(pytest tests/test_evidence_tools.py 전체 결과 - collection 수, pass/fail 수)

KNOWN ISSUES:
(있다면)
```

이 보고서 자체는 Evidence Package Standard v1.1 §4 기준 **Risk Tier B**(신규 코드/테스트, 기존 계약·아키텍처 영향 없음)이며, 도구가 아직 존재하지 않는 시점의 작업이므로 이번 완료 보고는 Evidence Package 없이 `REPORTED` 상태로 제출한다. 다음 Task Order(039)에서 이 도구들을 실제로 사용해 첫 dogfooding Evidence Package를 만들고 CUE가 검토한다.

## 4. 금지 사항

- `NAE/` 하위 파일 수정 금지 — 이번 작업은 `scripts/evidence/`와 신규 테스트 파일에 한정
- `docs/agent_governance/EVIDENCE_PACKAGE_STANDARD_v1.1.md` 내용 수정 금지 (구현이 규격을 따라야지, 규격을 구현에 맞춰 바꾸면 안 됨 — 불일치를 발견하면 코드를 짜지 말고 CUE에 먼저 보고)
- 실제 `evidence/` 디렉터리에 진짜 태스크용 패키지 생성 금지 (테스트는 `tmp_path`에서만)
- git commit 금지 (CUE 검토 후 별도 승인)
- 완료 보고에서 "완료", "검증됨", "준비됨" 같은 승격 표현 사용 금지 — Evidence Package Standard v1.1 §1에 따라 이 작업의 상태는 `REPORTED`로 고정

---

## C1 전달용 지시 문구 (복사해서 그대로 전달)

```
C1, 다음 작업을 진행해줘.

작업명령서: docs/agents/c1/C1-TASK-ORDER-038.md

docs/agent_governance/EVIDENCE_PACKAGE_STANDARD_v1.1.md §5~§7을 그대로
구현하는 4개 스크립트(build_manifest.py, verify_manifest.py, build_seal.py,
verify_package.py)를 scripts/evidence/에 만들어줘.

가장 중요한 부분은 verify_package.py의 항목 9야 - manifest 완전성 검사를
워킹 디렉터리가 아니라 반드시 E 커밋 시점의 git tree(git show/git ls-tree)를
대상으로 해야 해. 워킹 디렉터리를 검사하면 "커밋한 뒤 파일만 몰래 고치는"
공격을 못 잡아 - 이게 이 도구를 만드는 이유다.

verify_package.py의 seal commit 범위 검사(항목 4)는 git diff --name-status로
E와 S 사이 변경이 정확히 seal.json 추가 한 줄인지 확인해야 하고, M/D/R/C나
다른 파일의 A는 전부 BLOCKED여야 해.

테스트는 tmp_path에 임시 git repo를 만들어서 진짜 커밋 두 개(E, S)를 찍어보고
검증하는 end-to-end 케이스를 최소 1개 포함해줘. 실패 케이스 4가지
(S가 E의 자식이 아님 / seal commit에 다른 파일 섞임 / payload_commit_sha 불일치 /
manifest-파일 불일치)도 각각 테스트로 만들어줘.

NAE/ 하위는 건드리지 말고, 표준 문서 내용도 수정하지 마 - 표준과 코드가
안 맞으면 네가 표준을 고치지 말고 먼저 보고해.

완료되면 문서에 명시된 "완료 보고 형식"으로 보고해. 이 작업은 Evidence
Package 없이 REPORTED 상태로 제출하는 거니까 "완료"라는 표현은 쓰지 마.
git commit도 하지 마.
```
