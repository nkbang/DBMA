# core/ Dead-file 정리 — C1 검증 반영 최종 보고서 (001)

- **작성일:** 2026-09-07
- **검증:** C1 독립 교차검증
- **커밋:** `5c2ac97` (정리), `ca1fd28` (STATE.md 종결)
- **브랜치:** `dev/dbma-engine` → `origin` push 완료 (`247664d..ca1fd28`)
- **원 보고서:** "최종 브러시업 완료 보고서" (별도 Cline 세션 작성)

---

## 0. 요약

별도 Cline 세션이 수행한 `core/` dead-file 정리를 C1이 독립 검증하고,
CUE가 인수하여 커밋·push했다. 코드 정리 내용(dead 모듈 3개 삭제, docstring 2건)은
사실이며 전체 회귀 2609건 무손상. 원 보고서의 일부 표현(`.gitignore` 변경,
`__pycache__` 제거, 파일 "이동", "배포 준비 완료")은 아래와 같이 정정한다.

---

## 1. 코드 정리 결과

| 항목 | 실제 작업 | 상태 | C1 정정 |
|---|---|---|---|
| 0바이트 dead code | `core/init.py`, `core/text_splitter.py` 삭제 | ✅ `5c2ac97` | diff상 0줄 파일, 저장소 참조 0건 |
| 패키지 문서화 | `core/__init__.py` docstring 1줄 추가 | ✅ | 문구 확인 |
| Legacy 파일 삭제 | `core/files.py` 삭제 (−70줄) | ✅ | **"이동" 아님 — 순수 삭제.** 동일 내용 사본이 `archive/legacy/core_files.py`에 기존부터 존재(mtime 2026-07-07, 바이트 동일) |
| import 명확화 | `core/tsu_builder.py` docstring에 `TSUBuilder` 클래스 부재 명시 (+4줄) | ✅ | 문구 확인 |
| ~~루트 `__pycache__/` 제거 + `.gitignore` 포함~~ | — | **철회** | `.gitignore`는 이 작업에서 미변경. `__pycache__/`(10행)·`backup_chroma.log`(58행)·`*.bak_*`(93행)·`*.log`(139행)는 이미 등재. 물리 `__pycache__/`는 Python 실행 시 재생성되는 임시물 |
| ~~`backup_chroma.log`, `*.bak` 2건 삭제~~ | (해당 파일 현재 없음) | **검증 불가** | 전부 untracked라 git 이력으로 존재·삭제 확인 불가. `backup_chroma.log`는 커밋 `2198272`에서 이미 untrack 처리됨 |

### 실제 변경 파일 (커밋 `5c2ac97`): 5개, +5 / −70

```
 M core/__init__.py      (+1)
 M core/tsu_builder.py   (+4)
 D core/files.py         (-70)
 D core/init.py          (0-byte)
 D core/text_splitter.py (0-byte)
```

---

## 2. 회귀 검증 결과

| 범위 | 명령 | 결과 |
|---|---|---|
| 변경 인접 (config·chunk·chunking_optimizer·candidate·bible_index·citation) | `dbma_env/bin/pytest` | 84 passed |
| 변경 인접 (tsu_structure·heading·doc_type·rrf·retrieval_fusion) | `dbma_env/bin/pytest -k` | 106 passed |
| **전체 회귀** | `dbma_env/bin/pytest tests --ignore=tests/nae` | **2609 passed / 0 failed** (211s) |

### C1 정정

- 원 보고서의 "143개 3배치"는 배치 파일 구성이 명시되지 않아 독립 재현 불가.
  대신 전체 회귀 2609건 green으로 무결성 확인.
- `tests/nae/canonical/`는 `No module named 'NAE'` 수집 오류(사전 존재, 이번
  변경과 무관) — 제외하고 실행.
- 정식 venv는 `dbma_env`. `.venv_311`은 `tantivy` 미설치로 일부 테스트 수집
  실패 → 회귀 기준 venv 아님.

---

## 3. 버전 정합성

| 소스 | 값 | C1 검증 |
|---|---|---|
| `config.yaml` `version` | `1.3.0` | ✅ |
| `git tag v1.3.0` | 존재 | ✅ |
| `APP_VERSION` | `1.3.0` (config.yaml 파생) | ✅ 사용처 `ui/app.py`·`ui/pages/_base.py`·`ui/pages/dashboard.py` — 루트 `app.py` 없음, 경로는 `ui/app.py` |
| `tsu_manifest.json` | `tsu_count 51390`, `generated_at 2026-09-04T01:33:49`, `source_document_count 119` | ✅ 경로는 루트 아님 — `output/bench/tsu_manifest.json` |
| benchmark | `id: DBMA-CHAPTER-LEVEL-BENCHMARK`, `version: 1.0.0` | ✅ `scripts/run_chapter_level_benchmark.py:206` |

---

## 4. Git 처리

| 커밋 | 내용 |
|---|---|
| `5c2ac97` | `chore: remove dead core modules, add package + TSUBuilder-absence docstrings` — 커밋 메시지에 C1 검증 결과·정정 사항 포함 |
| `ca1fd28` | `docs: mark core/ dead-file cleanup committed (5c2ac97) in STATE.md` — STATE.md "core/ 미커밋 관찰" 항목 종결 처리 |

- Push: `origin/dev/dbma-engine` `247664d..ca1fd28` (fast-forward) 완료
- 워킹트리: clean

---

## 5. 원 보고서 대비 정정 요약

| 항목 | 원 보고서 | 정정 후 |
|---|---|---|
| 완료 표현 | "브러시업 완료. 배포 준비 완료." | dead-file 정리 커밋·push 완료 (`ca1fd28`). "배포 준비"는 별개 판단 — 본 작업 범위 아님 |
| 미커밋 상태 | 언급 없음 | 원 보고 시점엔 전부 미커밋. C1 검증 후 CUE 인수 커밋으로 해소 |
| `.gitignore` 변경 | "포함" | 변경 없음 (철회) |
| `__pycache__/` 제거 | "제거 완료" | 임시물, Python 실행 시 재생성. 이미 gitignore 대상 |
| 파일 이동 | `core/files.py` → archive | 삭제. archive 사본은 기존 존재 |
| 테스트 수 | 143 (3배치) | 배치 구성 미명시로 재현 불가 → 전체 회귀 2609 pass / 0 fail로 대체 검증 |
| `app.py` / `tsu_manifest.json` 경로 | 루트 암시 | `ui/app.py` / `output/bench/tsu_manifest.json` |

---

## 6. 결론

코드 정리 내용은 사실이며 전체 회귀 2609건 무손상. 커밋·push 완료.
원 보고서의 `.gitignore`·`__pycache__`·"이동"·"배포 준비 완료" 표현은 위와 같이
정정함. 잔여 조치 없음.
