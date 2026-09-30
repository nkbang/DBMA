# GS 운영 통합 — ⑤ 구현 설계 자료

- 작성: CUE · 2026-09-30
- 단계: HQ 결정 순서 ⑤ 구현 설계
- 선행 결정
  - ① 릴리스 라인 = `dev/dbma-engine`
  - ② ADR-036 = GS 경계, ADR-037 = 공개 자료 근거 답변
  - ③ GS 계약 = A(citation provenance) + B(원문 언어 citation span). C(semantic grounding) 제외
- 선행 사실: [④ 생성·스트리밍 계약 브리프](NAE_GS_GENERATION_CONTRACT_BRIEF_HQ_REPORT.md) (`09cd60dc`)
- 성격: **구현 명령이 아니다.** ④의 계약 항목 5가지가 아직 HQ 미결이므로, 결정 조합별 설계를 나란히 제시한다. 옵션을 추천하지 않는다.
- 방법: 읽기 전용. 코드·ADR·prompt 변경 없음.
- 표기: [CONFIRMED] 코드·문서로 확인 / [INFERRED] 추론 / [DESIGN OPTION] 설계안 / [UNKNOWN] 미확인

## 0. 착수 전제 (구현 전에 반드시 성립해야 하는 것)

| # | 전제 | 근거 | 현재 |
|---|---|---|---|
| P-1 | **새 ADR 승인** | ADR-036 B1 "두 경로 공존, 병합은 별도 ADR" / "P12 이후 새 ADR과 HQ 승인". P12 완료(`ec204adf`) | 미작성 |
| P-2 | ④ 계약 항목 5가지 HQ 결정 | ④ 브리프 마지막 절 | 미결 |
| P-3 | 착지 라인에 GS·근거 계층이 있을 것 | ① 결정 자료 5절: dev에는 없음 | dev에 없음 |
| P-4 | FU-007 번역 방식 결정(병합 충돌 3개) | FU-007 결과 문서 8절 | 미결(결합안 C 권고 상태) |

[CONFIRMED] P-1이 없으면 Architecture Freeze Rule과 B1에 따라 구현을 시작할 수 없다. 이 문서는 P-1(새 ADR)의 **설계 입력**이다.

## 1. 목표 계약 (③ 그대로)

| 층 | 보장 | 구현 수단(현재 있는 것) |
|---|---|---|
| A. Citation provenance | 인용한 evidence ID ∈ included set, provenance 추적 가능 | `bind_claims`(`grounded_claims.py` L57~), `check_citation_provenance`의 `id_exists`·`provenance_traceable`(`grounded_citation.py` L154~L186) |
| B. Citation span | 원문 언어 인용 구간이 해당 evidence text에 글자 그대로 있음 | `_check_span_in_text`(`grounded_citation.py` L110~L119). **현재는 claim 본문 전체를 구간으로 씀**(④ C5) |
| C. Semantic grounding | **보장하지 않음** | 없음. B6·C-03에 따라 사람·CUE 표본 검토로 분리 |

표시 명칭: 검증 결과는 "citation/provenance span verified". "grounded"를 "근거로 뒷받침됨"으로 옮겨 표시하지 않는다(③).

## 2. 착지 준비 (Phase 0) — dev로 들여올 것

[CONFIRMED] main에 있고 dev에 없는 파일(① 자료와 이번 조회):

| 층 | core | tests |
|---|---|---|
| 근거 계층 | `evidence_model.py`, `evidence_pool.py`, `evidence_assembly.py`, `evidence_adapters/tsu_adapter.py` | `test_evidence_model.py`, `test_evidence_pool.py`, `test_evidence_assembly.py` |
| GS | `grounded_synthesis_input.py`, `grounded_claims.py`, `grounded_answer.py`, `grounded_citation.py` | `test_grounded_*.py` 6개(테스트 함수 105개) |
| 인용 검증 | `citation_verifier.py` | `test_citation_verifier.py` |
| 검색 부속 | `index_page_detector.py` | `test_index_page_detector.py` |

- [INFERRED] 이 파일들을 개별로 옮기는 것보다 FU-007 병합(main→dev, 충돌 3개)으로 들여오는 편이 계보가 깨끗하다. 방법은 FU-007 결정 사항이다(P-4). 검색 코어 변경이 포함되므로 C1 Review 대상이다.
- [CONFIRMED] 병합하면 dev의 Tantivy 스키마(한국어 형태소 `_search` 필드)가 유지되어 인덱스 재빌드가 필요하다(FU-007 결과 문서 1절).
- ADR 문서: ADR-036(GS 경계, p4 브랜치에만 있음)과 ADR-037(공개 자료, 번호 정리는 결과 브랜치에만 있음)을 dev에 반영하는 경로도 Phase 0에 들어간다(② 결정 후속).

## 3. 목표 구조 [DESIGN OPTION]

```text
ui/pages/chat.py (5개 호출자)
   │  response = processor.process(...)            ← 현행 그대로
   ▼
[신규] GS 오케스트레이터  core/grounded_synthesis_executor.py
   │  (B9 예외 이름. ollama·GenerationService import 허용. 파일은 현재 없음 [CONFIRMED])
   ├─ assemble_evidence_pool_with_manifest(top_k_results)   ← 기존 core
   ├─ build_synthesis_input(pool, manifest, max_evidence)   ← 기존 GS
   ├─ 생성 (④-1 결정에 따라 A/B/C)
   ├─ bind_claims(raw_claims, synthesis_input)              ← 기존 GS
   ├─ assemble_grounded_answer(claims, synthesis_input)     ← 기존 GS
   └─ check_citation_provenance(answer, synthesis_input, pool) ← 기존 GS
   ▼
GenerationResult (+ 신규 선택 필드)  → UI 표시(④-2 결정에 따라)
```

- **GS 4개 모듈은 수정하지 않는 것을 기본으로 한다**(B8 변경은 ④-3 결정 사항).
- [CONFIRMED] B9: GS 모듈이 `GenerationService`를 부를 수 없으므로, 호출 방향은 오케스트레이터 → GS다.
- `GenerationResult` 확장 [DESIGN OPTION]: `grounded_synthesis: GroundedSynthesisResult | None = None`처럼 기본값 None인 필드를 추가한다. 기존 필드 8개(dev)·9개(main)는 유지되고, 기존 호출자와 테스트에 영향이 없다([INFERRED], dataclass 기본값 규칙).
- 기능 스위치 [DESIGN OPTION]: 기본값 off인 단일 스위치를 둔다. 끄면 현행 경로로 동작한다. 선례로 ADR-037(당시 ADR-036)이 "스위치 하나, 롤백 = false"를 채택했다(`modules.nae_pd.enabled`).

## 4. 결정 항목별 설계

### 4-1. 생성 방식 (④ 결정 1)

| | A. 구조화 생성 | B. 생성 후 추출 | C. 혼합 |
|---|---|---|---|
| 프롬프트 | `prompt_text`에 `[evidence_id: …]` 부착. 출력 형식은 "claim + evidence_ids + 원문 구간" 줄 단위(데모 L90~L100 확장) | 현행 `_build_prompt` 유지 | 구조화 claim 블록 + 목회 문단을 한 번에 생성하거나, 두 단계로 생성 |
| 파서/추출기 | core에 파서 신설. 데모 `parse_llm_claims`는 첫 줄 1개만 만들므로 그대로 쓸 수 없다(④ C5) | LLM 추출기 신설(`ClaimExtractor` Protocol 구현, 오케스트레이터 쪽). 라벨→ID 대응 규칙 필요 | 파서 + 사용자 문단 조립 |
| 근거 ID 확보 | 모델이 ID를 복사(P9 실모델 3건) | 라벨에서 역추적. 같은 라벨이 여러 근거면 모호([INFERRED], ④ C7) | A와 같음 |
| 원문 구간 | 모델이 원문 구간을 복사 → B 검사로 존재 확인 | 한국어 claim에서 원문 구간을 결정적으로 찾을 수 없음([INFERRED]) | A와 같음 |
| LLM 호출 수 | 1 | 2 | 1~2 |
| 실패 처리 | 파싱 실패 → 근거 부족(B5)으로 처리할지, 현행 답변으로 폴백할지 결정 필요 | 추출 실패 시 같은 결정 필요 | 같음 |

### 4-2. 스트리밍과 차단 (④ 결정 2)

| | 흐름 | 필요 변경 | 비고 |
|---|---|---|---|
| S-A 비스트리밍 | generate → validate → display | UI 5곳을 비스트리밍 호출로 전환 | P0-5 생성 시간 32~276초 동안 화면이 비어 있음([CONFIRMED] P0-5 로그) |
| S-B 현행 | stream → display → validate | 없음 | display-before-validation 유지(④ C2) |
| S-C 버퍼 | stream → buffer → validate → display | UI가 `st.write_stream` 대신 스트림을 소비한 뒤 표시. 버퍼는 `GenerationStream._answer_parts`에 이미 있음(④ C6) | 진행 표시 설계 필요 |

차단 정책(S-A·S-C에서만 의미가 있음):

| 정책 | 동작 |
|---|---|
| 경고만 | 현행 ClaimGuard·citation_verifier와 같이 fail-open |
| 부분 차단 | `valid=False` claim과 span 미확인 claim을 본문에서 제외(GS `assemble_grounded_answer`가 이미 valid claim만 조립, L111~L124) |
| 전면 유보 | 확인된 claim이 0개면 B5 고정 문구 |

[CONFIRMED] 구조화 생성(4-1 A)을 원문 그대로 스트리밍하면 claim 표기가 화면에 노출된다. 그래서 A는 사실상 S-A 또는 S-C와 짝을 이룬다.

### 4-3. 원문 인용 구간의 저장 위치 (④ 결정 3)

| 안 | 내용 | ADR 영향 |
|---|---|---|
| 3-a | B8 `Claim`에 `source_spans: list[(evidence_id, span_text)]` 추가. `check_citation_provenance`는 claim 본문 대신 구간으로 검사 | B8 정본 시그니처 변경 → 새 ADR 또는 ADR-036 Amendment([UNKNOWN] 어느 쪽인지 규칙 없음) |
| 3-b | GS 모듈은 그대로 두고, 오케스트레이터가 (evidence_id, 구간)마다 **검증용 Claim**(`text` = 원문 구간)을 만들어 기존 `check_citation_provenance`에 넣는다. 한국어 문장과 구간의 대응은 오케스트레이터 자료구조에 둔다 | B8 무변경. 대신 `Claim.text`의 뜻이 "주장"과 "구간"으로 둘로 쓰인다(설계 부채, 새 ADR에 명시 필요) |
| 3-c | 구간을 저장하지 않음 | B(span) 계약을 한국어 답변에 적용할 수 없음(③ 계약의 실효 없음) |

### 4-4. 새 ADR 범위 (④ 결정 4)

| 범위 | 포함 호출자 | 고려 사항 |
|---|---|---|
| 채팅만 | `chat.py` L481·L566 | 가장 좁음. 본문 해설·공개 자료 답변은 현행 유지 |
| 앱 5곳 전부 | + `nae_public_section.py` L147, `passage_commentary_panel.py` L94, `_passage_commentary_tab.py` L119 | ADR-037(공개 자료) 경로와 교차. ADR-037의 "기존 근거 강제 지시문 재사용" 계약과의 관계를 정해야 함 |
| 공통 | — | 교단 지시문 근거가 ADR-009 Amendment A(**Proposed**). 생성 계약이 바뀌면 교단 지시문 위치도 정해야 함 |

### 4-5. 사용자 노출 문구 (④ 결정 5)

| 내부 상태 | 금지 표현(③) | 가능한 표현 [DESIGN OPTION] |
|---|---|---|
| `status == "grounded"`(valid claim ≥1) | "근거로 확인됨", "검증된 답변" | "인용 출처 확인됨"처럼 A·B 범위만 말하는 문구 |
| span 미확인 | — | "원문 구간을 확인하지 못한 인용" 표시 |
| `insufficient_evidence` | — | B5 고정 문구(`grounded_answer.py` L89) |

## 5. 단계별 진행안 [DESIGN OPTION]

| 단계 | 내용 | 게이트 |
|---|---|---|
| 0 | dev 착지 준비(2절): FU-007 병합, 인덱스 재빌드, ADR-036·037 반영 | FU-007 결정(P-4), C1 Review, 전체 회귀 |
| 1 | 새 ADR 작성: 4-1~4-5 결정 반영, 3절 구조, B1·B8·B9 관계, C 제외 명시 | C1 Review → HQ 승인(P-1) |
| 2 | 오케스트레이터 + 파서/추출기 + `GenerationResult` 확장. 스위치 기본 off | stub LLM 단위 테스트(B7), 기존 GS 테스트 105개·생성 테스트 회귀 |
| 3 | UI 연결(4-2 결정대로, 4-4 범위만) | 스위치 on/off 양쪽 회귀, 화면 확인 |
| 4 | P0-5 24건 기준선 재검증: A·B는 자동 지표로, C는 B6대로 CUE 표본 검토로 **분리 보고** | 기준선 `1b1ac017`(APPINDEX) 대비 |
| 5 | 릴리스 판단 | HQ |

## 6. 검증 설계

| 층 | 지표(자동) | 비고 |
|---|---|---|
| A | claim별 `id_exists` 비율, `valid=False`로 제외된 claim 수, `provenance_traceable` 비율 | 결정적 |
| B | `span_found_in_text` 비율(원문 구간 기준) | 거짓 음성 원인(쪽 머리글·OCR·공백) 분류 병기(③ 3.2절) |
| C | 자동 지표 없음 | P6 방식의 문장 대조 표본. 자동 지표와 **합산하지 않음**(B6, B7) |
| 회귀 | 스위치 off일 때 현행 출력과 동일 | 기존 테스트 전량 |

P0-5 대비 기대치는 적지 않는다. 설계 결정 전이라 근거가 없다.

## 7. 알려진 위험

| 위험 | 근거 |
|---|---|
| 모델의 ID·구간 복사 능력의 표본이 3건뿐이다 | P9 실모델 결과(`GS-P09-REAL-MODEL-RUN-RESULTS.md`) |
| 지연 증가(추출 호출 추가, 버퍼 대기) | P0-5 생성 중앙값 약 80초 |
| 정확 일치의 거짓 음성 | ③ 3.2절(H2 쪽 머리글 사례) |
| A·B를 통과해도 C 실패는 그대로다 | P0-5의 주 실패 유형(D1·C1·C2)은 근거 ID가 맞는 근거 밖 진술 |
| 착지 전 병합 비용이 계속 커진다 | main 고유 커밋 82 → 91 |
| 교단 지시문 근거 ADR이 Proposed다 | ADR-009 Amendment A |

## 8. HQ 결정이 필요한 순서

1. ④ 계약 5항목(4-1~4-5) — 새 ADR의 내용이 된다.
2. FU-007 번역 방식(P-4) — Phase 0의 전제다.
3. 새 ADR 작성 지시(P-1) — 이 자료와 ④ 브리프를 입력으로 삼는다.

## 9. MUTATION

- 코드·ADR·prompt 변경 없음. 이 문서의 커밋·푸시만 수행한다.
