# DBMA 고처리량 통합 — Baseline 측정

**측정일**: 2026-09-07T15:30:00KST

## 시스템
- RAM: 128.0GB
- CPUs: 18

## Ollama 서버
- parallel (-np): **1** (기본값, 변경 안됨)
- 모델: bge-m3 (임베딩), my-theology-bot-v2 (Claim 추출)
- 포트: 56707

## 임베딩 측정

| n (텍스트 수) | single(s) | batch(s) | speedup |
|---------------|-----------|----------|---------|
| 8 | 0.24 | 0.23 | 1.02x |
| 16 | 0.42 | 0.29 | **1.41x** |
| 32 | 0.74 | 0.61 | 1.21x |

## Claim 추출 측정 (참고)
- 1건당 소요시간: ~11.5s
- `-np 1`이므로 동시 요청은 서버에서 큐잉됨 → speedup ≈ 1.0x

## 게이트 판정

| Phase | 게이트 기준 | 실제 측정 | 판정 |
|-------|------------|-----------|------|
| Phase 2 (임베딩 배치) | >=2x speedup | 1.41x (n=16 최대) | ⚠️ **미달** |
| Phase 3 (Claim 동시) | >=1.5x (-np>=2) / >=1.2x (-np=1) | ~1.0x (-np=1) | ❌ **폐기** |

## 분석

### 임베딩 배치 speedup이 낮은 이유
1. Ollama 서버가 `-np 1`로 설정되어 있어 배치 입력도 순차 처리
2. 배치 API의 JSON 직렬화 오버헤드가 네트워크 절약 이득 상쇄
3. 실제 이득은 서버 `-np >= 2`일 때 나타남 (GPU 병렬 처리 활용)

### Claim 추출 동시성 폐기 이유
1. `-np 1`에서 ThreadPoolExecutor 동시 요청은 서버 큐잉만 유발
2. LLM generation time (~11.5s/건) 이 실제 bottleneck
3. speedup 개선 없음 → Phase 3 폐기

## 결론

### 진행: Phase 2 (임베딩 배치) — 조건부
- speedup 게이트 미달이지만 **향후 서버 `-np` 증가 시 이득 예상**
- additive 확장으로 아키텍처 변경 없음 → **보류 유지**
- `max_workers=1` 기본값으로 현행 동작 완전 보존

### 폐기: Phase 3 (Claim 동시), Phase 4 (CLI 병렬 옵션)
- `-np 1` 환경에서 개선 없음
- 서버 `-np >= 2`로 변경 후 재측정 필요

## 다음 단계
1. `embed/client.py`에 `embed_texts_batch()` 추가 완료 (이미 구현됨)
2. `builder.py`에 `max_workers=1` kwarg 추가 (현행 보존)
3. `runner.py`에 `--max-workers` 추가 (기본 1)
4. 서버 `-np` 변경 후 재측정 → speedup >=2x 이면 배치 활성화
