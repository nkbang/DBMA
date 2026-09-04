# DBMA-TLI (Theology Language Intelligence) — 아키텍처 비전 v1

작성: Human HQ (2026-07-24) — CUE 검토 후 보존
성격: **장기 비전 문서.** 구현 근거가 아니라 방향 근거로 쓴다. 실제
구현 범위는 항상 개별 Task Order(§20 참고)가 결정한다 — 이 문서가
Task Order를 임의로 확장하는 근거로 쓰이면 안 된다.

---

## CUE 검토 메모 (2026-07-24)

- 승인: Hunspell을 UI가 직접 호출하지 않고 어댑터 인터페이스 뒤에
  두는 원칙(§5, §6), 사전을 코드에 하드코딩하지 않고 리소스 파일로
  관리하는 원칙(§7~9).
- 보류/제한: §4의 Spell/Dictionary/Style/Citation/Named Entity Engine
  아키텍처 다이어그램은 **장기 목표로만** 유지한다. 각 Engine은 실제
  수요가 생겼을 때 별도 Task Order로 하나씩 구현한다 — 지금 당장
  빈 스텁 파일로 미리 만들지 않는다(프로젝트 원칙: half-finished
  구현 금지, 불필요한 추상화 금지).
- 이번 라운드(Task Order 014 + addendum)에서 실제로 만드는 것은
  `core/tli/spell_engine.py`(인터페이스) + `core/tli/hunspell_adapter.py`
  (구현체) 두 파일뿐이다. Dictionary/Style/Citation/Named Entity
  Engine은 이번에 생성하지 않는다.

---

## 원문

### 1. Mission

DBMA는 일반 문서 편집기가 아니다. DBMA는 Theology Intelligence
Platform이다. 이번 작업의 목적은 "한국어 맞춤법 기능"을 추가하는
것이 아니다. 이번 작업은 Theology Language Intelligence(TLI)의
기반을 구축하는 것이다.

앞으로 Sermon Writing / Research Workspace / RAG / TSU / Retrieval /
Generation / Translation / Bible Citation / Theology Search 모든
영역은 TLI를 공통 언어 계층(Language Layer)으로 사용하게 된다.
TLI는 DBMA의 Core Infrastructure이다. 절대로 단순 Utility Module로
구현하지 말 것.

### 2. Fundamental Principle

TLI는 Spell Checker가 아니다. TLI는 Language Intelligence Layer다.

```
Application Layer → Generation → Research → Retrieval → TLI → Dictionary → Storage
```

모든 기능은 TLI API를 통하도록 설계한다. 직접 Hunspell을 호출하는
코드는 허용하지 않는다.

### 3. Long-term Goal

3.1 Korean Spell Checking(맞춤법/띄어쓰기/오타)
3.2 Theology Dictionary(칭의/성화/영화/중생/대속/속죄/언약/선택/예정/섭리 등 수천 개)
3.3 Biblical Proper Names(므비보셋/느부갓네살/스룹바벨/에바브로디도 등)
3.4 Biblical Places(기브온/길갈/브엘세바/드고아 등)
3.5 Denominational Dictionary(교단별 용어, 예: 세례↔침례)
3.6 Style Guide(예: 예수님↔예수 그리스도, 첫 등장 권장)
3.7 Citation Intelligence(예: 롬 8:28 ↔ Romans 8:28)
3.8 Theology Metadata(term/language/english/greek/hebrew/doctrine/
related_terms/related_passages/aliases/frequency/source)

### 4. Architecture (장기 목표)

```
TLI
├── Spell Engine
├── Dictionary Engine
├── Style Engine
├── Citation Engine
├── Named Entity Engine
└── API
```

각 Engine은 독립적으로 테스트 가능해야 한다.

### 5. Layer Rule

`UI → Hunspell` 처럼 직접 연결하지 않는다. 반드시
`UI → TLI API → Spell Engine → Hunspell`.

### 6. Dependency Rule

외부 라이브러리는 교체 가능해야 한다(Hunspell → Nuspell/LanguageTool
등). Adapter Pattern을 유지한다.

### 7. Data Rule

Dictionary는 코드에 작성하지 않는다. 반드시 Resource로 관리한다:
`resources/dictionary/{theology,biblical,style,user}/`

### 8. User Dictionary

사용자 사전은 독립 저장(`user.dict`), 자동 생성 가능.

### 9. Theology Dictionary

Python Source에 `WORDS=[...]` 형태로 작성하지 않는다. 반드시 Resource
File(JSON/YAML/Hunspell Dictionary/SQLite 중 하나).

### 10. Future Growth

향후 약 50,000 신학용어를 저장할 수 있어야 한다. 메모리에 전부
적재하지 않는 구조도 고려한다.

### 11. Retrieval Integration

향후 Retrieval은 질의를 TLI를 통해 Normalize한다(예: 칭의 → Justification,
또는 동의어 확장).

### 12. Generation Integration

Generation은 TLI를 통해 용어 일관성을 유지한다(예: 한 문서 안에서
침례/세례 혼용 시 경고).

### 13. TSU Integration

TSU는 용어를 자동 Tagging한다(Doctrine/Person/Place/Event/Book/
Church History).

### 14. Performance Requirement

실시간 편집은 50ms 이하 권장. 무거운 검사는 Background.

### 15. Offline First

DBMA는 인터넷 없이 동작해야 한다. 클라우드 API 의존 금지.

### 16. Coding Rule

Magic String 금지. Singleton 남용 금지. Global State 금지. Hard
Coding 금지.

### 17. Documentation Rule

새 모듈마다 README 작성. Public API 설명. 의존성 설명. 폴백 절차
설명.

### 18. Testing Rule

최소: Spell / Dictionary Loading / Unicode / Hangul / Bible Names /
User Dictionary / Regression.

### 19. Current Scope (IMPORTANT)

이번 Task는 전체 TLI를 구현하는 것이 아니다. TLI Foundation을 만드는
것이다.

**이번 단계에서 구현 가능한 범위**: TLI Layer 생성, Spell Adapter,
Dictionary Loader, Resource 구조, User Dictionary, Hunspell Adapter,
향후 Engine 확장 가능한 API.

**이번 단계에서 구현하지 않는 것**: Theology Search, Semantic
Analysis, Style Engine, Citation Intelligence, TSU Tagger, RAG
Expansion, Doctrine Classification.

단, 향후 추가 가능한 구조를 반드시 유지한다 — **다만 이는 "인터페이스가
확장 가능한 형태로 설계되어야 한다"는 뜻이지, "지금 빈 스텁 파일을
미리 만들어 둔다"는 뜻이 아니다** (CUE 주석, 2026-07-24).

### 20. Existing Task Order Priority

`docs/agents/c1/C1-TASK-ORDER-014.md`의 설계와 구현 범위는 그대로
유지한다. 본 문서는 상위 비전과 아키텍처 원칙을 정의하는 것이며,
기존 Task Order를 임의로 변경하거나 확장하는 근거로 사용해서는 안
된다.

- §2 설계는 변경하지 않는다.
- 구현 범위를 임의로 확대하지 않는다.
- Hunspell 설치 실패 시에는 기존 Task Order의 §5 폴백 절차를 그대로
  따른다.
- `brew install` 등 시스템 변경이 필요한 경우에는 반드시 Human HQ의
  사전 승인을 받는다.
- 완료 후에는 기존 Task Order의 §6 절차에 따라 변경 파일 목록과
  테스트 결과를 `docs/agents/c1/`에 기록하고 CUE 리뷰를 요청한다.
- C1은 직접 커밋하지 않는다.

### 21. Engineering Philosophy

이번 작업의 성공 기준은 "맞춤법 기능이 동작한다"가 아니다. 성공
기준은 DBMA의 향후 5~10년 동안 사용할 Theology Language
Intelligence(TLI)의 기반이 되는 안정적인 언어 계층을 구축하는
것이다. 새로운 기능을 추가하더라도 기존 Retrieval, Generation,
TSU, Research Workspace와 느슨하게 결합(loose coupling)되어야 하며,
TLI는 DBMA 전반에서 재사용 가능한 공통 인프라로 유지되어야 한다.
