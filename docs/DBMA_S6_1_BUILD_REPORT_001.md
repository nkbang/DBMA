# S6-1 Build Report — R1~R8 체크리스트 (배포 게이트 G4)

- 작성: CUE · 일자: 2026-09-21
- 근거: `docs/DBMA_RELEASE_GAP_CLOSURE_PIPELINE_v1.md` §0(R1~R8), §5(G4)

---

## 요약: G4 조건부 — R4 구현 완료, Release 발행만 남음

| # | 조건 | 판정 | 근거 |
|---|---|---|---|
| R1 | 자료 0건 시 생성 차단 | ✅ PASS | `tests/test_sermon_insufficient_evidence.py` 5건 PASS (자동 테스트). 빈 코퍼스 실기는 미실시(운영 코퍼스를 비우는 파괴적 조작이라 회귀 테스트로 대체) |
| R2 | 인용에 책 제목·저자 (null 없음) | 🟡 부분 | registry 81건 중 77건(95%) title/author 채워짐(사이드카 백필, PR #60). 나머지 4건은 기존 orphan 레코드(zero-padding 파일명 불일치) — 별도 세션에서 진행 중(task_ee6d0f37, 현재 OPEN, MTP 전권 재확보 작업으로 확장됨) |
| R3 | 설교 저장·재열람 | ✅ PASS | P1 SermonArtifact(PR #63) — Streamlit AppTest로 목록·열기·강단모드 실기 확인 |
| R4 | 동봉 자산 전량 출처 확인 | 🟡 **구현 완료, 발행 대기** | §1 참고. HQ가 "방식 A(GitHub Release 바이너리 자산)"로 결정(2026-09-21). `scripts/build_corpus_bundle.sh`(신규) + `scripts/install_nae_beta.command` 수정으로 구현·기능 검증 완료. **실제 GitHub Release 생성·자산 업로드는 승인 항목(CLAUDE.md)이라 아직 미실행** — S6-4에서 함께 처리 |
| R5 | 한글 성경 본문 경로 | ✅ PASS (R4에 종속) | `reference.json`이 R4의 Release 자산 번들에 포함됨 — R4 발행 시 함께 해소. `core/bible_text.py`의 fail-closed 동작은 코드 검토로 별도 확인 완료 |
| R6 | 외부 3~5명 실기 | ⏳ 미착수 | 사용자 몫(S6-3). R4 Release 발행 후 착수 가능 |
| R7 | 보안 체크리스트 5건 | ✅ PASS | `scripts/security_preflight.py` 재실행 확인(2026-09-21) — 4/5 적용, 1/5(FileVault)는 사용자 기기 설정이라 INSTALL.md 권고로 대응, 1/5(업로드 스캔) 부분충족은 배포 차단 아님으로 기존 판정 유지 |
| R8 | 회귀 테스트 전량 통과 | ✅ PASS | 3,152 passed, 0 failed (`pytest tests/`, 2026-09-21) |

**G4(S6-1) 판정: 조건부 — 코드는 전부 준비됐으나, Release 생성(승인 항목)과 R6(사용자의 외부 실기)만 남음.**

---

## 1. R4 결함 상세 — "동봉 서재"가 실제로는 동봉되지 않는다

### 확인한 사실

1. `.gitignore:2` = `data/` — 예외 패턴 없음. `git ls-files data/` → **0건**(현재 `data/` 아래 어떤 파일도 git이 추적하지 않는다).
2. `output/`도 마찬가지로 대부분 gitignore 대상 — TSU dataset(`output/bench/tsu_dataset.jsonl`, 224MB)도 추적 안 됨.
3. `scripts/install_nae_beta.command:116` — 설치 시 내려받는 것은
   `https://github.com/{owner}/{repo}/archive/refs/tags/{LATEST_TAG}.tar.gz`,
   즉 **git이 추적하는 파일만 담긴 태그 스냅샷**이다.
4. `scripts/setup_beta_tester.command` 전체를 확인했으나 코퍼스·
   성경본문을 내려받거나 재구성하는 단계가 **없다**.
5. 따라서 베타 테스터가 설치를 마치면: `data/RAW` 없음 → `data/제련완성본/
   registry/documents.json` 없음(또는 빈 레지스트리) → 첫 검색 시
   R1의 "자료 0건" 정상 차단 화면만 보게 된다.

### 왜 지금까지 안 드러났는가

S2-3/S2-4(코퍼스 확충, PR #44)와 S5-선결(`reset_for_beta.py::reseed_baseline()`,
PR #45)은 전부 **이 개발 기기 위에서** 코퍼스를 만들고 재적재하는
작업이었다 — "다음에 배포 패키징할 때 자동으로 실린다"는 암묵적 가정이
있었으나, 실제 배포 산출물(git 태그 tarball)이 `data/`를 아예 보지
못한다는 사실을 이번 S6-1 체크리스트를 실행하며 처음 확인했다.
`reseed_baseline()`이 참조하는 원본 경로(`~/NAE_CORPUS_RAW/raw/archive_org/
sermons/`)도 이 개발 기기에만 있는 로컬 경로라, 테스터 기기에서
돌려도 소스가 없어 실패한다.

### 해결 방향 — HQ 결정: 방식 A (2026-09-21)

코퍼스를 실제로 테스터에게 전달하려면 아래 중 하나가 필요하다:

| 방식 | 개요 | 장점 | 단점 |
|---|---|---|---|
| **A. GitHub Release 바이너리 자산** | 빌드된 `tsu_dataset.jsonl`(224MB)+`registry/documents.json`+`data/bible/reference.json`을 압축해 Release 자산으로 올리고, `install_nae_beta.command`가 태그 tarball과 별도로 내려받아 압축 해제 | 테스터 첫 실행이 빠름(재처리 없음), GitHub Release 자산 2GB 한도 내 | Release 생성마다 자산 재업로드 필요(승인 항목), 자산 버전과 코드 버전 동기화 관리 필요 |
| **B. 첫 실행 시 RAW 재처리** | `data/RAW`(111MB, 63종 원문)를 Release 자산으로 배포 → 첫 실행 시 `reset_for_beta.py` 유사 로직으로 처리(추출→청킹→임베딩) | 코드와 데이터가 같은 파이프라인 버전으로 항상 일치 | 첫 실행이 매우 느림(로컬 LLM 임베딩 63종, 체감 수십 분), 실패 지점 많음 |
| **C. git-lfs 또는 서브모듈로 `data/` 일부 추적 전환** | `.gitignore` 예외를 둬서 코퍼스 파일만 git으로 추적 | 기존 태그 tarball 메커니즘 그대로 재사용 | git 저장소 비대화, 기존 "개인 서재는 커밋 안 됨" 설계 원칙과 충돌 위험(사용자 문서·PDF와 같은 디렉터리 구조라 실수로 개인 자료까지 추적될 위험) |

CUE 권고: **A** — 이미 §5-1/5-2(Ollama 다운로드)에서 "설치 시 필요한 큰 자산은
Release/공식 배포처에서 내려받는다"는 패턴을 쓰고 있어 일관되고, 코퍼스
버전 관리가 코드 버전과 분리돼 재현성 있는 릴리스 관리가 된다.

**구현 완료**: `scripts/build_corpus_bundle.sh`(신규) — `output/bench/
tsu_dataset.jsonl`+`tsu_manifest.json`+registry+`reference.json`을
묶어 `dist/nae_baseline_corpus.tar.gz`로 압축(실측 47MB, GitHub 자산
2GB 한도 내). `tantivy_index`/`bible_index.sqlite3` 등 캐시는 담지
않음 — `core/candidate_generator.py::open_or_build_index()`가 첫
검색 시 `tsu_dataset.jsonl`에서 스스로 만든다(자체 확인). `knrv.json`
(저작권 있는 개역개정)은 의도적으로 제외.

`scripts/install_nae_beta.command`에 코퍼스 다운로드 단계 추가 —
`$APP_DIR/output/bench/tsu_dataset.jsonl`이 없을 때만(첫 설치, 또는
테스터가 직접 지웠을 때) 같은 태그의 Release 자산을 내려받아 푼다.
다운로드 실패해도 치명적이지 않게 설계(빈 서재로 계속 진행, R1 정상
차단 화면).

**기능 검증**: 실 프로덕션 데이터로 번들 생성 → 로컬 mock 설치
시뮬레이션(curl을 로컬 파일 복사로 대체)으로 "1차 실행 시 다운로드
+ 압축 해제", "2차 실행 시 이미 있어 건너뜀" 두 분기 모두 확인.
`bash -n`으로 두 스크립트 문법 검사 통과.

**남은 것**: 실제 GitHub Release 생성·자산 업로드(`gh release
create`)는 CLAUDE.md 승인 항목(Release 생성)이라 아직 미실행 — S6-4에서
사용자 승인 후 함께 처리한다.

---

## 2. R2/R5 잔여 사항

- R2 orphan 4건: 사용자가 별도 세션(task_ee6d0f37)에서 MTP 전권
  chspurgeon.com 현대어판 교체로 확장 진행 중 — 완료되면 자동으로
  해소될 가능성이 높음(재처리 시 새 sidecar 백필 필요 여부만 확인
  하면 됨). 이번 리포트에서 별도 조치 안 함.
- R5: R4(방식 A)가 해결되면 `reference.json`이 Release 자산에 포함돼
  같이 해소된다. 추가 작업 불필요.

---

## 3. 다음 조치

1. ~~R4 해결 방식 확정~~ — 완료(방식 A, 2026-09-21).
2. ~~구현~~ — 완료(`build_corpus_bundle.sh` + `install_nae_beta.command`).
3. **S6-4에서 실제 Release 생성 + `bash scripts/build_corpus_bundle.sh`
   실행 후 자산 업로드** — 승인 필요, 아직 미실행.
4. R6(외부 실기)은 Release 발행 후 착수.
5. R2 orphan 4건은 별도 세션(task_ee6d0f37) 완료 후 확인.

```
STATUS:      S6-1 체크리스트 실행 + R4 구현 완료 — Release 발행만 남음
Changed:     scripts/build_corpus_bundle.sh(신규), scripts/install_nae_beta.command,
             docs/DBMA_S6_1_BUILD_REPORT_001.md
Tests:       회귀 3,152 PASS, 보안 체크리스트 재실행 PASS. 신규 bash 로직은
             실 프로덕션 데이터로 번들 생성 + 로컬 mock 설치 시뮬레이션
             (다운로드/건너뛰기 두 분기) 기능 검증, bash -n 문법 검사 PASS
Regression:  PASS
Git:         커밋·푸시 예정
Next:        S6-4(Release 생성, 승인 항목) → R6(외부 실기, 사용자 몫) → G4 재평가
```
