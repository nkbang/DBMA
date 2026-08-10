# NAE Identifier Crosswalk Review Package 001

**Project:** NAE-IDENTIFIER-CROSSWALK-DESIGN-001 Phase 6
**작성일:** 2026-08-05
**대상 독자:** C1(Architecture Gatekeeper) — 구현 지시 아님, 검증만 요청.

---

## 검토 대상 문서(5개, 전부 Design Only)

```
docs/NAE_IDENTIFIER_INVENTORY_002.md
docs/NAE_IDENTIFIER_CROSSWALK_SCHEMA_001.md
docs/NAE_IDENTIFIER_CROSSWALK_MAPPING_POLICY_001.md
docs/NAE_IDENTIFIER_CROSSWALK_ADR_IMPACT_001.md
docs/NAE_TSU_IDENTIFIER_CONTRACT_001.md
```

---

## Required Questions

| 질문 | 답변 |
|---|---|
| Identifier 불일치 원인은? | Manifest/Registry `source_id`(예: `BAP-CHURCH-DAGG-001`)와 Corpus `canonical/`/TSU `identifier`(예: `PBC1742`)가 **애초에 서로 다른 두 시스템에서 독립적으로 생성된 값**이기 때문(Inventory 002 §5) — 오류나 버그가 아니라 두 계층 사이에 번역 계약이 한 번도 만들어진 적이 없었다는 사실. 부가로 Registry `sources.yaml`의 `file_path`가 가리키는 경로도 NAE-GIT-HISTORY-CLEANUP-001 이후 실제 디렉토리 구조와 어긋나 있음을 확인(Inventory 002 §2). |
| Crosswalk Layer 필요한가? | **예.** Authority↔Manifest는 이미 1:1로 잘 연결되어 있어(source_id 10/10 일치) 그쪽엔 Crosswalk이 필요 없지만, Manifest↔Corpus/TSU 구간은 실측 결과 0/10 일치 — 이 구간을 잇는 번역 계층이 없으면 TSU Pipeline이 Manifest Gate를 참조할 방법 자체가 없다(참조할 identifier가 없으므로). |
| ADR-017 영향? | **없음.** canonical_id/legacy_id authority 완전 유지(ADR Impact 001) — Crosswalk은 그 값들을 조회만 하고 절대 쓰지 않는다(Mapping Policy Rule 1). |
| ADR-015 영향? | **당장 없음.** ADR-015 자체가 아직 미구현(Proposed, 구현 근거 없음, 승격 보류) — 지금 발견된 문제는 이미 유입된 legacy Pilot corpus의 문제이지 ADR-015가 다루는 "신규 유입" 문제가 아니다. 향후 ADR-015가 실행되면 그 Ingestion Lifecycle에 Crosswalk 생성 단계를 추가할지 별도 검토 권고(ADR Impact 001). |
| TSU Gate 연결 방식? | Crosswalk Resolver가 Manifest→TSU 사이에 신규 계층으로 들어가며, `TSU_ELIGIBLE=READY` **AND** Crosswalk `mapping_status=manual-confirmed`(사람이 최종 확인한 매핑) 두 조건을 모두 만족하는 entry만 TSU Builder에 전달한다(TSU Identifier Contract 001 §4) — 기존 TSU Builder 내부 로직(claim 추출 등)은 무수정. |
| Retrieval 보호 여부? | **보호됨.** 이번 5개 문서 어디에도 `core/retrieval.py`나 Retrieval 관련 코드 변경 제안이 없다 — Crosswalk은 Manifest↔Corpus/TSU 구간에서 끝나며, Retrieval은 그보다 하류(downstream)에 있어 이번 설계의 직접 대상이 아니다. 다만 `NAE/pipeline/index/`(Qdrant 연동)가 이미 존재한다는 사실은 Preflight Report에서 별도 기록해 두었다(이번 Crosswalk 설계 범위 밖, 참고용). |

---

## C1에게 요청하는 것

1. Crosswalk Schema(§Schema 001)의 필드 구성이 향후 Manifest/Registry
   구조와 충돌 없이 확장 가능한지 검토
2. Mapping Policy(§Mapping Policy 001)의 3단계 신뢰도 체계
   (`evidence-backed` → `manual-confirmed`)가 "추측 금지" 요구사항을
   충분히 강제하는지 검토
3. ADR Impact 분석(§ADR Impact 001)에서 "이번 단계 수정 불필요, ADR-019
   저장 위치 결정 시점에 재검토"라는 판단이 Architecture Freeze Rule
   해석상 타당한지 검증
4. TSU Identifier Contract(§TSU Identifier Contract 001)의 Resolver
   삽입 지점(`build_tsu_for_all`의 identifier 열거부 대체)이 기존
   TSU Builder 로직을 실제로 무수정으로 남길 수 있는 설계인지 코드
   구조 재확인

**C1은 이 5개 문서에 대한 구현을 지시받지 않는다** — 설계 검증만
수행하고, 승인 이후에만 Crosswalk Adapter 구현 단계로 진행한다.
