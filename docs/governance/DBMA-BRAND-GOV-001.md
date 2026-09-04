# NAE BRAND FREEZE — GLOBAL BRAND GOVERNANCE DIRECTIVE

**Document ID:** DBMA-BRAND-GOV-001
**Status:** APPROVED / FROZEN
**Authority:** Human HQ
**Effective:** 2026-07-28
**Scope:** Entire DBMA ecosystem
**Applies To:** C1 / CUE / Claude Code / AI Agents / Developers / Documentation / UI / Release Artifacts

## 1. PURPOSE

본 지시는 DBMA 프로젝트의 배포 전 브랜드명을 최종 확정하고, 이후 모든 개발·문서·UI·배포 작업에서 동일한 브랜드 정체성을 유지하기 위한 Global Naming & Branding Freeze이다.

Human HQ가 승인한 최종 브랜드는 다음과 같다.

- 내서재
- NAE

이 결정은 이후 별도의 Human HQ 승인 없이 변경하거나 재해석할 수 없다.

## 2. FINAL BRAND IDENTITY

### 2.1 Korean Brand — FROZEN

**내서재**

한국어 사용자에게 노출되는 공식 제품 브랜드명이다. 모든 사용자-facing UI에서 제품을 지칭할 때 기본적으로 "내서재"를 사용한다.

### 2.2 English Brand — FROZEN

**NAE**

영문 공식 브랜드 식별자이다. 반드시 대문자 NAE로 표기한다.

허용: `NAE`, `내서재 · NAE`, `내서재 (NAE)`

금지: `Nae`, `nae`, `N.A.E.`, `NAE AI`, `NAE AI Assistant`, `NAE Ministry AI`, 임의의 새로운 acronym expansion

### 2.3 Internal Engineering Identity — PRESERVED

**DBMA**

기존 DBMA는 폐기하지 않는다. 다음 영역에서 계속 공식 internal engineering/project identifier로 유지한다:
repository, Python package/module names, source code, configuration identifiers, environment names,
database/vector-store paths, test fixtures, internal APIs, Git history, CI/CD, scripts,
Docker/container identifiers, development environments, internal architecture documentation.

브랜드 변경은 DBMA → NAE의 global code rename이 **아니다**.

## 3. BRAND HIERARCHY

```text
USER-FACING BRAND
        │
        ├── 내서재
        │
        └── NAE
              │
INTERNAL ENGINEERING IDENTITY
              │
             DBMA
              │
      ┌───────┼────────┐
      │       │        │
     TSU   Retrieval   SIL
             Engine
```

핵심 원칙: 내서재 / NAE is the product brand. DBMA is the internal engineering identity. 두 이름을 혼동하지 않는다.

## 4. BRAND MEANING

공식 브랜드 핵심 메시지: **나의 자료 · 나의 연구 · 나의 목회**

NAE acronym expansion은 **동결되지 않았다(NOT FROZEN)**. `Notes · Archive · Exploration` 등은 브랜드 철학 설명용 후보일 뿐 공식 확정이 아니다. 어떤 Agent도 acronym expansion을 임의로 문서/UI에 확정 기재해서는 안 된다. 향후 Human HQ 별도 승인 대상.

## 5. USER-FACING NAMING RULE

- 한국어: 내서재
- 영문: NAE
- 병기: 내서재 · NAE 또는 내서재 (NAE)

## 6. UI RULES

적용 대상: Application title, Main header, Sidebar brand, Welcome/Login screen, Empty state, About/Help page,
User documentation, Onboarding, Export metadata, PDF/report headers, User-facing notifications,
Release notes(사용자향), Marketing/presentation material.

## 7. INTERNAL CODE RULES

다음은 임의로 변경하지 않는다: `DBMA`, `dbma`, `dbma_ui.py`, `core/`, `TSU`, `RetrievalEngine`, `SIL`.

금지: `DBMA → NAE`, `dbma → nae`, `dbma_ui.py → nae_ui.py`, `core/dbma_* → core/nae_*` 등
단순 브랜드 변경을 이유로 source tree, imports, package names, config keys, database paths, API identifiers 변경 금지.

## 8. REPOSITORY AND GIT RULE

Repository/Project identifier/internal architecture는 DBMA로 유지. 브랜드 변경을 이유로 Git history(commit/branch/tag/issue/test reference) rewrite 금지. 기존 historical references는 보존한다.

## 9. DOCUMENTATION RULE

- User-facing documentation: 내서재 (NAE)
- Engineering documentation: DBMA
- 필요 시: "DBMA — internal engineering project for NAE (내서재)"

## 10. AGENT BEHAVIOR RULE

**MUST:**
1. 이미 확정된 내서재 / NAE 브랜드를 사용한다.
2. DBMA를 internal identifier로 유지한다.
3. 새로운 제품명을 제안하지 않는다.
4. 기존 브랜드를 임의로 변경하지 않는다.
5. NAE acronym의 새로운 expansion을 공식화하지 않는다.
6. 브랜드 변경과 코드 rename을 혼동하지 않는다.
7. 브랜드 충돌/ambiguity 발견 시 변경하지 말고 Human HQ에 보고한다.

**MUST NOT:**
- 새로운 브랜드명 독자 제안, `d'BMA` 재도입, `DBMA`를 사용자-facing product name으로 되돌림,
  `NAE`를 다른 acronym으로 재정의, `NAE AI`/`NAE Bible`/`NAE Ministry` 등 파생 제품명 임의 생성,
  전역 DBMA → NAE code rename, repository/package rename, historical Git reference 변경,
  기존 브랜드 정책을 architecture task의 일부로 임의 수정.

## 11. CHANGE CONTROL

다음은 Human HQ의 명시적 승인 없이는 변경하지 않는다: Korean/English product name, NAE spelling/capitalization,
brand mark, official tagline, official acronym expansion, brand hierarchy, product family naming,
public repository identity, user-facing product identity.

더 좋은 이름을 발견해도 자체 변경하지 않고 다음 형식으로 보고한다:

```text
BRAND CHANGE REQUEST
Current: 내서재 / NAE
Proposed: [proposal]
Reason: [reason]
Impact: [impact]
Recommendation: [recommendation]
Status: WAITING FOR HUMAN HQ APPROVAL
```

## 12. PRIORITY RULE

Human HQ approved Brand Freeze takes precedence over개별 Task Order. Task Order가 "rename product",
"update branding" 등으로 표현되어 있더라도 이미 확정된 이름을 다른 이름으로 변경하는 것으로 해석하지 않는다.

## 13. RELEASE GATE

**Brand Identity:** 사용자 화면 공식 제품명 `내서재` 표시 확인 / 영문 브랜드 `NAE` 표시 확인 /
임의의 다른 제품명 잔존 여부 확인 / `d'BMA` 사용자-facing 잔존 여부 확인 /
`Digital Bible Ministry Archive` 공식 제품명 표시 여부 확인.

**Engineering Identity:** DBMA internal identifier 유지 확인 / Python imports 손상 여부 /
configuration keys 변경 여부 / database/vector paths 변경 여부 / Git history 보존 여부.

**Brand Consistency:** UI / README / Documentation / About / Help / Export / Release artifacts 전체 일관성.

## 14. FINAL AUTHORITY

이 문서의 최종 결정권자는 Human HQ이다. AI Agent, C1, CUE, reviewer, developer 또는 다른 자동화 시스템은
본 문서의 브랜드 결정을 재해석하거나 무효화할 수 없다. 새로운 브랜드 변경이 필요하다고 판단되는 경우:
**DO NOT CHANGE. REPORT TO HUMAN HQ.**

## 15. FINAL FROZEN STATEMENT

The product is named "내서재" in Korean and "NAE" in English. DBMA remains the internal engineering and
project identity. This naming is frozen and may not be changed without explicit approval from Human HQ.

제품명은 한국어로 "내서재", 영어로 "NAE"이다. DBMA는 내부 엔지니어링 및 프로젝트 식별자로 유지한다.
이 네이밍은 동결되며 Human HQ의 명시적인 승인 없이는 변경할 수 없다.

**STATUS: FROZEN**
