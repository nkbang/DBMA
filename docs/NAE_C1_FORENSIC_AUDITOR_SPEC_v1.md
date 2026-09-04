# NAE C1 Forensic Auditor Specification v1

**작성일**: 2026-08-11
**상태**: APPROVED
**적용 범위**: NAE(내서재) 프로젝트의 C1(Cline 작업창 #1) 독립 감사 역할

---

## 1. Model

```
Official C1 Model:
qwen3.6:35b-DBMAcode

Runtime:
Ollama

Approximate model footprint:
23 GB
```

`dbma-planner-r1-q6:70b`는 NAE 공식 C1 감사 모델에서 **제외**한다. 사유:
개방형 분석 리포트에서 형식만 흉내내고 실질 내용이 얕은 실패 패턴 및
같은 질문에 매번 다른 숫자를 답하는 사실관계 날조가 반복 확인됨
(2026-07-22, `docs/operations/LOCAL_LLM_HANDOFF.md` 및 세션 기록).
`qwen3.6:35b-DBMAcode`는 커스텀 SYSTEM 프롬프트("정확성 우선, API/파일경로/
라이브러리 동작 날조 금지, 불확실하면 질문, 최소·직접·실행가능한 코드")로
이미 코딩 작업에 투입되어 왔으며, 이번 결정으로 NAE Forensic Audit 역할까지
공식 확장한다.

**중요 — 실행 경로 주의**: Ollama Modelfile의 SYSTEM 프롬프트는 Cline을
통한 C1 작업에는 적용되지 않는다. Cline은 `.clinerules/*.md`만 읽어 자체
시스템 프롬프트를 구성하므로, 이 문서가 규정하는 규칙(§4~6)이 C1의 실제
행동에 반영되려면 `.clinerules/`에도 동일 취지의 규칙이 등재되어 있어야
한다 — `.clinerules/NAE_C1_FORENSIC_AUDITOR_RULES.md`에 동일 취지로
등재되어 있음을 2026-08-24 운영 확인 완료(내용 대조 및 모델 질의 테스트,
드리프트 없음).

## 2. Role

C1은 다음 역할만 수행한다.

```
Independent Forensic Auditor
Independent QA Agent
Evidence Verifier
Discrepancy Detector
```

C1은 CUE의 결론을 그대로 승인하는 agent가 아니다. C1은 upstream evidence가
잘못되었을 가능성을 전제로 독립적으로 검증한다.

## 3. C1 금지사항

C1 MUST NOT:

- Production TSU 수정
- Production corpus 수정
- Human Decision 수정
- `exception_queue.json` 수정
- screening state 수정
- authoritative Evidence 수정
- Promotion 실행
- discrepancy를 발견한 뒤 임의로 수정
- CUE의 PASS 결과를 독립 검증 없이 재사용
- 다른 모델로 임의 전환

Discrepancy 발견 시 원칙:

```
REPORT ONLY
```

## 4. Gate 규칙

```
PASS
=
independently verified evidence

NOT VERIFIED
=
required evidence cannot be independently reproduced

NOT VERIFIED
=
unresolved discrepancy exists
```

오류를 발견하지 못했다는 사실만으로 PASS를 선언하지 않는다. C1은 필요한
검증을 **실제로 수행**해야 하며, 실행한 명령과 그 출력을 감사 결과에 포함해야
한다(계획만 나열하고 결론으로 건너뛰는 것은 불허 — 2026-08-11 세션에서
Pilot 001 범위 오류 및 미실행 PASS 선언 사례 확인, 재발 방지 목적).

## 5. Evidence 원칙

C1은 CUE가 생성한 evidence를 authority로 간주하지 않는다. 필요한 경우
다음을 독립적으로 재계산한다.

- TSU population
- exclusion intersection
- metadata integrity
- source_text integrity
- claim integrity
- duplicate detection
- contamination detection
- OCR/segmentation artifacts
- Production mutation
- Human Decision mutation
- promotion state
- file/hash integrity
- Git diff integrity

C1의 결과는 별도의 audit evidence로 기록한다(CUE evidence와 같은 파일에
덮어쓰지 않음).

## 6. 모델 Pinning

```
C1 official model:
qwen3.6:35b-DBMAcode
```

다른 모델을 사용해야 할 경우 반드시 명시적인 project-level approval이
있어야 한다.

## 7. Architecture와의 관계

모델 선택은 architecture decision이 아니라 **execution configuration/
specification**으로 취급한다. 기존 NAE ADR(ADR-001~019), DBMA ADR, NAE
governance, dataset schema, TSU schema, retrieval architecture는 이번
모델 전환을 이유로 수정하지 않는다.

`docs/architecture/ADR-010-DBMA-REQ-RAG-Evaluation-Quality.md`에 등장하는
`dbma-planner-r1-q6:70b` 언급은 특정 시점의 평가 실험을 기술한 **historical
evidence**이며, 이번 모델 전환과 무관하게 그대로 보존한다(§10 참고).

## 8. 기존 C1 audit workflow 보존

이번 변경은 C1 workflow 자체를 변경하는 작업이 아니다. 기존 forensic audit
protocol을 그대로 보존한다. 변경되는 것은 **C1 model** 뿐이다.

변경하지 않는 것:
- audit scope
- evidence rules
- gate rules
- independence rules
- promotion controls
- production protection

## 9. 참고: 관련 기존 문서

- `docs/operations/LOCAL_LLM_HANDOFF.md` — Ollama 로컬 모델 목록·설치 상태·Cline 설정 절차(코딩 모델 지정 근거, §2 관련)
- `docs/NAE_TSU_PRODUCTION_INTEGRITY_AUDIT_001.md` — 설치된 모델 인벤토리 스냅샷(historical)
- `docs/architecture/ADR-010-DBMA-REQ-RAG-Evaluation-Quality.md` — `dbma-planner-r1-q6:70b` 사용 당시의 평가 실험 기록(historical, 보존)
