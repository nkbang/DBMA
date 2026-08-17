# C1 Task Order — End-User Package Gate 1: G1(Version SSOT) / G2(README) / G3(INSTALL.md) / DoD#7(Headless Verification)

| | |
|---|---|
| Issued by | CUE |
| Issued | 2026-08-17 |
| Executor | C1 |
| Verifier | CUE |
| Approver (final) | Rev. Bang |
| Status | GREEN — 착수 승인(Rev. Bang, 2026-08-17) |
| Basis | `docs/END_USER_PACKAGE_GATE1_BASELINE.md`, `docs/END_USER_PACKAGE_GATE1_G1G2G3_INVESTIGATION.md` |

---

## 0. Purpose (scope-limited)

Gate 1(End-User Package baseline)의 남은 4개 항목을 순서대로 구현·검증한다:
**G1(버전 SSOT 정리) → G2(README 갱신) → G3(INSTALL.md 재작성) → DoD#7(기존 venv 기반 headless 실행 검증)**.

This Task Order does **not**:
- `core/retrieval.py`, `RetrievalEngine`, ranking/embedding 로직 수정
- `pyproject.toml`에 새 packaging authority(`[project]` version 등) 생성 — G1 범위 아님, 별도 결정 대상
- Production corpus/TSU 파일, `dbma_qdrant`/`nae_qdrant` 데이터 변경
- 새 ADR 작성 — 이 작업 전부가 문서/문자열 정리이며 Architecture/Metadata Model/ID Governance를 건드리지 않음(CLAUDE.md C1 Review 트리거 미해당)

---

## 1. Prior Facts (CUE가 이미 확정 — 재조사 금지)

- 버전 문자열 4곳 불일치 확인됨: `config.yaml:6`(`"1.3.0"`, 정상값) / `core/config.py:35` fallback(`"0.6.4"`) / `dbma_ui.py:1` docstring(`"v1.1.0"`) / `scripts/install_nae_beta.command:32` `FALLBACK_TAG`(`"beta-v1.3.0-rc1"`).
- Git 태그 최신값(`v1.3.0`, `beta-v1.3.0-rc3`)이 `config.yaml`의 `"1.3.0"`을 뒷받침 — `config.yaml::app.version`이 실질적 SSOT.
- README.md가 언급하는 파일 경로는 `app/` 디렉터리 하나만 실제로 없음(나머지는 전부 실존 확인됨, 이전 baseline 조사의 "경로 누락" 판정은 오류였음 — 재조사하지 말 것).
- README.md 내부 자기모순 확인: 42-44행("ChromaDB 벡터 저장소를 통한 문서 임베딩 및 검색")과 88행("ChromaDB/Qdrant는 legacy... 검색 경로에서 쿼리되지 않음")이 정반대 서술.
- README.md에 현재 9개 UI 페이지(Dashboard/Library/Processing/Research/Chat/설교문 작성/설교 리뷰/Monitor/도움말), Citation 표시(방금 완료), NAE bridge(ADR-024, opt-in) 언급이 전혀 없음.
- INSTALL.md는 "Sprint 1"(2026-07-04) 문서, Ollama 설치 안내 0건, Qdrant를 "optional Sprint 2/3"으로 서술(현재 ADR-001/003/013/024와 불일치), `dbma_qdrant`(6333) 컨테이너는 현재 로컬에 존재하지도 않음(legacy/frozen이라 불필요).
- 로컬 환경(참고용, 이 값 자체를 하드코딩하지 말 것): Ollama 설치됨 + `bge-m3:latest`/`llama3.1:8b` 등 모델 준비됨, `~/envs/dbma311` venv 존재, Docker에 `nae_qdrant`(7333)는 떠 있으나 `dbma_qdrant`(6333)는 없음.
- 메모리 근거: DBMA 공식 venv는 `~/envs/dbma311`이며 `.venv_311` 등 임의 venv를 지시 없이 쓰지 말 것.

---

## 2. Role Separation

**C1 (executor)**: G1→G2→G3→DoD#7 순서로 구현·검증, evidence를 `.automation/evidence/end-user-package-gate1/`에 기록.
**CUE (verifier)**: 각 단계 완료 후 §5 acceptance criteria 대조, Hard Stop 여부 판정.
**Rev. Bang (approver)**: 이미 착수 승인 완료(GREEN). 완료 보고 시 최종 확인만.

---

## 3. Phases

### Phase G1 — Version SSOT 정리

- `config.yaml::app.version`(현재 `"1.3.0"`)을 유일한 SSOT로 확정.
- `core/config.py:35`의 fallback 값을 실제와 가까운 값으로 갱신(`APP_VERSION = _yaml_app.get("version", "1.3.0")` 형태 — YAML 로드 실패 시에만 노출되는 안전망이므로 SSOT와 다른 별도 버전 문자열을 새로 만들지 말 것).
- `dbma_ui.py:1` docstring의 `"v1.1.0"`을 SSOT와 일치시키거나(예: `"DBMA — Production Streamlit Entry Point"`처럼 버전 번호 자체를 docstring에서 제거하고 `config.yaml` 참조로 대체), 코드가 아닌 순수 주석이므로 하드코딩된 숫자를 남기지 않는 방향을 우선 검토.
- `scripts/install_nae_beta.command:32`의 `FALLBACK_TAG`는 배포 태그 체계(`beta-vX.Y.Z-rcN`)이므로 **삭제하거나 SSOT로 대체하지 말고**, 최신 태그로만 갱신(`beta-v1.3.0-rc3`) — 이 값의 정상 목적(네트워크 장애 시 fallback)을 유지.
- `pyproject.toml`에 `[project]` version 필드를 신규로 추가하지 말 것(범위 밖, Hard Stop 대상).

### Phase G2 — README.md 갱신

- `app/` 디렉터리 서술 제거(실존하지 않음).
- ChromaDB 관련 자기모순(42-44행 vs 88행) 제거 — 현재 상태(ChromaDB/Qdrant는 legacy, 검색 경로에서 쿼리되지 않음, ADR-001 Correction/ADR-003 근거)로 통일.
- End-user가 알아야 할 현재 기능을 중심으로 갱신:
  - 실제 9개 UI 페이지(Dashboard, Library, Processing, Research, Chat, 설교문 작성, 설교 리뷰, Monitor, 도움말)
  - Citation/Provenance 표시(방금 구현된 author/source_title/evidence_confidence 포함)
  - Dashboard(사용자용 통계)와 Monitor(시스템 상태) 분리 원칙
  - NAE bridge의 존재와 opt-in 성격(`config.yaml::modules.nae_pd.enabled`, 기본 `false`) — 내부 구현 세부사항(bridge_query 함수명 등)까지 옮기지 말고 "있다는 것과 기본 꺼져있다는 것"만 사용자 관점으로 서술.
- 버전 표기는 G1의 SSOT를 참조(하드코딩 금지 — README에 숫자를 직접 박아넣지 말고 "config.yaml 기준"으로 서술하거나, 빌드/릴리스 시 갱신하는 절차를 명시).
- **개발자 내부 아키텍처 설명(ADR 번호, 모듈 경계, RetrievalEngine 내부 구조 등)을 과도하게 옮기지 말 것** — README는 End-User 관점 유지, 개발자 상세는 기존 `docs/architecture/*`로 링크만.

### Phase G3 — INSTALL.md 재작성

End-user가 설치→실행까지 갈 수 있도록 아래 8개 섹션 최소 포함(현재 문서의 GPU/CUDA/ROCm/Conda/Windows 상세, 여러 OS 절차 등 개발자용 잡다한 내용은 축소하거나 `docs/`의 별도 개발자 문서로 분리 — 이 Task Order 범위에서 새 문서를 만들어야 한다면 파일명만 제안하고 내용 작성은 CUE 승인 후):

1. 사전 요구사항(Python 버전, 디스크/RAM, macOS 우선)
2. Python/venv 준비 — **`~/envs/dbma311` 관행을 문서화**(SPRINT/메모리 근거) 또는 프로젝트 로컬 `.venv` 중 실제 배포 시 사용자가 따라야 할 방식 하나로 통일(둘 다 제시해 혼란 주지 말 것)
3. **Ollama 설치**(macOS 기준 `brew install ollama` 또는 공식 방법) — 현재 문서에 0건이었던 gap
4. **필요한 Ollama 모델 준비**(`ollama pull bge-m3:latest` 등 — `config.yaml::embedding`/`ollama` 섹션 기준으로 정확한 모델명 확인 후 기재)
5. DBMA 설치/실행(`pip install -r requirements.txt`, `streamlit run dbma_ui.py`)
6. 최초 실행 확인(Onboarding 화면, 9개 페이지 로드)
7. 기본 검색/Chat 사용(짧은 실사용 예시)
8. 문제 발생 시 최소 진단 절차(로그 위치, 흔한 오류 3-5개)

**Qdrant 서술 처리**: "optional Sprint 2/3 services"라는 낡은 프레이밍 제거. 현재 사실(DBMA production 검색은 Qdrant를 전혀 쓰지 않음 — ADR-001/003, NAE opt-in 모듈만 별도 `nae_qdrant` 사용 — ADR-013/024)에 맞게 정확히 수정하거나, End-user 필수 설치 항목이 아니므로 통째로 "고급/선택 기능" 절로 이동. **필수 설치 항목처럼 보이게 하지 말 것.**

### Phase DoD#7 — Headless 실행 검증 (Option A)

- 기존 `~/envs/dbma311` venv를 그대로 사용(신규 venv 생성 금지, 모델 재다운로드 금지).
- `pip check`로 의존성 무결성 확인.
- `streamlit run dbma_ui.py`를 headless로 기동(예: `streamlit run dbma_ui.py --server.headless true &`), 9개 페이지 각각 에러 없이 렌더되는지 확인(스크린샷 또는 HTTP 응답 캡처).
- 검색 1회 실행 → citation/provenance 표시까지 실제 확인(방금 구현된 기능 재확인 겸함).
- **Production TSU/Qdrant mutation 0건**임을 검증(읽기 전용 쿼리만, `git status`로 corpus/output 파일 무변경 확인 + Qdrant point count 변화 없음 확인).
- **Evidence에 반드시 명시**: "이 검증은 기존 개발 환경(`~/envs/dbma311`, 이미 Ollama 모델 준비됨)에 의존하며, 완전히 새로운 사용자의 최초 설치 경험을 재현한 것이 아니다."

---

## 4. Hard Stop Conditions

즉시 중단하고 CUE에 보고(Rev. Bang에게 직접 보고 금지):
1. `config.yaml::app.version`을 SSOT로 유지할 수 없는 기술적 이유가 발견되는 경우
2. 버전을 중앙화하기 위해 architecture/packaging ADR이 필요하다고 판단되는 경우
3. INSTALL 과정에서 새로운 필수 infrastructure(현재 문서에 없는)가 발견되는 경우
4. `core/retrieval.py` 또는 DBMA Core/Retrieval authority 수정이 필요한 경우
5. Production corpus/TSU/Qdrant 변경이 필요한 경우
6. DoD#7 headless 검증이 Production mutation 없이 불가능한 것으로 확인되는 경우
7. `ui/tabs.py`/`ui/sidebar.py`가 실제로 죽은 코드인지 판단이 필요해지는 경우(G2 범위 밖 — README 서술만 정리, 코드 삭제/정리는 별도 작업)

**Never touch**: RAW 데이터, `core/retrieval.py`, ADR-001/003/013/017/024, Production Qdrant/TSU, `pyproject.toml`의 새 packaging authority 생성.

---

## 5. Acceptance Criteria

**G1**: 4곳의 버전 문자열이 `config.yaml::app.version`을 SSOT로 일관되게 참조/일치. `pyproject.toml` 무변경.
**G2**: README.md의 자기모순 해소, `app/` 서술 제거, 9개 페이지/Citation/Dashboard-Monitor 분리/NAE bridge(opt-in) 언급 추가, 개발자 내부 구조 과다 서술 없음.
**G3**: 8개 섹션 전부 포함, Ollama 설치+모델 pull 안내 추가, Qdrant 서술이 현재 아키텍처와 일치(또는 선택 기능으로 재분류), End-user가 실제로 따라갈 수 있는 흐름.
**DoD#7**: `~/envs/dbma311` 기반 headless 실행으로 9개 페이지 로드 + 검색 1회 + citation 표시 확인, Production mutation 0건, evidence에 "기존 환경 의존" 명시.

---

## 6. Output format expected from C1 per phase

`PHASE <G1|G2|G3|DoD7> — <PASS|INCOMPLETE|BLOCKED> — <1-line summary> — evidence: <path>`

Evidence 저장 위치: `.automation/evidence/end-user-package-gate1/`

---

## 7. CUE Pre-Review Gate

- [ ] `core/retrieval.py` 수정 필요? → No — 전부 문서/버전 문자열/설치 가이드.
- [ ] 신규 ADR 필요? → No — Metadata Model/ID Governance/Validator/Migration 변경 없음.
- [ ] Production mutation 필요? → No — DoD#7도 읽기 전용 쿼리만.
- [ ] `pyproject.toml` 신규 packaging authority 생성 위험? → 명시적으로 금지됨(§0, Hard Stop #1/2).
- [ ] ADR-001/003/013/024 영향? → No — 문서 서술 정정일 뿐 architecture 변경 아님.

**CUE Pre-Review verdict: PASS — Task Order may be issued to C1.**
