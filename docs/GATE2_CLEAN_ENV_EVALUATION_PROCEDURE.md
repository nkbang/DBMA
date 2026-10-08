# Gate 2 깨끗한 환경 평가 절차서

- 작성: 2026-10-07 · 대상 브랜치 `fix/merge-production-path-safety`
- 상위 문서: `docs/GATE2_REASSESSMENT_20261007.md` (Gate 2 최종 재판정)
- 목적: 개발 Mac에서는 평가할 수 없었던 **전역 설치 단계와 기본 모드 end-to-end**를 깨끗한 macOS에서 평가한다.
- 도구: `scripts/gate2/clean_env_snapshot.sh` (읽기 전용 스냅샷 수집기)

## 0. 먼저 알아야 할 사실

1. **지금 테스터가 받는 릴리스에도 F1 결함이 있다.** `install_nae_beta.command`는 현재 브랜치가 아니라 `origin/dev/dbma-engine`의 `BETA_LATEST_TAG.txt`(현재 `beta-v1.3.0-rc6`)가 가리키는 태그 tarball을 내려받는다. 그 태그를 `git archive`로 풀어 시험하면 `import ui.app`이 `No module named 'NAE'`로 실패하고 AppTest도 같은 예외를 낸다 (`NAE/ export-ignore` + `ui/` 최상위 NAE import). F1·F1-b 수정(`3a10bb3b`, `f49ffeb3`)과 설치 스크립트 정비(`aafd2dfb`)는 **아직 `dev/dbma-engine`에도, 어떤 태그에도 없다**.
2. **설치기에는 다운로드 URL 오버라이드가 없다.** 그래서 후보(수정 포함) 빌드로 `install_nae_beta.command` 전체 경로를 평가하려면 새 태그와 `BETA_LATEST_TAG.txt` 갱신이 필요하다(승인 사항, §2).
3. **GitHub 태그 tarball도 `export-ignore`를 따른다 — 2026-10-07 개발 Mac에서 실제 다운로드로 확인 완료**(`evidence/gate2/20261007-t0-tarball/`: `NAE/` 멤버 0, 압축 해제본 `import ui.app` 실패). 아래 T0 단계는 깨끗한 환경에서 같은 결과를 재확인하는 용도다.
4. 이 평가는 **개발 Mac에서 하지 않는다.** 설치기는 `~/내서재_베타`, `/Applications`, `/usr/local`, Homebrew, 실행 중 Ollama를 건드린다.

## 1. 평가 트랙

| 트랙 | 평가 대상 | 진입점 | 선결 조건 | 예상 결과 |
|---|---|---|---|---|
| **A. 현 배포 현상 확인** | 지금 배포된 `beta-v1.3.0-rc6` | `install_nae_beta.command` (실제 사용자 경로) | 없음 | **C9에서 FAIL 예상** (F1). PASS면 이상 징후 — §6 |
| **B. 후보 설치 스크립트** | 후보 커밋의 `setup_beta_tester.command` | 후보 `git archive`를 풀어 직접 실행 | 후보 tarball 전달 | 전역 설치 단계·앱 기동 평가. 다운로드·업데이트 경로는 **미포함** |
| **C. 후보 end-to-end** | 수정 포함 후보 태그 | `install_nae_beta.command` | **승인 필요**: 후보 태그 생성, `dev/dbma-engine` 병합, `BETA_LATEST_TAG.txt` 갱신 | 전체 PASS가 목표. 업데이트 보존(U1)은 태그 2개 필요 |

권고 순서: A → B → (승인 후) C. A는 F1이 실제 릴리스에서 재현되는지 확정하고, B는 승인 없이 전역 설치 단계를 평가한다.

## 2. 승인이 필요한 항목 (CUE는 임의로 수행하지 않는다)

- 후보 **Release Tag 생성**, GitHub Release 생성
- `dev/dbma-engine`(주 라인) 병합 및 `BETA_LATEST_TAG.txt` 갱신 — 테스터 전원에게 영향
- 기존 `beta-v1.3.0-rc6`의 이동·삭제 (하지 않는다)
- 평가 결과가 FAIL이어도 릴리스 롤백/중단 결정은 HQ

## 3. 환경 요건

**깨끗한 환경의 정의**: 아래 사전 점검(P1)에서 도구류가 모두 `absent`, 설치 디렉터리 없음, 포트 8520 비어 있음.

| 항목 | 요건 |
|---|---|
| OS | macOS, **Apple Silicon**(arm64). 설치 스크립트가 `/opt/homebrew`를 전제 |
| 형태 | **새 macOS VM**(UTM/Parallels/Tart 등) 또는 별도 Mac의 새 사용자 계정. VM이면 시작 직전 **스냅샷**을 만들어 둔다(롤백용) |
| 메모리 | 모델 등급이 메모리로 결정된다: `<8GB` 설치 중단, `8~16GB` `llama3.2:3b`, `≥16GB` `llama3.1:8b`. **최소 두 등급(예: 8GB, 16GB+)**에서 평가 권고 |
| 디스크 | 여유 **30GB 이상** (venv 수 GB + 모델 약 5~6GB + 임베딩 1.2GB) |
| 네트워크 | github.com, raw.githubusercontent.com, ollama.com, Homebrew, PyPI 접근 |
| 권한 | 관리자 계정(Homebrew·`/Applications`·`/usr/local` 쓰기). 암호 입력이 나오면 평가자가 직접 입력 |
| 금지 | 실제 개인 자료·계정·API 키 사용 금지. 평가용 소형 샘플 문서만 사용 |

## 4. 절차

모든 터미널 출력은 **단계마다 새 파일명**으로 저장한다(`tee` 덮어쓰기 사고 방지). 저장 위치 예: `~/gate2-clean-env/`. `clean_env_snapshot.sh`는 같은 라벨이 이미 있으면 중단한다.

### P — 사전 점검

**P1. 환경 확인** (평가 대상 Mac에서; `clean_env_snapshot.sh`를 먼저 옮겨 둔다)

```bash
mkdir -p ~/gate2-clean-env && bash clean_env_snapshot.sh precheck ~/gate2-clean-env && cat ~/gate2-clean-env/snapshot_precheck.txt
```

합격: `virtual_machine: 1`(VM인 경우), `brew`·`ollama`·`python3.11`·`pdftoppm`·`tesseract`·`Ollama.app`·`~/내서재_베타`가 모두 `absent`, 포트 8520/11434 listeners 0. 하나라도 `PRESENT`면 깨끗하지 않다 → 스냅샷으로 되돌리거나 새 계정을 쓴다. Command Line Tools는 있어도 되지만 `PRESENT/absent`를 기록한다(없으면 Homebrew 설치 중 설치됨).

**P2. 평가 대상 고정**: 평가할 태그/커밋 SHA를 기록한다.

```bash
echo "TRACK=A subject=beta-v1.3.0-rc6" | tee ~/gate2-clean-env/subject.txt
```

### T0 — (트랙 A) 실제 tarball에 NAE가 포함되는지 확인

```bash
curl -fL https://github.com/nkbang/DBMA/archive/refs/tags/beta-v1.3.0-rc6.tar.gz | tar -tz | tee ~/gate2-clean-env/T0_tarball_listing.txt | grep -c '/NAE/'
```

결과 `0`이면 `export-ignore`가 적용된 것이다(F1이 릴리스에서 재현될 전제 성립). 0이 아니면 §6의 불일치 처리.

### I — 설치 실행

**트랙 A/C** (실제 사용자 경로):

```bash
bash clean_env_snapshot.sh before ~/gate2-clean-env
# .app/.dmg를 쓰는 경우 더블클릭. 스크립트로 시험하는 경우:
bash install_nae_beta.command 2>&1 | tee ~/gate2-clean-env/I1_install_run1.txt
```

**트랙 B** (후보 스크립트 단독 — 후보 tarball을 `~/candidate/`에 푼 뒤):

```bash
bash clean_env_snapshot.sh before ~/gate2-clean-env
cd ~/candidate/DBMA-* && bash scripts/setup_beta_tester.command 2>&1 | tee ~/gate2-clean-env/I1_setup_run1.txt
```

관찰·기록: macOS 알림/대화상자 문구와 시각(스크린샷), 소요 시간, 암호 프롬프트 발생 여부, 종료 코드(`tee` 때문에 `${PIPESTATUS[0]}`로 확인).

```bash
bash clean_env_snapshot.sh after-install ~/gate2-clean-env
```

### V — 기능 확인

| 단계 | 방법 |
|---|---|
| V1 | 브라우저에서 `http://localhost:8520` 확인, 첫 실행 온보딩 표시 |
| V2 | 사이드바 6개 페이지(홈, 내 서재, 자료 등록, 연구·채팅, 설교 준비, 도움말)를 모두 열어 오류 화면(traceback) 유무 기록 |
| V3 | 연구·채팅 화면에 "내서재 공개 자료" 섹션이 **보이지 않음**(기본 `nae_pd` 꺼짐) |
| V4 | 소형 샘플 문서 1건 업로드→처리→검색/질문 1회. 답변이 생성되고 출처가 표시됨 |
| V5 | (선택, 후보 빌드) `config.yaml`에서 `modules.nae_pd.enabled: true`로 바꾸고 공개 자료 검색 클릭 → 앱이 죽지 않고 "이 설치본에 포함되어 있지 않습니다" 경고 후 빈 결과 |
| V6 | 앱 로그 확인: `~/내서재_베타/app/beta_app.log` 말미 |

### U — 재실행·업데이트·보존

| 단계 | 방법 |
|---|---|
| U0 | 같은 설치기를 다시 실행(동일 태그) → 중복 설치·오류 없이 기동, 버전 문구 확인. 출력은 `I2_install_run2.txt`로 별도 저장 |
| U1 | **(트랙 C, 태그 2개 필요)** 설치 후 `~/내서재_베타/app/` 아래 `PERSIST_ITEMS` 8개 경로에 표식 파일을 만들고, 새 태그로 업데이트 승인 → 8개 모두 보존·내용 일치 |

`PERSIST_ITEMS`: `data/RAW`, `data/제련완성본`, `output`, `chroma_db`, `logs`, `config.yaml`, `data/chat_session_history.json`, `data/inbox/logos_export`.

### N — 부정 시험 (선택)

| 단계 | 방법 | 합격 기준 |
|---|---|---|
| N1 | 네트워크 차단 상태에서 설치 | 대화상자로 실패 사유 안내(Homebrew/Ollama 설치 실패), 무한 대기 없음 |
| N2 | 메모리 8GB 미만 VM | "최소 사양(8GB) 미만" 안내 후 중단 |
| N3 | 서버 기동 지연을 재현하기 어려우면 생략 | 지연 시 "완료" 대신 "아직 응답하지 않습니다" 문구(후보 빌드) |

### X — 정리·롤백

- VM이면 **스냅샷으로 복귀**(권장). 새 계정이면 계정 삭제.
- 수동 정리가 필요한 경우: 앱 서버 종료(`pkill -f "streamlit run dbma_ui.py"`), `~/내서재_베타` 삭제. `/Applications/Ollama.app`·`/usr/local/bin/ollama`·Homebrew 패키지는 의도적으로 설치 스크립트의 정리 범위 밖이다(Gate 2 90 스크립트도 동일).
- 마지막 스냅샷: `bash clean_env_snapshot.sh after-cleanup ~/gate2-clean-env`

## 5. 합격 기준

| ID | 항목 | 합격 기준 |
|---|---|---|
| C1 | 설치기 다운로드·버전 확인 | `.installed_tag`가 평가 대상 태그와 일치 |
| C2 | 설치 5단계 완료 | 알림 1/5~5/5 순서대로, 대화상자(FATAL) 없음, 종료 코드 0 |
| C3 | Ollama 직접 설치 | `/Applications/Ollama.app` 존재, `/usr/local/bin/ollama` 링크, `codesign --verify`/`spctl -a` 통과 |
| C4 | 모델 | `ollama list`에 `bge-m3:latest`와 등급 모델(`llama3.1:8b` 또는 `llama3.2:3b`) |
| C5 | Homebrew 패키지 | `poppler`, `tesseract`, `python@3.11`, `hunspell` |
| C6 | hunspell 링크 | `/usr/local/lib/libhunspell.dylib`, `/usr/local/Cellar/hunspell/1.6.2/include/hunspell` |
| C7 | Python 환경 | `~/내서재_베타/app/.venv_beta` 존재, `pip install -r requirements.txt` 성공(hunspell 빌드 포함) |
| C8 | 서버 기동 | 포트 8520 listen, `curl -fs http://localhost:8520` 성공 |
| **C9** | **앱 실제 동작** | V1~V2: 6개 페이지 모두 traceback 없이 열림 (`import ui.app` 성공) |
| C10 | 모듈 게이팅 | V3: 기본 상태에서 공개 자료 섹션 비표시 |
| C11 | 기능 | V4: 소형 문서 처리→질문→출처 포함 답변 |
| C12 | NAE 부재 fail-closed | V5(후보 빌드): 경고+빈 결과, 앱 생존 |
| C13 | 재실행 | U0: 오류 없이 기동 |
| C14 | 데이터 보존 | U1(트랙 C): 8/8 보존 |
| C15 | 설치 모델 등급 | 메모리 등급과 `ollama list`의 생성 모델 일치 |

## 6. 판정 규칙과 예상 결과

- **PASS**: 해당 트랙의 필수 항목(트랙 A: C1~C9, 트랙 B: C2~C12, 트랙 C: C1~C15) 전부 합격
- **FAIL**: 필수 항목 하나라도 불합격. 불합격 항목·재현 단계·증거 파일명을 기록
- **BLOCKED**: 환경 문제로 판정 불가(예: 네트워크 장애, VM 문제). 재시도 후에도 같으면 사유 기록
- **N/A**: 해당 트랙에 적용되지 않음(예: 트랙 B의 C1·C14)
- **트랙 A 예상 결과는 C9 FAIL**이다. PASS가 나오면 "F1이 릴리스에서 재현되지 않음"이라는 **불일치**이므로, T0 결과(tarball에 `NAE/`가 포함됐는지)와 `.installed_tag`를 확인해 원인을 기록하고 재판정 문서의 F1 서술을 수정한다.
- **트랙 A FAIL의 의미**: 현재 배포(rc6)를 새로 설치한 테스터의 앱이 기동하지 않는다는 뜻이다. 후속 조치(핫픽스 태그, `BETA_LATEST_TAG` 조정)는 HQ 결정 사항이다.
- Gate 2 전체 판정은 이 평가 결과를 반영해 `docs/GATE2_REASSESSMENT_20261007.md`를 갱신하여 재산정한다.

## 7. 증거 수집·보관

수집물 (평가 Mac의 `~/gate2-clean-env/` → 저장소 `evidence/gate2/<run-id>-clean-env/`로 복사):

- `snapshot_precheck.txt`, `snapshot_before.txt`, `snapshot_after-install.txt`, (`snapshot_after-rerun.txt`), `snapshot_after-cleanup.txt`
- `subject.txt`, `T0_tarball_listing.txt`, `I1_*.txt`, `I2_*.txt` — 단계별 원본 출력
- 알림/대화상자/오류 화면 스크린샷, 각 페이지(V2) 스크린샷
- `beta_app.log` 사본, `ollama list`, `brew list`, 종료 코드 기록
- 평가 메모: 평가자, 일시, 트랙, 환경(VM 종류·메모리·macOS 버전), 이상 징후

주의: 출력 파일은 **원본 캡처**여야 한다(대화 기록에서 옮긴 복원본은 증거 신뢰도가 낮아 별도 표기). 개인 정보가 들어갈 수 있는 스크린샷은 올리기 전에 확인한다. 저장소에는 **manifest v2 + 커밋본 기준 verify**(기존 `evidence/gate2/*` 방식)로 고정하고, `.log` 확장자는 `.gitignore`(`*.log`)에 걸리므로 `.txt`로 저장한다.

## 8. 역할 분담

| 담당 | 작업 |
|---|---|
| 평가자(사용자) | VM/계정 준비, 위 명령 실행, 스크린샷·원본 출력 수집, 암호 입력 |
| CUE | 수집물 정리·manifest/verify 생성·커밋, 결과를 판정표에 반영, F1 재현 불일치 분석 |
| HQ | §2 승인 항목(후보 태그, 병합, `BETA_LATEST_TAG` 갱신), FAIL 시 릴리스 조치 |

## 9. 한계

- GitHub 태그 tarball의 내용은 개발 Mac에서 이미 확인했다(`20261007-t0-tarball`). 로컬 `git archive`는 GitHub tarball과 `tests/nae/`(테스트 파일 4개)만 다르다 — 이 Mac의 `core.ignorecase=true` 때문이며 앱 실행과 무관.
- 메모리 등급별 평가는 환경 마련 여건에 따라 일부만 수행할 수 있으며, 수행하지 못한 등급은 판정표에 `미평가`로 남긴다.
- 모델 응답 품질(groundedness 등)은 이 절차의 범위가 아니다(설교·신학 답변 품질 감사에서 다룸).
