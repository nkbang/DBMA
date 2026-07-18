# DBMA Local LLM Handoff Guide

## 0. 목적

Claude(원격, 토큰 과금) 기반 CUE 작업 방식을 **로컬 Ollama 모델 기반 작업**으로
전환하기 위한 실행 가이드다. 토큰 소진/예산 제약 상황에서 개발 작업을 중단하지
않고 로컬 자원으로 이어가는 것이 목적이다.

이 문서는 다음을 포함한다:
1. 지금까지의 CUE 작업 방식 요약(로컬 모델이 재현해야 할 패턴)
2. 로컬 모델 현황과 용도별 추천
3. Cline(VSCode 확장) → Ollama 연동 설정
4. CUE 워크플로우를 로컬 환경 제약에 맞게 축소한 버전
5. **컨텍스트 핸드오프** — 로컬 모델이 알아야 할 DBMA 현재 상태 요약
6. 한계와 주의사항

---

## 1. 지금까지의 작업 방식 (CUE 패턴)

이 세션 전체에서 반복된 루프:

```
Preflight (조사만, 코드 변경 금지)
      ↓
Design (옵션 비교 → 승인)
      ↓
Implementation (최소 변경)
      ↓
Verification (테스트 + 실측 재현, 격리 tmp 우선)
      ↓
commit → push (사용자 승인 후에만)
```

핵심 원칙(CLAUDE.md와 일치):
- 한 파일/한 함수 단위로 최소 변경
- 코드 변경 전 조사·설계를 먼저 문서화
- 변경 후 반드시 실행 검증(pytest + 실측)
- 실 production 데이터를 건드릴 땐 사전 백업
- 커밋 메시지에 "왜"를 남김(무엇을 했는지는 diff가 말해줌)

**로컬 모델로 이관할 때 이 루프 자체를 반드시 유지해야 한다** — 로컬 모델은
Claude보다 추론 깊이가 얕고 컨텍스트 유지력이 약하므로, 오히려 이 루프의
"최소 변경 + 즉시 검증" 원칙이 실패 시 피해를 줄이는 안전장치로 더 중요해진다.

---

## 2. 로컬 모델 현황 (`ollama list` 기준) 및 용도별 추천

| 모델 | 크기 | 용도 추천 |
|---|---|---|
| **`qwen3.6:35b-DBMAcode`** | 23GB | **1순위 — 이미 DBMA 전용으로 준비된 코딩 모델.** Cline의 기본 코딩 모델로 우선 사용 |
| `qwen3-coder:30b` | 18GB | 2순위 — 범용 코딩 특화, DBMAcode보다 가벼움(속도 우선 시) |
| `qwen2.5-coder:32b-instruct-q8_0` | 34GB | 3순위 — 고정밀 필요 시(품질 우선, 속도 희생) |
| `codestral:latest` | 12GB | 빠른 단건 수정/자동완성용, 큰 설계 판단엔 부적합 |
| `qwen3.6:35b` / `qwen3.6:latest` | 23GB | 코딩 외 일반 추론(Preflight 조사 요약 등)에 사용 가능 |
| `deepseek-r1:70b` | 42GB | 복잡한 아키텍처 판단(느림, reasoning 특화) — Design 단계 검토용 |
| `my-theology-bot:latest` | 42GB | **DBMA의 generation 경로 전용(core/generation.py) — 코딩 작업에 쓰지 말 것** |
| `bge-m3:latest` | 1.2GB | embedding 전용(core/embedder.py) — 코딩 작업과 무관 |

**결론: Cline의 기본 모델은 `qwen3.6:35b-DBMAcode`로 설정.** 속도 문제 시
`qwen3-coder:30b`로 전환.

---

## 3. Cline → Ollama 연동 설정

VSCode에서 Cline 확장 설치 후:

1. Cline 설정 패널(⚙️) 열기
2. API Provider: **Ollama** 선택
3. Base URL: `http://localhost:11434`
4. Model: `qwen3.6:35b-DBMAcode` 입력(드롭다운에 없으면 직접 타이핑)
5. Context window: 모델이 지원하는 최대치로 설정(qwen3.6 계열은 통상 32K~128K,
   실제 한도는 `ollama show qwen3.6:35b-DBMAcode`로 확인)

확인 명령:
```bash
ollama show qwen3.6:35b-DBMAcode
curl http://127.0.0.1:11434/api/tags   # Ollama 서버 살아있는지 확인
```

---

## 4. CUE 워크플로우 → Cline 제약 맞춤 축소판

CLAUDE.md에 이미 명시된 "Cline 사용 규칙"을 그대로 따르되, 이번 문서에서 구체화:

```
❌ 하지 말 것 (Claude 세션에서는 가능했지만 로컬 모델엔 위험):
- 여러 파일 동시 수정
- "알아서 판단해서 고쳐줘" 식의 광범위 요청
- Preflight 없이 바로 구현 요청
- 대규모 리팩터링

✅ 로컬 모델에 적합한 작업 단위:
- 이미 설계가 끝난 상태에서 "이 함수 하나만" 구현
- 명확한 diff 스펙이 있는 버그 수정
- 기존 패턴을 그대로 복제하는 반복 작업(예: 새 테스트 파일 추가)
```

### 4.1 로컬 모델용 프롬프트 템플릿 (CLAUDE.md 기존 템플릿 확장)

```text
너는 DBMA 프로젝트의 코드 보조자다.
프로젝트 루트는 /Users/David/DBMA 이다.
공식 Python 실행 환경은 ~/envs/dbma311 이다(다른 venv 사용 금지).

작업 원칙:
- 한 번에 하나의 파일 또는 하나의 함수만 다룬다.
- 관련 없는 파일은 수정하지 않는다.
- 기존 구조를 최대한 유지한다.
- 추측하지 말고, 필요한 정보가 부족하면 먼저 질문한다.
- 변경 전과 변경 후를 짧게 요약한다.

현재 작업:
- 대상 파일: {파일 경로}
- 대상 함수: {함수명}
- 목표: {구체적 목표, 이미 설계 완료된 내용만}

작업 후 반드시:
1. ~/envs/dbma311/bin/python -m pytest tests/ -q 실행 결과 보고
2. git diff 보고
3. commit/push는 사용자 승인 후에만
```

### 4.2 검증은 로컬 모델에게 맡기지 말 것

로컬 모델이 "테스트 통과했다"고 말해도 **반드시 사람이 직접**:
```bash
source ~/envs/dbma311/bin/activate
cd ~/DBMA
python -m pytest tests/ -q
git diff --stat
```
을 실행해 재확인한다. 로컬 모델의 자체 보고를 그대로 신뢰하지 않는다(이건 Claude
세션에서도 지켜온 원칙 — "verify" 스킬 — 이지만 로컬 모델에서는 신뢰도가 더
낮으므로 특히 중요).

---

## 5. 컨텍스트 핸드오프 — DBMA 현재 상태 요약

로컬 모델은 이 세션의 대화 이력을 모른다. 새 세션/새 모델 시작 시 아래 내용을
프롬프트에 붙여넣거나 CLAUDE.md에 이미 있는 내용과 함께 제공한다.

### 5.1 버전/브랜치 상태
```
버전: v1.3.0 (Architecture Consolidation Release)
브랜치: dev/dbma-engine
최근 완료 스프린트: SPRINT25-C (운영 검증 완료, 신규 gap 없음)
Working tree: clean
전체 테스트: 312 passed
```

### 5.2 확정된 Authority 구조 (이 경계를 넘는 수정은 반드시 사람 승인)
```
Processing   → core/processing.py
Identity     → core/identity_registry.py, core/document_identity.py
Index        → core/index_orchestrator.py
TSU 생성      → core/tsu_builder.py
Retrieval    → core/retrieval.py
Embedding    → core/embedder.py (BGE-M3 / Ollama / 1024차원)
Generation   → core/generation.py
UI 진입점     → dbma_ui.py → ui/app.py → ui/pages/*
Legacy(격리)  → archive/legacy/ (dbma.py 등, 공식 경로 무관)
```

### 5.3 핵심 데이터 흐름
```
data/RAW/{file}
  → core/processing.py::process_batch()/process_one_file()
  → data/제련완성본/registry/documents.json (Identity, SoT)
  → core/index_orchestrator.py::reconcile_pending() (자동 연결됨, SPRINT21-F-1)
  → output/bench/tsu_dataset.jsonl (TSU, 검색 대상)
  → core/retrieval.py::RetrievalEngine (BM25 + BGE-M3 하이브리드, 벡터DB 비의존)
```

### 5.4 절대 침범 금지 원칙 (여러 스프린트에서 반복 확정됨)
- `document_id`/`file_hash`는 순수 content-hash 기반(파일명 무관) — 이 생성
  로직 변경 금지(정체성 모델 전체 붕괴 위험).
- `pipeline_state`(NEW~INDEXED)와 `ingest_status`(PROCESSED/FAILED/ABANDONED)는
  **서로 독립** — 절대 하나가 다른 하나의 의미를 침범하면 안 됨.
- `core/extraction_failures.py`(pre-identity 실패 로그)와 `documents.json`은
  **의도적으로 분리**되어 있음 — 두 파일을 하나로 합치지 말 것.
- Retrieval은 Chroma/Qdrant를 쓰지 않음(레거시만 사용, `archive/legacy/`) —
  벡터DB를 다시 끌어들이는 방향으로 되돌리지 말 것.
- 실행 환경은 `~/envs/dbma311` 고정. 다른 venv(`.venv_311` 등) 사용 금지.

### 5.5 최근 완료된 작업(SPRINT21~25) 요약
```
SPRINT21-B/D/F/G  : pipeline_state 도입, Processing→TSU 자동연결, tsu_id 충돌 수정,
                    document supersession(동일 파일명 내용변경 시 이력 연결)
SPRINT22-A        : Drag & Drop 업로드 + 지원형식 4→7종 확장
SPRINT23          : 실패 이력 UI 노출
SPRINT24-1/24-2   : 재시도 대상 표시, source provenance(버전+실패 이력 join) UI
SPRINT25-B-1/B-2  : 예외 타입(error_type) 캡처 + UI 라벨 분류
SPRINT25-C        : force_reingest 안내 문구 수정, 실 데이터 운영 검증 완료
```

### 5.6 알려진 백로그(신규 스프린트 후보, 미착수)
```
- Library 페이지의 SUPPORTED_EXTENSIONS(5종, 구버전) vs Processing의
  SUPPORTED_EXTS(8종) — 동일 drift 문제, Library 쪽 미수정
- source_file 오탐 위험(무관 문서가 우연히 같은 파일명일 때) — 설계 한계로 인지됨
- Revert(옛 버전 복원) 미지원 — 의도된 설계 한계
- .batch_state.json 3중 독립 파싱 구조 — 정리 후보(낮은 우선순위)
```

---

## 6. 한계 및 주의사항

1. **컨텍스트 윈도우:** 로컬 모델은 이 대화 전체(수십 개 스프린트)를 모른다.
   §5의 요약만으로 판단하게 하고, 애매하면 반드시 질문하도록 프롬프트에 명시.
2. **추론 깊이:** `qwen3.6:35b-DBMAcode`는 Claude Opus 대비 다단계 아키텍처
   판단(예: SPRINT24-2의 provenance 설계처럼 여러 옵션을 비교하는 작업)에서
   품질이 떨어질 수 있음. **이런 설계 판단은 가능하면 사람이 직접 하거나, 토큰
   여유가 생겼을 때 Claude로 재확인**.
3. **환경 혼동 위험:** 로컬 모델은 `.venv`, `.venv_311`, `~/envs/dbma311`을
   구분 못 하고 아무거나 쓸 수 있다 — 프롬프트에 실행 환경을 매번 명시.
4. **destructive 작업:** `git push --force`, `git reset --hard`, registry/TSU
   직접 삭제 등은 로컬 모델에게 절대 위임하지 말 것 — 사람이 직접 실행.
5. **검증 없는 "완료" 보고 불신:** 4.2절 참고.

---

## 7. 전환 체크리스트

```
[ ] Ollama 서버 기동 확인 (curl 127.0.0.1:11434/api/tags)
[ ] Cline 확장 설치 + Ollama provider 연결 확인
[ ] 모델 qwen3.6:35b-DBMAcode 선택 확인
[ ] 이 문서(§5)를 새 세션 시작 프롬프트에 포함
[ ] 첫 작업은 반드시 "작은 단일 파일 수정"으로 시작해 로컬 모델 신뢰도 확인
[ ] 매 작업 후 사람이 직접 pytest + git diff 확인
[ ] commit/push는 사람 승인 후에만
```
