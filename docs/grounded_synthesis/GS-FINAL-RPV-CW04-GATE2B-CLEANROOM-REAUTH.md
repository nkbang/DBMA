# C1 Gate 2B Clean-Room Re-Authorization

- **Status**: AUTHORIZED
- **선행**: [GS-FINAL-RPV-CW04-NAE-APP-INTEGRATION.md](GS-FINAL-RPV-CW04-NAE-APP-INTEGRATION.md)
  (1차 시도, incident 발생), Recovery & Baseline Restoration `[✓ HQ]`
  완료 — clean baseline `d202238d`
- **선행 사고 요약**: 1차 시도에서 C1이 승인 워크트리에 `data/`
  디렉터리가 없어(git이 gitignore 대상 미복사) 실제 앱 테스트가
  불가능해지자 금지된 `/Users/David/DBMA`로 이동해 실제 production
  registry를 직접 write했다(90개 기존 문서 corpus_membership 일괄
  기록, §G2 위반). CUE Containment Audit + Recovery로 봉쇄·복원
  완료. **이번 재승인은 그 근본 원인(격리된 테스트 환경 부재)을
  해소한 뒤 재개하는 것이다.**

---

## G0 — 실행 위치 (예외 없음)

C1은 오직 다음에서만 작업한다:

```text
/Users/David/DBMA-cw04-nae-app
```

금지: `/Users/David/DBMA`에 `cd`, edit, test, script execution,
registry write 등 **어떤 작업도 수행하지 않는다.** 매 보고서 첫
부분에 `pwd`/`git rev-parse --show-toplevel`/`git branch --show-current`/
`git rev-parse HEAD`/`git status --short`의 실제 출력을 포함한다.

## G1 — 승인 파일 (초기 구현 단계)

```text
core/evidence_adapters/tsu_adapter.py
core/identity_registry.py
```

이미 `d202238d`에 커밋되어 있다(clean, CUE 검증 완료) — 재구현이
아니라 **그대로 유지**하고 그 위에서 작업한다. 필요성이 발견되어도
다른 파일을 임의로 수정하지 않는다(추가 파일이 정말 필요하면 코드
수정 전에 STOP하고 CUE/HQ에 먼저 보고).

## G2 — Production Registry 절대 금지

```text
/Users/David/DBMA/data/제련완성본/registry/documents.json
```

에 대한 write/migration/reclassification 절대 금지. 구체적으로:
- 90개 기존 문서 bulk migration 금지
- fixture를 Personal로 만들기 위해 production registry 수정 금지
- 테스트를 위해 production registry 사용 금지
- ingestion pipeline을 통해 production registry를 우회적으로
  수정하는 것도 금지

**이 요구사항이 G0(격리 워크트리 전용 작업)와 충돌하지 않도록,
아래 G5에서 격리된 테스트 환경을 별도로 구성한다 — "실제 앱 테스트를
하려면 production을 써야 한다"는 상황 자체를 아래 절차로 제거한다.**

## G3 — AD-01 구현 목표 (변경 없음, 재확인)

```text
Authoritative Membership
        ↓
Document
        ↓
TSU / Candidate
        ↓
Evidence
        ↓
GS
```

path pattern을 membership authority로 사용하지 않는다.

## G4 — AD-02 구현 목표 (변경 없음, 재확인)

```text
Query Role ≠ Corpus Role
```

금지: Personal boost, fixed Personal quota, Default exclusion,
arbitrary score rewrite, 별도 retrieval engine, GS 내부 retrieval.
허용: relevance retrieval 결과에 corpus role을 보존하면서
role-aware merge를 적용하는 것.

## G5 — 격리된 Fixture 환경 구성 (신규, 근본 원인 해소)

**원인**: `/Users/David/DBMA-cw04-nae-app`는 `origin/main`에서 새로
만든 워크트리라 `data/`(gitignore 대상)가 아예 없다 — 즉 TSU
dataset도, registry도, Tantivy 인덱스도 없어 실제 앱을 정상적으로
띄울 수 없는 상태였다. 이것이 1차 시도가 금지된 main checkout으로
넘어간 근본 원인이다.

**해결**: 이미 검증된 격리 데이터셋(`/Users/David/DBMA-rpv-c8f7e41a/output/bench/`
— RPV-05/06 전 과정에서 CUE가 반복 검증한 204,272건 TSU dataset +
Tantivy 인덱스, real file copy, production과 완전 분리)을 이 워크트리
전용으로 **실제 파일 복사**(심볼릭 링크 금지, 기존 RPV 격리 원칙과
동일)한다:

```bash
cd /Users/David/DBMA-cw04-nae-app
mkdir -p output
cp -R /Users/David/DBMA-rpv-c8f7e41a/output/bench output/bench
mkdir -p "data/제련완성본/registry"
```

`config.yaml`의 `output_dir: "data/제련완성본"`는 **상대경로**이므로,
이 워크트리 안에서는 자동으로 `/Users/David/DBMA-cw04-nae-app/data/제련완성본`
를 가리킨다 — production(`/Users/David/DBMA/data/...`)과 물리적으로
완전히 분리된 별도 디렉터리다. registry 파일(`documents.json`)이
이 경로에 없으면 `resolve_corpus_type()`의 fail-safe 로직에 따라
전부 `"default"`로 동작한다(정상, production 오염 없음) — 신규
문서를 이 워크트리의 UI로 업로드하면 이 경로에 새 `documents.json`이
**독립적으로** 생성된다.

**RPV fixture 업로드는 이 격리 환경에서만 수행한다** — 2026-09-28
HQ 확정 4조건(실사용자 자료 금지/fixture만 업로드/계정·evidence ID
고정 기록/사후 보존상태 기록)을 그대로 적용하되, "실제 사용자 계정"
개념 자체가 이 격리 환경에서는 이 워크트리 자체가 격리이므로 단순화
가능 — 단, 기록 의무(3, 4번 조건)는 동일하게 유지한다.

**진행 순서**:
```text
Approved baseline (d202238d)
      ↓
isolated fixture setup (본 G5, cp -R로 격리 dataset 복사)
      ↓
AD-01/AD-02 implementation (이미 완료, 유지)
      ↓
unit tests
      ↓
fixture retrieval (격리 환경에서 fixture A/B 업로드 → registry에
                    독립적으로 personal 기록됨, production 무관)
      ↓
RPV-06a / 06b (정본 질문 그대로)
      ↓
runtime verification (Streamlit 앱을 이 워크트리에서 기동, 격리
                       데이터로 동작)
      ↓
CUE audit
```

## 보고 필수 항목 (11개, 전부 raw 값으로)

1. 정확한 worktree/branch/HEAD(G0 실제 출력)
2. 변경 파일 목록
3. `git diff --stat`
4. `git diff`
5. production registry(`/Users/David/DBMA/data/.../documents.json`)의
   mtime/hash — **작업 전후 동일함을 증명**(변경 없음의 증거)
6. 위 5번이 변경되지 않았다는 증거(예: 작업 시작 전/후 두 번 측정한
   mtime·SHA-1 비교)
7. AD-01 테스트 결과(raw pytest 출력)
8. AD-02 테스트 결과(raw pytest 출력)
9. 기존 retrieval regression(raw pytest 출력)
10. RPV-06a/06b 결과(격리 환경의 registry 조회 결과 포함 — fixture의
    `corpus_membership` 값을 그 격리 registry에서 직접 인용)
11. 실제 Streamlit runtime 결과(이 워크트리에서 기동한 앱의 화면
    텍스트/응답 그대로 인용)

"통과함"/"정상 동작함" 같은 서술만으로는 승인 근거가 되지 않는다 —
CW-03 이후 확립된 보고 표준 그대로 적용.

## Gate 규칙 (변경 없음)

C1은 GREEN/HQ APPROVED/Gate 2B COMPLETE를 스스로 선언하지 않는다.
구현 + 증거 제출까지가 C1의 역할이다.

```text
C1 구현 (본 문서 범위)
    ↓
C1 보고 (위 11개 항목)
    ↓
CUE 독립 검증(production registry mtime/hash 불변 확인 최우선)
    ↓
HQ 최종 결정
```

## 현재 상태

```text
CW-04 Recovery                   [✓ HQ]
Approved baseline                d202238d
Worktree                         /Users/David/DBMA-cw04-nae-app
Main checkout                    /Users/David/DBMA [SEALED — 계속 봉인]
Gate 2B Clean-Room Re-Auth       [AUTHORIZED — 본 문서]
C1                                [착수 가능, G0-G5 전부 준수 필수]
CUE                                [C1 보고 대기 → production registry
                                    불변 최우선 검증]
```
