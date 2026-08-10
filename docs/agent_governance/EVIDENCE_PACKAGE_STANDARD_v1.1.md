# DBMA Evidence Package Standard v1.1

**Status:** APPROVED
**Authority:** HQ
**Effective date:** 2026-08-01
**Applies to:** C1 evidence submission; CUE evidence and repository assurance
**Supersedes:** Informal or task-specific Evidence Package conventions
**Normative language:** MUST, MUST NOT, REQUIRED, SHALL

## Status and Authority

This document is the normative standard for every C1 Evidence Package
submitted to CUE in DBMA/NAE work.

A task-specific directive may add stricter requirements, but it MUST NOT
weaken, override, or omit any requirement of this standard. Where a
task-specific directive conflicts with this standard, this standard governs
unless HQ explicitly records a versioned exception.

## Roles and Status Authority

### Roles

**HQ**  — final authority for priority, canonical admission, ADR adoption, release,
public disclosure, destructive actions, and other irreversible decisions.

**CUE** — Principal Quality, Evidence & Repository Assurance Authority; owns
pre-push evidence review and post-push GitHub repository assurance.

**C1**  — Local Implementation Engineer; implements, tests, and produces raw,
reproducible Evidence Packages.

No separate P1 role exists.

### Standard States

| 상태 | 정의 | 승격 조건 |
|---|---|---|
| `NOT_STARTED` | 작업이 아직 시작되지 않음 | HQ 지시 또는 C1 작업 시작 시 |
| `WORKING` | C1이 작업 중, 증거 미생성 | C1이 구현/수정 시작 시 |
| `EVIDENCE_GENERATED` | 증거 payload 생성 완료, manifest 작성 완료 | 모든 필수 파일 생성 시 |
| `LOCAL_SEALED` | seal.json 생성 및 두 번째 Git 커밋 완료 | E→S 봉인 체인 검증 통과 시 |
| `EVIDENCE_SUBMITTED` | CUE에 제출 대기 중 | LOCAL_SEALED + CUE 제출 기록 |
| `CUE-CLEARED` | CUE가 증거 충분성·불일치·범위 일치 판정 | Section 11 조건 모두 충족 |
| `BLOCKED` | CUE가 불일치·결손·규칙 위반 발견 | Section 12 자동 BLOCKED 사유 또는 CUE 수동 판정 |
| `REWORK_REQUIRED` | CUE가 특정 결함 수정 요청 | CUE가 구체적 결함 항목 명시 |
| `PUSHED_PENDING_CUE_REPOSITORY_CHECK` | push 완료, GitHub 반영 CUE 검증 대기 | push-record.json 존재 + S 커밋 원격 확인 |
| `CUE-GITHUB-VERIFIED` | 원격 E/S 커밋·seal·manifest 모두 검증 통과 | Section 7 검사 모두 통과 + 원격 확인 |
| `HQ_APPROVED` | HQ가 최종 승인 (Risk D 또는 비가역적 결정만) | CUE-GITHUB-VERIFIED + HQ 지시 |
| `COMPLETE` | HQ_APPROVED 또는 해당 상태의 최종 목표 달성 | 모든 게이트 통과 |

## 0. Purpose

C1은 구현, 테스트, 증거 생산만 담당한다. CUE는 증거 충분성, 계약 준수,
provenance, GitHub 반영 일치 여부를 판정한다. 이 표준은 CUE가 서술이 아니라
해시·원시 로그·Git 객체로 판정할 수 있도록 하는 단일 Evidence Package 형식을
정의한다.

## 1. 운영 원칙

- 하나의 작업 지시에는 하나의 Evidence Package만 제출한다.
- 사람이 읽는 요약(README)은 보조 자료이며, 원시 산출물과 충돌하면 원시
  산출물이 우선한다.
- Evidence Package가 없으면 C1의 상태는 언제나 `REPORTED`이며, `COMPLETE`,
  `VERIFIED`, `READY` 같은 승격 표현을 사용할 수 없다.
- C1은 파일·로그·해시를 사후 편집하지 않는다. 수정이 필요하면 새 패키지
  버전 또는 remediation 패키지를 생성한다.

## 2. 표준 디렉터리 구조

```text
evidence/<TASK-ID>/<PACKAGE-ID>/
├── README.md
├── manifest.json
├── seal.json
├── scope.json
├── environment.json
├── commands/
├── tests/
├── validation/
├── artifacts/
├── provenance/
├── diff/
├── repository/
└── exceptions/
```

`PACKAGE-ID` 예시: `NAE-EVIDENCE-RECONCILIATION-011-20260801T163400Z`

## 3. README ↔ manifest 순환 참조 금지

- `manifest.json`은 payload 파일(README, scope, 로그, 테스트 결과, validation
  출력, CSV, provenance, diff, 예외 문서 등)의 SHA256을 기록한다.
- `manifest.json`과 `seal.json`은 manifest 대상에서 **제외**한다 (자기참조 및
  순환 방지).
- `README.md`는 해시값을 직접 쓰지 않고 경로만 참조한다:

```md
## Integrity References
- Payload manifest: `manifest.json`
- Package seal: `seal.json`
- Integrity status: verify `seal.json` against the Git commit and `manifest.json`
```

## 4. Risk Tier 정의

| 등급 | 기준 | 예시 | 게이트 |
|---|---|---|---|
| A — Low | 되돌리기 쉬움, 계약/데이터 의미 영향 없음 | 오탈자, 문서 링크 수정 | 선택적 |
| B — Controlled | 코드/테스트 변경, 기존 계약·아키텍처 유지 | 단위 테스트 추가, 내부 리팩터링 | 필요시 제한 검토 |
| C — High | 평가 계약, retrieval, schema, registry, corpus, provenance, ID-space 영향 | benchmark metric 수정, Gold validator 변경 | **CUE 사전 게이트 필수** |
| D — Critical | 비가역적 변경 또는 신뢰 경계 영향 | canonical admission, corpus 삭제/대량 ingest, Qdrant 재색인, release | **CUE 검토 + HQ 최종 승인 필수** |

`scope.json`은 등급 판정 근거(`risk_rationale`)를 반드시 포함한다. 등급이
애매하면 C1은 `RISK UNRESOLVED`로 제출하고 CUE가 등급을 판정한다.

## 5. 패키지 봉인(Seal) 절차 — 불변성 확보

```text
1. C1이 증거 payload를 생성한다.
2. 고정 스크립트(scripts/evidence/build_manifest.py)로 manifest.json을 생성한다.
3. payload 전체(README, manifest.json 포함)를 첫 번째 Git 커밋으로 기록한다.
   └─ Payload Commit (E)
4. E의 commit SHA / tree SHA(git write-tree)를 확인한다.
5. build_seal.py로 seal.json을 생성한다 (payload_commit_sha, payload_tree_sha,
   manifest_sha256 포함).
6. seal.json만 포함한 두 번째 Git 커밋을 생성한다.
   └─ Seal Commit (S), S의 직접 부모는 반드시 E.
7. CUE 지시 전에는 payload 파일을 수정하지 않는다.
```

### 불변성 규칙

- payload 파일 수정이 필요하면 새 패키지 ID, 새 payload commit, 재생성된
  manifest, 새 seal commit이 필요하다.
- 봉인된 패키지의 amend/rebase/force-push/덮어쓰기/무음 교체는 금지한다.
- CUE는 Git 객체, manifest.json, 실제 payload 파일 간 불일치를 발견하면
  즉시 `BLOCKED`를 부여한다.
- push 전에는 `LOCAL SEALED — NOT REPOSITORY VERIFIED`까지만 부여 가능하며,
  원격 브랜치에서 동일 E/S 커밋이 확인되어야 `CUE-GITHUB-VERIFIED`가 된다.

## 6. Manifest 생성기 고정

```text
scripts/evidence/
├── build_manifest.py
├── verify_manifest.py
├── build_seal.py
└── verify_package.py
```

`environment.json`에 도구 버전/해시를 기록한다:

```json
{
  "evidence_tooling": {
    "manifest_builder_path": "scripts/evidence/build_manifest.py",
    "manifest_builder_git_blob_sha": "<git-blob-sha>",
    "manifest_builder_sha256": "<sha256>",
    "manifest_schema_version": "1.1",
    "package_verifier_path": "scripts/evidence/verify_package.py",
    "package_verifier_git_blob_sha": "<git-blob-sha>"
  }
}
```

`commands/executed-commands.txt`에 생성/검증/봉인 명령의 원문 실행 로그를
남긴다 (build_manifest → verify_manifest → git rev-parse/write-tree →
build_seal).

## 7. `verify_package.py` 필수 검사 항목

1. Payload commit(E)이 존재하는가
2. Seal commit(S)이 존재하는가
3. **S의 직접 부모가 E인가** (중간 커밋 오염 방지)
4. `git diff --name-status <E> <S>`의 변경이 정확히 한 줄인가:
   `A\t<PACKAGE_ROOT>/seal.json`
   (M/D/R/C 또는 다른 파일의 A는 모두 `BLOCKED`)
5. S 커밋에서 seal.json이 새로 추가(A)되었는가
6. `seal.json.payload_commit_sha` == E
7. `seal.json.payload_tree_sha` == E의 tree SHA
8. `seal.json.manifest_sha256` == E 안 manifest.json의 실제 SHA256
9. **Manifest payload 완전성/무결성 (양방향)**:
   - (a) E 안의 `<PACKAGE_ROOT>` 하위 모든 물리 파일(`manifest.json`,
     `seal.json` 제외)이 `manifest.json`에 정확히 한 번씩 등재됨
   - (b) `manifest.json`의 모든 항목이 E에 물리적으로 존재하고, 선언된
     크기·SHA256과 일치함
   - (c) 중복 경로, 중복 artifact identity, 경로 탐색(`..`), 절대경로,
     package root를 벗어나는 symlink, 미신고 제외 파일 금지
10. `seal.json`과 `manifest.json`이 선언한 package_id / package root 일치

검사 실패 시 표준 출력:

```text
BLOCKED — INVALID SEAL COMMIT SCOPE
BLOCKED — MANIFEST PAYLOAD SET MISMATCH
```

## 8. 필수 파일 요약

| 파일 | 필수 | 역할 |
|---|---:|---|
| README.md | 예 | C1 제출 요약 (해시 값 미기재, 경로만 참조) |
| manifest.json | 예 | payload 파일 SHA256/크기/역할 기준 목록 |
| seal.json | 예 | payload commit/tree/manifest 해시 봉인 |
| scope.json | 예 | 지시서, 허용/금지 범위, risk tier, 완료 조건 |
| environment.json | 예 | OS, Python, venv, Git HEAD, 도구 버전 |
| commands/executed-commands.txt | 예 | 실행 명령·종료코드 원문 (편집 금지, 실패 포함) |
| diff/git-status.txt, changed-files.txt | 예 | 작업 트리 상태, 변경 파일 목록 |
| diff/git-diff.patch | 조건부 | 코드/문서/설정 변경 시 |
| tests/pytest-*.txt | 조건부 | pytest 실행 시 (collection + output 모두) |
| validation/* | 예 | validator/checker/integrity 검증 출력 |
| artifacts/artifact-inventory.csv | 조건부 | corpus/quarantine/원본/생성 파일 다룰 때 |
| provenance/* | 조건부 | source/corpus/metadata/hash/canonical 작업 |
| repository/push-record.json | push 후 필수 | commit SHA, branch, remote, push 시각 |
| exceptions/unresolved-items.md | 예 | 없으면 `None` 명시, 숨김 금지 |

## 9. C1 Evidence Declaration (필수, 패키지 말미)

```md
## C1 Evidence Declaration
I submit this package as evidence of the specifically stated work only.
I do not claim:
- canonical admission,
- GitHub verification,
- production readiness,
- retrieval validity,
- benchmark validity,
- source identity verification,
- or HQ approval
unless those claims are explicitly supported by the referenced evidence and
authorized by the responsible gate authority.
Any item not evidenced in this package is `NOT VERIFIED`.
Any unresolved contradiction is listed in `exceptions/unresolved-items.md`.
```

## 10. 상태 흐름

```text
C1 WORKING → EVIDENCE GENERATED → LOCAL SEALED → EVIDENCE SUBMITTED
  → CUE-CLEARED / BLOCKED / REWORK REQUIRED
  → PUSHED — PENDING CUE REPOSITORY CHECK → CUE-GITHUB-VERIFIED
  → HQ APPROVED (Risk D 또는 비가역적 결정만)
```

## 11. CUE-CLEARED 최종 인증 조건 (모두 충족 필요)

1. Risk tier, 범위, 허용/금지 작업이 선언되고 실제 변경과 일치
2. Payload commit(E)·seal commit(S) 존재, S의 직접 부모가 E
3. E→S 변경이 해당 패키지 `seal.json` 추가 한 건뿐
4. 실제 payload 파일 집합과 manifest 선언 집합이 완전 양방향 일치
5. 모든 declared 파일의 경로·크기·SHA256이 E 커밋 내용과 일치
6. `seal.json`의 payload commit/tree/manifest SHA256이 실제 Git 객체와 일치
7. manifest 생성기/검증기의 저장소 경로·버전·실행 로그 보존
8. unresolved exception, quarantine 상태, canonical admission 상태가 과장 없이 기록

## 12. 자동 BLOCKED 사유

- manifest SHA256과 실제 재계산 값 불일치
- inventory에 없는 실제 artifact 발견 / manifest에 없는 물리 파일 존재
- provenance 없는 원시/파생 파일
- 테스트 요약과 원문 로그의 수치 불일치
- `INVALID_GOLD` 또는 존재하지 않는 TSU ID를 유효 Gold로 서술
- quarantine 파일을 canonical 자료처럼 표현
- 지시 범위를 벗어난 코드·데이터·registry·Qdrant 변경
- unresolved 문제가 있으나 `VERIFIED`/`COMPLETE`/`READY`로 과장
- seal commit이 seal.json 외 파일을 변경 (INVALID SEAL COMMIT SCOPE)
- manifest 생성 도구 경로/버전/실행 로그 부재

## 변경 이력

- v1.1 (2026-08-01, HQ 승인): README-manifest 순환 참조 제거(seal.json 분리),
  Risk tier 정의, payload/seal commit 봉인 체인, manifest 생성기 고정,
  seal commit 범위 기계 검증, manifest 양방향 완전성 검사 추가.
