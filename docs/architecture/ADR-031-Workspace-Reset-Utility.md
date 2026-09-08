---
title: "ADR-031: Workspace Reset Utility (Pre-Deployment Tuning Reset)"
category: governance + tooling
based_on:
  - docs/architecture/ADR-013-NAE-Vector-Store.md
  - docs/architecture/ADR-021-NAE-Source-Registration-Raw-Preservation-Extraction.md
  - docs/architecture/ADR-025-NAE-TSU-Extraction-Queue-Worker.md
  - docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md
  - CLAUDE.md (CUE Operating Policy v1.0 — Architecture Freeze / RAW·Corpus 변경 금지)
created: 2026-09-07
scope_modified: scripts/reset_workspace.py (신규), config.yaml (reset 그룹 선언 추가), ui/ 유지보수 액션 (신규)
---

# ADR-031: Workspace Reset Utility (Pre-Deployment Tuning Reset)

| | |
|---|---|
| **Status** | **PROPOSED (v1 — Open Questions resolved 2026-09-07)** |
| **Date** | 2026-09-07 |
| **Approved** | — |
| **Approver** | Rev. Bang / HQ (예정) |
| **Deciders** | 사용자 (HQ), CUE (초안), C1 (독립 리뷰 예정) |
| **Supersedes** | — |
| **Does NOT supersede** | ADR-013, ADR-021, ADR-025, ADR-030 (본 ADR은 이들이 보호하는 자산을 삭제 대상에서 제외한다) |

> **Evidence Before Promotion**: 이 문서는 Proposed 상태다. 구현 완료 · 회귀 테스트 통과 ·
> C1 독립 리뷰 · 사용자 승인 4개 조건을 모두 충족하기 전까지 Approved ADR의 근거로 사용하지 않는다.

---

## 1. Context

### 1.1 문제

배포 전 단계에서 각 기능(추출·정제·청킹·임베딩·검색·생성·평가)을 세세히 분석·조정·수정하는
반복 루프가 필요하다. 이 루프의 각 사이클은 **깨끗한 시작 상태**를 요구한다:

```text
파생물 삭제 → 튜닝된 설정 적용 → 파이프라인 재실행 → 결과 비교 → 재조정 → 반복
```

현재는 이 리셋을 매번 수동 `rm`으로 수행해야 한다. 이 방식의 위험:

1. **범위 오염** — 삭제 대상이 아닌 경로를 함께 지움. (메모리 기록: 테스트 경로 오염 사고 4회,
   `feedback_test_fixture_path_overrides`)
2. **RAW/소스 유실 위험** — `data/RAW/` (2.9G, 주석서 PDF 72개), `NAE/corpus/raw/` (894M,
   재취득 어렵거나 불가한 취득 소스)를 실수로 삭제하면 되돌릴 수 없다.
3. **거버넌스 위반 위험** — git 추적되는 NAE corpus baseline (ADR-030 FROZEN,
   `NAE/corpus/canonical/SLBC1689·PBC1765`, `NAE/corpus/tsu/Dagg_Church_Order` 등)을
   무심코 삭제하면 Architecture Freeze Rule 위반.
4. **추적 불가** — 무엇을 언제 왜 지웠는지 기록이 남지 않음. 프로젝트 원칙("작업은 반드시
   추적 가능해야 한다")과 배치됨.

### 1.3 기존 자산 — `scripts/reset_for_beta.py`

이미 베타 배포용 전체 초기화 스크립트가 존재한다. 특징:

- 대상: `data/RAW/` + `{output_dir}` + `chroma_db/` + TSU dataset/manifest 파일
- dry-run 기본, `--execute` 시 `backups/pre_beta_reset_<YYYYMMDD>/`로 전체 복사 후 삭제
- registry는 삭제 대신 빈 스키마로 재생성

**한계** (ADR-031이 보완하는 지점):

| 없는 것 | 결과 |
|---|---|
| 티어 구분 | RAW 포함 전체 삭제만 가능 — 튜닝 루프에 과함 |
| Protected Paths / git 추적 가드 | 추적 baseline·소스 삭제 방지 장치 없음 |
| 삭제 매니페스트 (JSON) | 무엇이 어디로 이동했는지 기계 판독 기록 없음 |
| Qdrant 컬렉션 처리 | Qdrant(현 primary) 미대응 — chroma만 |
| 휴지통 이동 후 완전삭제 옵션 | `backups/`가 무한 증가 |

ADR-031은 `reset_for_beta.py`를 **T3의 특수 사례**로 흡수한다. 구현 시
`reset_for_beta.py`는 `reset_workspace.py --tier T3 --include-raw`의 얇은
wrapper로 남기거나 deprecate 표시한다 (§7에서 결정).

### 1.2 현재 워크스페이스 실측 (2026-09-07)

| 분류 | 경로 | 크기 | git 추적 | 재생성 |
|---|---|---|---|---|
| **RAW/소스** | `data/RAW/` | 2.9G | 아니오 (gitignore) | 재취득 필요 |
| RAW/소스 | `NAE/corpus/raw/` | 894M | 아니오 (gitignore) | 재취득 필요, 일부 불가 |
| RAW/소스 | `NAE/corpus/canonical/` | 108M | **일부 예** | 재취득+재정규화 |
| RAW/소스 | `NAE/corpus/quarantine/` | 12M | **예** (원본 PDF) | 재취득 필요 |
| RAW/소스 | `data/bible/` | 4.9M | 확인 필요 | 재취득 필요 |
| RAW/소스 | `sermon_corpus/`, `data/sermon_corpus/`, `data/beta_corpus/` | ~170M | 확인 필요 | 재취득 필요 |
| **파생물** | `output/` | 7.7G | 아니오 | 파이프라인 재실행 |
| 파생물 | `NAE/corpus/embeddings/` | 1.1G | `.gitkeep`만 | 임베딩 재실행 |
| 파생물 | `NAE/corpus/tsu/` | 326M | **일부 예** (Dagg 등) | TSU 재추출 |
| 파생물 | `data/제련완성본/` | 201M | 확인 필요 | 추출·청킹 재실행 (단, 소스 PDF 사본 포함 — §4.3) |
| 파생물 | `chroma_db/` | 69M | 아니오 | 재인덱싱 |
| 파생물 | `cache/` | 555M | 아니오 | 자동 재생성 |
| 파생물 | `NAE/corpus/quarantine/` 제외 `reports/`, `manifests/`, `evidence/`, `NAE/benchmark/` | 소량 | 일부 `.gitkeep` | 재실행 |
| 파생물 | `data/normalized/`, `data/processed/`, `data/nae/`, `data/inbox/` | ~0B | 확인 필요 | 재실행 |
| **외부** | Qdrant 컬렉션 (`nae_bible_v1`, `nae_ref_v1`, ADR-013) | — | — | 재임베딩 |
| **백업** | `backups/` | 15G | 아니오 (gitignore) | 불가 |

---

## 2. Decision

### 2.1 티어드 리셋 유틸리티 도입

`scripts/reset_workspace.py` — CLI 우선 단일 진입점. 경로 그룹은 `config.yaml`의
`reset:` 섹션에 선언(하드코딩 금지). UI 유지보수 탭에 동일 로직을 호출하는 버튼 추가.

**all-or-nothing 리셋은 제공하지 않는다.** 리셋은 아래 3개 티어로만 수행한다.

| Tier | 이름 | 삭제 대상 | 구현 | 기본값 |
|---|---|---|---|---|
| **T1** | Derived Artifacts | `output/` (단 `output/SPRINT*` 감사 산출물 제외 옵션), `chroma_db/`, `cache/`, `NAE/corpus/embeddings/` 내용물, `data/제련완성본/`의 `*_pdf.md`·`*_chunks.txt`·`*_chunks_meta.json`, `data/normalized`·`processed`·`nae`·`inbox` 내용물, `reports/`, `evidence/` (비추적분) | **이번 범위** | 활성 |
| **T2** | + Intermediate Corpus | T1 + `NAE/corpus/tsu/` (비추적분), `NAE/corpus/manifests/` (비추적분), `NAE/corpus/quarantine/` (비추적분), `NAE/benchmark/` 산출물, **Qdrant 컬렉션 drop** (`--drop-qdrant` 명시 시) | **이번 범위** | 비활성 (명시 플래그) |
| **T3** | + RAW / Source | T2 + `data/RAW/`, `NAE/corpus/raw/`, `data/bible/`, `sermon_corpus/`, `data/*_corpus/` | **설계만 — 구현하지 않음 (HQ 결정 2026-09-07)** | — |

**T3 결정 근거**: 배포 전 튜닝은 RAW 재취득 없이 파생물 재생성만으로 충분하다.
RAW 삭제 능력을 코드로 노출하면 사고 표면만 넓어진다. T3는 이 문서에 설계로만
남기고, 필요 시 별도 승인 후 `reset_for_beta.py` 경로로 처리한다.

### 2.2 Protected Paths — 어떤 티어에서도 삭제 불가

다음은 리셋 유틸리티가 **무조건 거부**한다 (T3 포함):

```text
1. .git/, .git 워크트리 메타데이터
2. git 추적 중인 모든 파일 (git ls-files 로 판정) — 삭제하려면 별도 커밋이
   필요하며 이는 리셋 유틸리티의 범위가 아니다
3. 소스 코드 디렉터리: core/, ui/, scripts/, tests/, NAE/pipeline/, NAE/authority/,
   NAE/governance/, docs/
4. 설정/환경: config.yaml, .env, requirements*.txt, Modelfile, .venv*/, dbma_env/
5. ADR-021 raw preservation 대상 중 git 추적분
6. ADR-030 FROZEN baseline: NAE/corpus/canonical/{SLBC1689,PBC1765,PBC1765,...}
   중 git 추적 파일, NAE/corpus/tsu/*/tsu.json 중 git 추적 파일
7. NAE/pipeline/tsu/worker/ 의 state 파일이 아닌 소스 (ADR-025)
```

T3에서 RAW를 지우더라도, 위 목록에 걸리는 파일은 건너뛰고 매니페스트에 `SKIPPED (protected)`로 기록한다.

### 2.3 안전 장치 (모든 티어 공통)

| # | 장치 | 동작 |
|---|---|---|
| 1 | **Dry-run 기본** | 인자 없이 실행하면 삭제 목록 + 경로별 용량 + 합계만 출력. 실제 삭제는 `--apply` 필요 |
| 2 | **확인 문구** | `--apply` 시 정확한 문구 입력 요구 (T1/T2: `RESET <tier>`, T3: `RESET T3` + `DELETE RAW SOURCES` 2단계) |
| 3 | **휴지통 이동 우선** | hard `rm` 대신 `backups/reset_<UTC-timestamp>/<원경로>` 로 이동. `--hard` 명시 시에만 완전 삭제 |
| 4 | **삭제 매니페스트** | `backups/reset_<ts>/manifest.json` — {tier, timestamp, git_branch, git_head, moved:[{src,dest,bytes}], skipped_protected:[...], qdrant_dropped:[...]} |
| 5 | **브랜치/클린 트리 가드** | 추적 파일에 uncommitted 변경이 있으면 중단 (`--force` 로만 우회). 예상 브랜치 목록 밖이면 경고 |
| 6 | **Qdrant는 opt-in** | 컬렉션 drop은 T2+ 그리고 `--drop-qdrant` 동시 충족 시에만. ADR-013 격리 규칙 준수 — 지정 컬렉션만, 프리픽스 화이트리스트 검증 |
| 7 | **로그** | 프로젝트 로그 규칙 준수: `[reset] tier=T1 dry-run` / `[reset] moved 74 paths 3.3G → backups/reset_20260907T...` / `[reset] skipped 12 protected` |

### 2.4 config.yaml 선언 형식 (예시)

```yaml
reset:
  protected_prefixes:
    - .git
    - core/
    - ui/
    - scripts/
    - tests/
    - docs/
    - config.yaml
  tiers:
    T1:
      - output/
      - chroma_db/
      - cache/
      - NAE/corpus/embeddings/*
      - data/제련완성본/*_pdf.md
      - data/제련완성본/*_chunks.txt
      - data/제련완성본/*_chunks_meta.json
      - data/normalized/*
      - data/processed/*
    T2:
      - NAE/corpus/tsu/*
      - NAE/corpus/manifests/*
      - NAE/corpus/quarantine/*
      - NAE/benchmark/*
    T3:
      - data/RAW/*
      - NAE/corpus/raw/*
      - data/bible/*
      - sermon_corpus/*
  qdrant_collection_whitelist:
    - nae_bible_v1
    - nae_ref_v1
```

---

## 3. Consequences

### 3.1 Positive

- 반복 튜닝 루프의 리셋이 재현 가능·추적 가능해진다 (매니페스트 + 로그).
- RAW/소스와 git baseline이 구조적으로 보호된다 (Protected Paths, 기본 티어에서 제외).
- 휴지통 이동 기본값으로 리셋 실수를 `backups/reset_<ts>/` 에서 복구 가능.
- 사용자가 UI에서 직접 리셋 → CUE/C1 개입 없이 튜닝 사이클 반복 가능.

### 3.2 Negative

- 신규 모듈 + config 스키마 확장 + UI 액션 추가.
- `backups/` 증가 (리셋마다 스냅샷). → `--hard` 옵션 및 오래된 `reset_*` 정리 명령 제공.
- `data/제련완성본/` 이 소스 PDF 사본과 파생물을 한 디렉터리에 혼재 → §4.3 확인 필요.

### 3.3 Neutral

- Qdrant drop은 기본 비활성 → ADR-013 격리 규칙과 충돌하지 않음.
- 기존 파이프라인 코드 변경 없음 (리셋은 파일시스템/컬렉션 레벨에서만 동작).

---

## 4. Resolved Decisions (2026-09-07)

### 4.1 RAW/소스 삭제 (T3) — **구현하지 않음**

HQ 결정: T1/T2만 구현. T3는 §2.1에 설계로만 남긴다. (근거: §2.1 표 하단)

### 4.2 git 추적 baseline — **리셋 범위 밖 확정**

리셋 유틸리티는 `git ls-files` 로 판정되는 추적 파일을 어떤 티어에서도 삭제하지
않는다. 추적된 corpus baseline(ADR-030 FROZEN)을 실제로 비우려면 ADR-030
Amendment + 별도 커밋 절차가 선행되어야 하며, 이는 본 유틸리티의 책임이 아니다.
Protected Paths(§2.2)가 이를 코드로 강제한다.

### 4.3 `data/제련완성본/` 혼재 — **파생 확장자만 삭제, `.pdf` 보존**

T1은 이 디렉터리에서 `*_pdf.md`, `*_chunks.txt`, `*_chunks_meta.json`,
`*_pdf_chunks*.json` 패턴만 삭제한다. `.pdf`(소스 사본)와 그 외 확장자는 보존한다.
`config.yaml`의 `reset.tiers.T1` glob으로 명시하며, 디렉터리 통삭제는 금지한다.

### 4.4 Qdrant 컬렉션 화이트리스트 — **config 선언 + 명시 플래그, 기본 빈 목록**

- 실측 컬렉션명: `dbma_sermon`, `dbma_chunks` (config `vector_db.qdrant.collections`),
  `nae_tsu_v1` (config `nae.index_collection`), `nae_bible_v1`, `nae_ref_v1` (운영 인덱스).
- `config.yaml`의 `reset.qdrant_collection_whitelist` 에 나열된 컬렉션만 drop 가능.
- **기본값은 빈 목록** — 화이트리스트를 채우고 `--drop-qdrant` 를 동시에 줘야 실제 drop.
- drop 전 대상 컬렉션명이 화이트리스트에 정확히 포함되는지 재검증(부분 일치 금지),
  drop한 컬렉션은 매니페스트 `qdrant_dropped` 에 기록.
- ADR-013 격리: `url` 은 config 값(`http://localhost:6333`)만 사용, NAE 인스턴스
  (7333)에는 접속하지 않는다.

### 4.5 UI 노출 범위 — **T1만 노출**

UI 유지보수 버튼은 T1 dry-run → 확인 → apply 흐름만 제공한다. T2(중간 코퍼스 +
Qdrant drop)와 T3는 CLI 전용. UI에서 삭제 대상 목록과 용량, 이동될
`backups/reset_<ts>/` 경로를 먼저 보여준 뒤 실행한다.

---

## 5. Governance

| 항목 | 관계 |
|---|---|
| ADR-013 (Vector Store 격리) | Qdrant drop은 화이트리스트 컬렉션만, 기본 비활성. 격리 규칙 유지. |
| ADR-021 (Raw Preservation) | RAW는 기본 티어에서 제외. T3에서도 git 추적 raw는 Protected. |
| ADR-025 (TSU Worker) | worker state 파일(`worker_state*.json` 등)은 T2에서 삭제 가능(gitignore·런타임 상태). worker 소스는 Protected. |
| ADR-030 (Sermon Corpus FROZEN) | git 추적 canonical/tsu baseline은 Protected. 리셋이 FROZEN baseline을 변경하지 않음. |
| CLAUDE.md Architecture Freeze | 본 ADR은 신규 유틸리티 추가일 뿐 기존 ADR 규칙을 변경하지 않는다. |
| CLAUDE.md "RAW·Corpus 명령 없이 변경 금지" | 리셋 유틸리티 자체가 이 규칙의 집행 장치(Protected Paths)로 동작. |

**C1 Review 필요 시점**: 이 ADR은 신규 유틸리티 + Migration 성격(Qdrant drop, corpus 삭제 능력)이
있으므로 CLAUDE.md 기준 C1 독립 리뷰 대상이다.

---

## 6. Promotion Criteria (Proposed → Approved)

아래 4개를 **모두** 충족해야 Approved로 승격한다:

1. [ ] `scripts/reset_workspace.py` **T1 + T2** 구현 완료 (dry-run 기본, 삭제 매니페스트 JSON,
       Protected Paths 강제, `backups/reset_<ts>/` 휴지통 이동, 클린 트리 가드, T2 `--drop-qdrant`
       화이트리스트 검증). T3는 미구현 — 설계 문서로만 존재.
2. [ ] 회귀 테스트 통과 — 신규 `tests/test_reset_workspace.py`:
       Protected Paths(추적 파일·소스·config) 삭제 거부, dry-run 목록/용량 정확도, 매니페스트 스키마,
       경로 오염 방지(tmp fixture 격리 — `feedback_test_fixture_path_overrides` 준수),
       Qdrant 화이트리스트 부분일치 거부. + 기존 스위트 GREEN.
3. [ ] C1 독립 리뷰 완료 (신규 유틸리티 + Migration 성격 → CLAUDE.md 기준 대상)
4. [ ] 사용자(HQ) 승인

---

## 7. Next Steps

- [x] HQ가 Open Questions 답변 (2026-09-07: T1/T2 구현, T3 설계만, 나머지 CUE 판단)
- [x] 이 ADR을 v1로 확정
- [ ] **C1 Review 요청** ← 다음 게이트
- [ ] C1 리뷰 반영 후 T1+T2 구현 → `tests/test_reset_workspace.py` → 회귀 → Build Report
- [ ] `scripts/reset_for_beta.py` 처리 결정: T3 wrapper로 축소 vs deprecate 주석 (구현 시)
- [ ] 승인 시 Status `PROPOSED` → `ACCEPTED`, STATE.md 기록
