# End-User Package — Gate 2A: Packaging Surface Audit

- 작성: CUE, 2026-08-17
- 성격: 조사만 수행, 코드/문서/패키징 변경 없음
- Baseline: Gate 1 CLOSED / GREEN, 기준 commit `598fbdc`
- 목적: Gate 2B(Clean Install Test) 착수 전 "실제 배포 시 무엇이 포함되고 무엇이 빠지는가" 확정

---

## 1. 배포 메커니즘 구조

```
사용자 더블클릭
  → 내서재 베타 설치.app (scripts/build_mac_package.sh가 생성, 서명 없음)
      → Contents/MacOS/launcher (AppleScript, 터미널 안 띄움)
          → Contents/Resources/install_nae_beta.command
              → BETA_LATEST_TAG.txt(dev/dbma-engine 브랜치, raw) 읽어 최신 태그 확인
              → https://github.com/nkbang/DBMA/archive/refs/tags/{TAG}.tar.gz 다운로드
              → ~/내서재_베타/app 에 압축 해제 (기존 설치 있으면 PERSIST_ITEMS만 보존 후 교체)
              → scripts/setup_beta_tester.command 실행
                  → 메모리 감지 → 모델 등급 결정 → Homebrew/Ollama 설치 →
                    모델 pull → .venv_beta 생성 → pip install -r requirements.txt →
                    config.yaml 모델명 패치 → streamlit 백그라운드 실행 → 브라우저 오픈
```

**핵심 특징**: 패키징 단계에서 파일을 선별하지 않는다. `git archive`(GitHub 태그 tarball)가 **해당 태그 시점의 git-tracked 파일 전체**를 그대로 묶어 보낸다 — allowlist/denylist 메커니즘이 없다.

---

## 2. 현재 태그 시점(`beta-v1.3.0-rc3`, 2026-07-28) 기준 — 실사용자 영향 없음

`BETA_LATEST_TAG.txt`가 가리키는 태그를 직접 확인한 결과, **현재 라이브 베타 테스터는 문제 없음**:
- `git ls-tree -r beta-v1.3.0-rc3`에서 `NAE/` 경로 **0건** — 그 시점엔 NAE 파이프라인이 아직 저장소에 없었음.
- 즉 지금 이 순간 새로 설치하는 테스터는 깨끗한(NAE 미포함) 코드베이스를 받는다.

---

## 3. ⚠️ 핵심 발견 — 다음 릴리스 태그 시점 위험

**현재 HEAD(`dev/dbma-engine`, Gate 1 baseline 포함) 기준으로 새 태그를 컷하면 상황이 완전히 달라진다:**

| 대상 | git-tracked 파일 수 | 크기 |
|---|---|---|
| `NAE/` (전체) | 348 | **360M** |
| `.automation/` | 178 | 1.3M |
| `output/` | 0 | 0 (미추적, 안전) |
| `test_seal_*` (13개 디렉터리) | 211 | 소규모(개별 8-12K) |
| **저장소 전체 git-tracked 총합** | — | **385M** |

**`NAE/`가 git-tracked 전체 용량의 약 93.5%를 차지한다.** 세부:
- `NAE/corpus/`(작업 트리 기준 723M, 이 중 상당수가 tracked) — NAE 자체 TSU corpus 데이터. ADR-013/024에 따라 이는 **opt-in 모듈(`nae_pd`, 기본 `false`) 전용 데이터**로, 일반 최종 사용자(내서재 기본 사용자)는 전혀 필요로 하지 않음.
- `NAE/pipeline/`(1.7M), `NAE/review/`(25M) 등은 개발/파이프라인 도구.

**결론**: 지금 이 상태로 새 릴리스 태그(예: Gate 1의 Citation UI, README/INSTALL 개선을 반영한 다음 베타)를 컷하면, "터미널을 전혀 다루지 못하는 목회자 테스터"가 **385MB(그중 360MB가 불필요한 NAE 개발/코퍼스 데이터)를 다운로드**하게 된다. Gate 1에서 어렵게 정리한 매끄러운 설치 경험(INSTALL.md 8단계, Ollama 안내 등)이 무색해지는 실질적 회귀 위험.

**필터링 메커니즘 부재**: `.gitattributes`(export-ignore) 파일이 저장소에 없음 — `git archive`/GitHub 태그 tarball에서 특정 경로를 제외하는 표준 메커니즘이 현재 전혀 설정되어 있지 않다.

---

## 4. 그 외 패키징 표면 확인

- **`pyproject.toml`**: `[tool.basedpyright]`만 존재, 패키징 메타데이터 없음(Gate 1 G1에서 이미 확인·현행 유지 결정됨) — 이번 조사에서 재확인만, 변경 없음.
- **`core/config.py`**: `APP_VERSION`/`APP_NAME`이 `config.yaml`을 읽음 — 배포본에 `config.yaml`이 포함되는 한 정상 동작(포함됨, gitignore 대상 아님).
- **`dbma_ui.py`**: 단순 wrapper, 배포본에 포함되어야 함(포함됨).
- **`.gitignore`**: `data/`, `chroma_db/`, `archive/`, `backup(s)/`, `cache/`, `output/SPRINT5_ENGINEERING_VALIDATION/` 등은 올바르게 제외 — 이 부분은 정상. 문제는 **NAE/corpus, .automation/, test_seal_\* 가 gitignore 대상이 아니라 tracked 상태**라는 점.
- **PERSIST_ITEMS**(`install_nae_beta.command:40`): 업데이트 시 보존 대상은 `data/RAW`, `data/제련완성본`, `output`, `chroma_db`, `logs`, `config.yaml` — Gate 1에서 확인된 실제 데이터 흐름과 일치, 문제 없음.
- **모델 배포 로직**(`setup_beta_tester.command`): 메모리 기반 3단계 등급(8GB 미만 차단/16GB 미만 llama3.2:3b/이상 llama3.1:8b), 임베딩은 `bge-m3:latest` 고정 — Gate 1 G3에서 문서화한 내용과 일치.
- **UI 정적 자산**: 별도 `static/`류 디렉터리 없음(grep 결과 없음) — Streamlit이 자체 처리, 이번 감사에서 별도 이슈 없음.

---

## 5. Gate 2B 착수 전 결정 필요 사항

1. **다음 릴리스 태그를 컷하기 전에 반드시** `NAE/`, `.automation/`, `test_seal_*` 등 dev-only 경로를 배포 tarball에서 제외하는 메커니즘(`.gitattributes export-ignore`, 또는 릴리스 전용 빌드 스텝에서 필터링)을 마련해야 한다 — 이건 Gate 2 구현 항목 후보이지 지금 임의로 처리하지 않음(Architecture Freeze 범위는 아니지만, 배포 스크립트 변경이므로 CUE가 임의 진행하지 않고 승인 필요).
2. Gate 2B(Clean Install Test)는 **현재 태그(`beta-v1.3.0-rc3`) 기준으로 수행하면 이번 발견과 무관하게 통과할 것** — 그러나 그것만으로는 "Gate 1에서 완성한 변경사항이 실제로 배포 가능한가"를 검증하지 못한다(Gate 1 변경분은 아직 어떤 태그에도 포함되지 않았으므로). Gate 2B의 진짜 목적(Gate 1 산출물의 배포 가능성 검증)을 달성하려면 이 필터링 문제를 먼저 풀어야 한다.
3. Production 격리 원칙(Gate 2 핵심 원칙 #2)과 직결: `NAE/corpus`가 태그에 그대로 포함되는 것은 "Production 데이터를 이용해 설치 성공을 증명"하는 것과는 다른 문제이지만(이건 설치*생성물*에 프로덕션 데이터가 섞여 나가는 문제), 같은 맥락에서 **배포물 자체에 프로덕션/코퍼스 데이터가 섞이지 않아야 한다**는 원칙과 연결된다.

---

## 6. 변경하지 않은 것 (확인)

- `core/retrieval.py`, `pyproject.toml` — 무수정.
- `install_nae_beta.command`, `build_mac_package.sh`, `setup_beta_tester.command`, `.gitignore` — 전부 읽기만 함, 무수정.
- `BETA_LATEST_TAG.txt` — 무수정, 여전히 `beta-v1.3.0-rc3`.
- 어떤 태그도 새로 생성하지 않음, 어떤 파일도 스테이징/커밋하지 않음.
