# GS 통합 이후 여정 계획 — CUE 점검 보고

- 작성: CUE · 2026-09-30
- 대상: HQ가 제시한 여정 계획 두 가지
  - 1차: ④ 이후 13단계
  - 수정안: 1차 점검 결과를 반영한 것
- 기준
  - 결과 브랜치: `tmp/fu007-integration-trial`
  - ④ 결정 기록: `bf68c38a` / 최종 보고: `52f02143`
- 표기: [CONFIRMED] 코드·문서로 확인 / [INFERRED] 추론
- **MUTATION: NONE**

## 1. 1차 계획 점검 — HQ가 모두 채택함

### 1.1 수정이 필요했던 것 (사실과 어긋남)

| # | 계획 내용 | 사실 | 근거 |
|---|---|---|---|
| A1 | FU-007 = 한국어 답변에 쓸 원문 인용 구간의 번역 방식 | FU-007은 **검색용 한국어 질의 번역**이다. A는 main, B는 dev의 LLM 번역, C는 결합안이다. main→dev 병합에서 충돌하는 3파일과 묶여 있다. 계획에서 말한 질문(답변 쪽 인용 구간)은 ④ B + 3-b 추출기 계약에 속하는 사항이다 [CONFIRMED] | `NAE_EUAT_001_FU007_INTEGRATION_TRIAL_RESULT.md` 1·8절, ⑤ 설계 P-4 |
| A2 | Phase 0(dev 착지) 없음 | `origin/dev/dbma-engine`에는 다음이 하나도 없다(`git ls-tree`로 확인) [CONFIRMED]: `grounded_*` 모듈, 근거 계층, `citation_verifier.py`, GS 테스트. GS 테스트 105개는 결과 브랜치에서만 수집된다 | ⑤ 설계 단계 0 |
| A3 | C1에게 구현 지시 | CUE Operating Policy는 **구현은 CUE, C1은 독립 검토(Audit)**로 정한다 [CONFIRMED] | CLAUDE.md |

### 1.2 보완이 필요했던 것

| # | 항목 | 사실 |
|---|---|---|
| B1 | ④ 기준 커밋 | 계획에 적힌 `b1a68417`은 중간 상태다. 정규화 제외와 grounded 문구 유지는 **`bf68c38a`**에 기록됐다 |
| B2 | ⑤ CLOSED | ⑤ 자료(`802f2e0f`)는 ④ 결정 전에 선택지별로 쓴 것이라 확정 조합이 반영돼 있지 않다. C1 검토도 COMPLETE로 채택하지 않았다 |
| B3 | "확인된 claim"의 정의 | `assemble_grounded_answer`는 `valid`(ID 소속)만 본다(`grounded_answer.py` L111~L124) [CONFIRMED]. 3-b 구간 검사에 실패한 claim을 빼는지, 즉 전면 유보 판정에서 0개를 무엇으로 세는지는 정해지지 않았다. **새 ADR에서 정해야 한다** |
| B4 | citation_verifier | dev에는 이 모듈이 없다. 그래서 ④-5의 네 번째 문구가 나올 곳이 없다. C1 검토 대상 파일도 dev에 없으므로 검토할 브랜치를 명시해야 한다 |
| B5 | HQ 승인의 의미 | Evidence Before Promotion 규칙상 착수 승인은 Proposed 상태에서 한다. Approved 판단은 구현·회귀·C1 검토를 마친 뒤에 한다 |
| B6 | 빠진 항목 | ADR-009 Amendment(교단 지시문) 트랙, 구현 브랜치와 dev 반영 경로. 현재 푸시가 허용된 곳은 `tmp/fu007-*`뿐이다 |

## 2. 수정안 점검 — 보완 4건

HQ 수정안의 큰 순서는 확정된 사실과 맞는다. 다만 게이트 세 곳이 빠졌고 표기 한 곳을 바로잡아야 한다.

| # | 빠진 것 | 근거 |
|---|---|---|
| R1 | **새 ADR에 대한 C1 검토**: 수정안은 새 ADR 작성 다음이 바로 HQ 착수 승인이다 | CLAUDE.md "C1 Review 요청 시점: 새 ADR 작성" [CONFIRMED] |
| R2 | **구현을 마친 뒤의 C1 검토**: C1 검토가 Phase 0에만 있다 | Evidence Before Promotion 승격 조건 3 "독립 리뷰(C1) 완료" [CONFIRMED] |
| R3 | **Phase 0의 dev 반영 승인**: 수정안은 착지 구현 → C1 검토 → 새 ADR로 바로 이어진다 | 아래 세 가지 모두 HQ 승인이 필요하다 [CONFIRMED]. ① 충돌 파일 `hybrid_candidate_pipeline`·`candidate_generator`는 검색 코어다(CLAUDE.md 예외 "Retrieval Engine 변경"). ② `origin/dev/dbma-engine`은 푸시 금지 상태다. ③ Tantivy 인덱스를 다시 빌드해야 한다 |
| R4 | **READ-ONLY 단계의 이름**: 수정안 표기는 "충돌 구조 확인"인데, 충돌 3파일의 구조와 해결은 FU-007 시도에서 이미 확인했다. 따라서 이 단계는 "Phase 0 착지 범위 비교"다 | FU-007 결과 문서 1절 |

R3에 대한 참고 [INFERRED]: dev로 들어오는 GS 모듈은 운영 경로에 연결되지 않은 상태다. 이것은 B1이 말하는 "운영 경로 교체"가 아니다. 따라서 새 ADR보다 먼저 들여와도 B1과 충돌하지 않는다.

R4에서 함께 정할 사항 [CONFIRMED]:
- main→dev 병합을 하면 main에만 있는 커밋 91개가 한꺼번에 들어온다.
- 그 안에 공개 자료 답변 경로(`NAE/public_answer.py`, 다섯 번째 호출자)가 섞여 있다.
- ④에서 GS ADR 범위를 채팅만으로 정했더라도, 병합하면 이 경로는 dev에 들어온다.
- 그래서 Phase 0 범위에서 정해야 한다: 이 경로를 함께 들일지, 들이되 연결하지 않을지.

## 3. 보완을 반영한 여정

```text
④ CLOSED (bf68c38a / 52f02143)
→ [HQ] FU-007 질의 번역 A/B/C 결정 (충돌 3파일 해소 방식 포함)
→ [CUE READ-ONLY] Phase 0 착지 범위 비교
     grounded_* / 근거 계층 / citation_verifier / GS tests / FU-007 통합 /
     Tantivy 재빌드 / ADR-036·037 상태 / 공개 자료 답변 경로 / dev 검색 코어 회귀
→ [HQ] Phase 0 범위 확정
→ [CUE] 착지 구현 (tmp 브랜치) → [C1] 검토 → [HQ] dev 반영 승인 → dev 반영·인덱스 재빌드
→ [CUE] 새 ADR (Proposed) → [C1] 검토 → [HQ] 착수 승인
→ [CUE] 구현 → 회귀 → 브라우저 검증 → [C1] 검토
→ [CUE] P0-5 의미 독립 검증 → [HQ] 최종 승인 → ADR Approved → 릴리스 판단

별도 트랙: ADR-009 Amendment (교단 지시문)
```

계속 유지할 원칙 [CONFIRMED]:
- ADR-036을 고쳐서 해결하지 않고 새 ADR로 해결한다.
- ADR-037은 GS ADR 범위에서 제외한다.
- executor는 B9가 허용한 예외 이름(`grounded_synthesis*_executor.py`)으로 둔다.
- 자동 검증과 의미 grounding 검증은 서로 다르다. GS 통합에 성공했다고 해서 P0-5를 해결했다고 표현하지 않는다.

## 4. FU-007 결정 자료의 현황

| 자료 | 위치 |
|---|---|
| A/B 측정(검색 단계 P0-5 24건) | FU-007 결과 문서 3절 |
| C 재측정 | 같은 문서 8절 |
| C 생성 단계 24건 | 같은 문서 9절 |

8절 C 재측정 결과:
- 대리 지표(120점 만점): A 45 / B 55 / C 60
- 구절 장 표기 적중(25건 중): A 17 / B 3 / C 15
- 회귀에 결함이 없는 방식은 C 하나다.

- 주의: 같은 문서 8.4절에는 **CUE가 쓴 결합안 C 권고**가 남아 있다. 이 권고는 지금의 추천 없음 방침보다 먼저 쓴 것이다.
- 권고를 뺀 결정 자료가 필요하면 별도로 작성한다(지시 대기).

## 5. MUTATION

- 코드·ADR·prompt를 바꾸지 않았다. 이 문서를 커밋·푸시하는 것만 수행한다.
