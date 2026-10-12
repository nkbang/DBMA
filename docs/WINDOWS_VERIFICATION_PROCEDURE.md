# Windows 검증 절차서

- 작성: 2026-10-12 · 기준 코드: `dev/dbma-engine` (PR #116 인코딩 위생, PR #117 `fcntl` 대체가 병합된 `1b50181f` 이후)
- 실행 도구: `scripts/windows/verify_windows_readiness.py` (자동 점검 11개, 크로스플랫폼 파이썬)
- 관련 문서: `docs/GATE2_CLEAN_ENV_EVALUATION_PROCEDURE.md`(macOS 설치기 평가), `docs/GATE2_REASSESSMENT_20261007.md`

## 0. 이 절차가 하는 일과 하지 않는 일

**하는 일**: Windows 머신에서 **소스로부터 앱을 실행**해, 지금까지 코드 수정으로 해소했다고 믿는 문제(앱 기동, 파일 잠금, 인코딩)가 실제로 해소됐는지 확인하고, **아직 해소되지 않은 것으로 알려진 위험**(§1)을 측정한다.

**하지 않는 일** — 이 절차를 통과해도 아래는 **검증되지 않은 상태**다:
- Windows 설치기: 현재 설치기(`install_nae_beta.command`, `setup_beta_tester.command`)는 전부 macOS 전용이라 **Windows용 설치기는 아직 존재하지 않는다.** 이 절차는 설치기가 아니라 "소스 실행 가능 여부"를 본다.
- 코드서명·SmartScreen/Defender 경고, Windows on ARM, 장시간 안정성, 실제 사용자 자료의 대량 처리, 모델 응답 품질.
- 이 스크립트 자체: **macOS에서만 시험되었고 Windows에서는 첫 실행이다.** 이상한 결과가 나오면 앱 결함으로 단정하기 전에 먼저 스크립트의 오류를 의심하라.

## 1. 지금까지 알려진 Windows 상태

| 항목 | 상태 | 근거 |
|---|---|---|
| 앱 기동 (`import ui.app`) | **해소로 추정, Windows 미검증** | `fcntl`(POSIX 전용) 직접 사용을 `core/file_lock.py`로 교체(#117). `fcntl` 등 POSIX 전용 모듈을 막은 macOS 모사에서 성공 |
| 파일 잠금 | **macOS에서만 검증** | 기존 시험 7건 + 신규 8건 통과. Windows는 `filelock`의 `msvcrt.locking` 경로를 소스로 읽은 것이 근거 |
| 텍스트 인코딩 | 위생 수정, **앱 일반 경로의 실제 장애는 없었음** | 미지정 14곳에 `encoding="utf-8"` 명시(#116), AST 회귀 시험. 한국어 로케일 재현: em dash·히브리어·폴리토닉 헬라어는 기본 인코딩에서 실패 |
| **레지스트리 교체 경합** | **★ 미해소 · 가장 의심되는 위험** | 아래 §1.1 |
| `hunspell`(맞춤법) | Windows용 wheel 없음 | 소스 빌드 필요. **없어도 안전**: 대체 엔진(no-op)으로 넘어가 맞춤법 검사만 꺼짐. 이 절차는 설치에서 제외한다 |
| `tesseract`·`poppler` | 별도 설치 필요(선택) | 스캔 PDF OCR에만 필요 |
| 설치기 | **없음** | 위 §0 |

### 1.1 가장 중요한 미해소 위험: 레지스트리 교체 경합

`core/identity_registry.py`는 문서 레지스트리를 `.tmp`에 쓴 뒤 `os.replace`로 교체한다. macOS에서는 교체가 읽는 쪽에 원자적으로 보이지만 **Windows에서는 다른 곳이 그 파일을 열고 있으면 교체가 `PermissionError`로 실패**할 수 있다. 문제는 그 뒤 처리다.

- `save_identity_registry`는 `OSError`(`PermissionError` 포함)를 **조용히 삼키고 `False`를 반환**한다. 호출 22곳 중 **반환값을 확인하는 곳은 5곳**이고, 백그라운드 인덱서(`index_orchestrator.py` 3곳)·`processing.py`·`raw_hygiene.py`는 무시한다 → 저장이 **소리 없이 사라질** 수 있다.
- `load_identity_registry`는 `OSError`가 나면 **빈 레지스트리를 반환**한다("손상 → 재구성"). Windows에서 교체 순간에 읽기가 걸려 빈 레지스트리를 받고 그 위에 읽기→수정→저장이 이어지면 실제 레지스트리를 덮어쓸 수 있다.
- `load_identity_registry` 호출은 실제 26곳이고, 같은 함수 안의 `with registry_lock(...)` 블록 안은 5곳, **밖은 21곳**이다(AST 분류: `ui/pages/library.py` 6, `core/index_orchestrator.py` 3, `ui/pages/dashboard.py` 3 등 — 화면 렌더링과 5초 주기 백그라운드 인덱서가 동시에 동작). 한계: 호출 지점의 *상위 함수*가 이미 잠금을 쥔 경우는 이 분류가 구분하지 못하므로 '밖 21곳'은 상한에 가까운 추정이다.

과거에 문서 49건이 오류도 로그도 없이 사라진 사고(2026-08-23)와 같은 유형이다. **점검 `08`이 이것을 직접 센다.** macOS에서는 0건이며, 실패를 인위적으로 주입한 대조 실험에서는 `WARN`으로 저장 실패와 빈 읽기를 정확히 잡는 것을 확인했다.

## 2. 필요한 환경

| 항목 | 요건 |
|---|---|
| OS | Windows 10 22H2 또는 Windows 11, **x64**. (Windows on ARM은 범위 밖) |
| **로케일** | **한국어 Windows 권장.** 인코딩 결함은 시스템 로케일이 UTF-8이 아닐 때만 드러난다. 점검 `01`이 로케일 인코딩을 기록하며, `utf-8`이면 인코딩 시험의 의미가 약해진다고 경고한다. 확인: "제어판 → 국가 또는 지역 → 관리자 옵션 → 시스템 로케일 변경 → **Beta: 세계 언어 지원을 위해 Unicode UTF-8 사용**"이 **꺼져 있어야** 한다 |
| 메모리 / 디스크 | 16GB 이상 권장 / 여유 40GB 이상 (PyTorch 등 수 GB + 모델 약 6GB) |
| 네트워크 | github.com, pypi.org, ollama.com |
| 권한 | 일반 사용자 계정(대부분). 일부 설치는 관리자 승인을 요구할 수 있다 |
| 경로 | **짧은 경로**(`C:\dbma`)와 **한글·공백이 든 경로**(`C:\Users\<한글이름>\...`) 두 가지로 한 번씩 (§4.5) |
| 금지 | 실제 개인 자료·계정·API 키 사용 금지. 소형 샘플 문서만 사용 |

## 3. 준비 (PowerShell)

모든 터미널 출력은 **단계마다 새 파일명**으로 저장한다(덮어쓰기 사고 방지). 결과 폴더를 먼저 만든다.

```powershell
New-Item -ItemType Directory -Force C:\dbma-win-results | Out-Null
```

**P1. 환경 기록**

```powershell
winver
chcp
Get-Culture | Format-List Name, DisplayName
(Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem').LongPathsEnabled
```

기록: Windows 버전·빌드, 활성 코드 페이지(`chcp` — 한국어면 949), 로케일, 긴 경로 사용 여부.
`LongPathsEnabled`가 `0`이면 PyTorch·docling 설치 중 경로 길이 오류가 날 수 있다. 그대로 시험하되 실패 시 이를 원인 후보로 기록하고, 켠 뒤(관리자 권한 필요) 재시도한다.

**P2. Python 3.11, Git**

```powershell
winget install -e --id Python.Python.3.11
winget install -e --id Git.Git
py -3.11 --version
git config --global core.longpaths true
```

**P3. 코드 받기** (정확한 커밋을 기록한다)

```powershell
git clone --branch dev/dbma-engine https://github.com/nkbang/DBMA.git C:\dbma\DBMA
cd C:\dbma\DBMA
git rev-parse HEAD
```

`git rev-parse HEAD`가 `1b50181f…` 이거나 그 이후 커밋이어야 한다(`git merge-base --is-ancestor 1b50181f HEAD`가 성공). **`scripts\windows\verify_windows_readiness.py`가 없으면**: 이 도구가 아직 `dev`에 병합되지 않은 것이다. 파일을 따로 받아 같은 경로에 두면 된다.

**P4. 가상환경** (활성화 스크립트를 쓰지 않는다 — 실행 정책 오류를 피하기 위해 항상 `venv`의 `python.exe`를 직접 호출한다)

```powershell
py -3.11 -m venv C:\dbma\venv
C:\dbma\venv\Scripts\python.exe -m pip install --upgrade pip
```

**P5. 의존성 설치 (`hunspell` 제외)**

`requirements.txt`의 `hunspell`은 Windows에서 빌드되지 않으므로 그 줄만 뺀 사본으로 설치한다.

```powershell
C:\dbma\venv\Scripts\python.exe -c "import io; src=io.open('requirements.txt',encoding='utf-8').read().splitlines(); io.open('requirements.windows.txt','w',encoding='utf-8',newline='\n').write('\n'.join(l for l in src if not l.strip().lower().startswith('hunspell'))+'\n')"
cmd /c "C:\dbma\venv\Scripts\python.exe -m pip install -r requirements.windows.txt pytest > C:\dbma-win-results\pip_install_attempt1.txt 2>&1"
echo $LASTEXITCODE
```

- 수 GB를 받으므로 오래 걸린다. 끝나면 `pip_install_attempt1.txt` 끝부분을 확인한다.
- 실패하면 **어느 패키지에서, 어떤 오류로** 실패했는지를 기록하고 재시도는 새 이름(`attempt2`)으로 저장한다. 소스 빌드가 필요한 패키지(`kiwipiepy-model` 등)는 Visual C++ 빌드 도구가 없으면 실패할 수 있다 — 그 경우 이것이 이 앱의 Windows 설치 장벽이므로 **결함으로 기록**한다.

**P6. Ollama와 모델**

```powershell
# https://ollama.com/download 에서 OllamaSetup.exe(약 1.5GB) 설치 후
ollama --version
ollama pull bge-m3
ollama pull llama3.1:8b
```

메모리가 8GB 미만이면 `llama3.2:3b`를 쓴다(설치기가 쓰는 메모리 등급과 동일). 모델이 없으면 자동 점검 `04`가 `WARN`을 낸다.

**P7. (선택) OCR 구성 요소** — Tesseract(UB Mannheim 빌드)와 Poppler for Windows를 설치하고 `PATH`에 추가. 없어도 나머지 시험은 진행되며 점검 `03`이 "OCR 제한"으로 기록한다.

## 4. 실행

### 4.1 자동 점검 (핵심)

```powershell
cd C:\dbma\DBMA
C:\dbma\venv\Scripts\python.exe scripts\windows\verify_windows_readiness.py --out C:\dbma-win-results\run1
```

- 약 5~10분 걸린다(의존성 임포트가 가장 오래 걸린다). `--out`은 **새 폴더**여야 하며 내용이 있으면 스크립트가 중단한다.
- 레지스트리 경합 시험은 기본 12초이다. 더 길게 보려면 먼저 `$env:STRESS_SECONDS = "60"`.
- 결과: `REPORT.md`(요약), `results.json`, `logs\`(점검별 상세). 종료 코드는 FAIL이 있으면 1이다. **WARN은 종료 코드에 영향이 없으므로 `REPORT.md`를 반드시 읽을 것.**

| ID | 점검 | 합격 기준 | 실패/경고의 의미 |
|---|---|---|---|
| 01 | 환경 | (기록) | 로케일이 UTF-8이면 인코딩 시험 의미 약화, Python 3.11이 아니면 표시 |
| 02 | 의존성 | 필수 15개 임포트 성공 | FAIL: 어느 패키지인지가 Windows 설치 장벽 |
| 03 | 외부 실행 파일 | `ollama` 존재 | OCR 구성 요소 없음은 정보로만 기록 |
| 04 | Ollama 서버 | 응답 + `bge-m3` + 생성 모델 | WARN: 생성·임베딩 시험을 못 함 |
| **05** | **`import ui.app`** | **성공** | **FAIL이면 #117의 목적이 Windows에서 달성되지 않은 것(최우선 결함)** |
| 06 | 파일 잠금 | 스레드·프로세스 상호 배제, 예외 후 해제, 한글 경로 | FAIL: `filelock`/`msvcrt` 경로 결함 |
| 07 | 인코딩 왕복 | 히브리어·폴리토닉 헬라어·한글·em dash 보존 | FAIL: 로케일 인코딩 결함이 앱 경로에 남아 있음 |
| **08** | **레지스트리 교체 경합** | **저장 실패 0, 빈 읽기 0** | **WARN이면 §1.1의 위험이 실제로 관찰된 것 — 조치 필요** |
| 09 | Streamlit 기동 | `/_stcore/health` = ok | FAIL: 서버가 안 뜸 |
| 10 | 6개 페이지 렌더링 | 예외 0, 페이지 선택값 일치 | FAIL: 화면 결함. WARN(선택값 불일치): 메뉴 키 변경 |
| 11 | Windows 관련 시험 5개 파일 | 전부 통과 | FAIL: 시험이 Windows에서 실패 |

### 4.2 수동 확인 (사람 눈)

자동 점검이 못 보는 것이다. 각 항목의 **스크린샷**을 `C:\dbma-win-results\manual\`에 새 이름으로 저장한다.

```powershell
cd C:\dbma\DBMA
C:\dbma\venv\Scripts\python.exe -m streamlit run dbma_ui.py --server.port 8520
```

브라우저에서 `http://localhost:8520`:

| ID | 확인 | 합격 기준 |
|---|---|---|
| M1 | 첫 화면 | 온보딩이 표시되고 오류 화면(빨간 traceback)이 없다 |
| M2 | 사이드바 6개 페이지(홈, 내 서재, 자료 등록, 연구·채팅, 설교 준비, 도움말) | 모두 열리고 한글이 깨지지 않는다 |
| M3 | "연구·채팅"에 "내서재 공개 자료" 섹션 | **보이지 않는다**(기본 비활성) |
| M4 | 검색창에 한글·히브리어(`בראשית`)·폴리토닉 헬라어(`ἐν ἀρχῇ`) 입력 | 입력·표시가 보존된다 |
| M5 | 소형 샘플 텍스트(한글+히브리어+헬라어 포함)를 "자료 등록"으로 처리 | 오류 없이 처리되고, 처리 후 "내 서재"에 나타난다 |
| M6 | 질문 1건 | 답변이 생성되고 출처가 표시된다. **걸린 시간을 기록**(Ollama 가속 여부에 따라 다름) |
| M7 | 맞춤법 기능(설교 준비) | 오류 없이 지나간다(`hunspell` 없음 → 검사만 꺼짐이 **정상**) |
| M8 | 앱을 종료(Ctrl+C) 후 재실행 | 이전에 처리한 자료가 남아 있다 |

### 4.3 전체 시험 (선택)

```powershell
C:\dbma\venv\Scripts\python.exe scripts\windows\verify_windows_readiness.py --out C:\dbma-win-results\run-full --with-full-tests
```

시험 약 290개 파일을 실행한다(1시간 이상 걸릴 수 있다). **실패가 있어도 결함으로 단정하지 말고 분류한다.** 정적 점검상 Windows 가정이 있는 시험은 소수다:

| 가정 | 해당 파일 수 | 기대 |
|---|---:|---|
| `/tmp/` 하드코딩 | 3 | Windows에서 실패 가능 → 시험의 이식성 문제로 분류 |
| `/Users/` 하드코딩 | 1 | 〃 |
| `chmod`/권한 | 5 | 〃 (Windows는 권한 모델이 다름) |
| `.sh` 스크립트 실행 | 1 | 〃 |
| 위 외의 실패 | — | **앱 결함 후보** — 파일명과 오류를 그대로 기록 |

### 4.4 반복과 변수 (안정성)

- 4.1을 **세 번** 실행한다(`run1`, `run2`, `run3`). 점검 `08`이 매번 같은 결과인지가 중요하다. 간헐적으로만 `WARN`이 나오면 그것이 실제 사용에서 일어나는 경합의 양상이다.
- **Windows Defender 실시간 검사가 파일 열림 시간을 늘려** 교체 충돌을 증폭시킬 수 있다. 다음 두 조건을 모두 `08`로 비교한다: (a) 기본 상태, (b) 실시간 보호를 일시 중지한 상태(**비교용으로만, 시험 후 반드시 다시 켠다**).
- 긴 경합 시험: `$env:STRESS_SECONDS = "120"` 후 한 번 더.

### 4.5 경로 변수

4.1~4.2를 **한글·공백이 든 경로**에서도 한 번 수행한다(예: `C:\Users\홍길동\내 문서\dbma-test`로 클론·venv 생성). 점검 `06`이 한글 경로의 잠금을 보지만, 앱 전체의 한글 경로 동작은 이 반복에서만 드러난다.

## 5. 판정

| 판정 | 조건 |
|---|---|
| **PASS** | 자동 점검 `01~11`이 FAIL 없이 끝나고, `08`이 `PASS`(세 번 모두), 수동 M1~M8 통과 |
| **조건부 PASS** | FAIL 없음 + `08`이 `WARN` → **알려진 위험이 실제로 확인된 것.** 기능은 돌지만 레지스트리 유실 위험이 있어 §6 조치 전에는 배포 불가 |
| **FAIL** | `05`, `06`, `07`, `09`, `10`, `11` 중 하나라도 FAIL, 또는 M1~M5 불통과 |
| **BLOCKED** | 환경 문제로 판정 불가(설치 실패, 네트워크). 어느 단계에서 어떤 오류인지 기록 |

각 항목은 **무엇이 관찰됐는지**와 **무엇을 근거로 판정했는지**를 구분해서 적는다. 추측으로 채우지 않는다.

## 6. 결과가 나쁠 때의 후속 조치 (제안, 이 절차에서는 수행하지 않는다)

| 관찰 | 후속 |
|---|---|
| `08` WARN | `save_identity_registry`에서 `os.replace`를 `PermissionError`에 대해 짧은 백오프로 재시도, 실패 시 예외를 전파하거나 호출자가 확인하도록 변경; `load_identity_registry`가 일시적 `OSError`와 "파일 없음/손상"을 구분해 **빈 레지스트리를 반환하지 않도록** 재설계; 잠금 밖의 읽기(약 21곳)가 같은 잠금을 쓰도록 검토. 별도 PR·승인 필요 |
| `05` FAIL | 임포트 실패 지점을 확인(다른 POSIX 전용 모듈, 경로, 의존성 로드 순서) — 최우선 |
| `02` FAIL | 실패 패키지의 Windows wheel 부재 여부 확인 → 대체 또는 선택 의존성화 |
| 설치 장벽(빌드 도구 필요 등) | 배포 형태(설치기)의 설계에 반영 — 이 절차의 결과가 설치기 설계의 입력이 된다 |

## 7. 증거 회신

다음을 압축해서 전달한다. **각 파일은 원본 그대로**여야 한다(콘솔에서 옮겨 적은 사본은 신뢰도가 낮다).

```powershell
Compress-Archive -Path C:\dbma-win-results\* -DestinationPath C:\dbma-win-results-bundle.zip
```

- `run1`, `run2`, `run3`(`REPORT.md`, `results.json`, `logs\`), `pip_install_attempt*.txt`
- 수동 확인 스크린샷(`manual\`), P1 환경 기록(`chcp`·로케일·`winver`·`LongPathsEnabled`)
- 사용한 커밋 해시(`git rev-parse HEAD`)와 평가자·일시·기기 사양
- 사용자 이름이 경로에 들어간 파일이 있으면 공유 전에 확인

## 8. 부록: 문제 해결

| 증상 | 대응 |
|---|---|
| `이 시스템에서 스크립트를 실행할 수 없으므로…` | 활성화 스크립트(`Activate.ps1`)를 쓰지 말고 `C:\dbma\venv\Scripts\python.exe`를 직접 호출한다 |
| pip 설치 중 경로가 너무 길다는 오류 | `LongPathsEnabled`를 1로(관리자), `git config --global core.longpaths true`, 더 짧은 경로(`C:\dbma`) |
| 8520 포트가 사용 중 | `--server.port 8521` |
| 점검 `09`가 120초 안에 응답 없음 | `logs\09_streamlit_server_output.txt`의 마지막 줄을 확인 |
| 콘솔 글자가 깨져 보임 | 정상일 수 있다. 결과 파일(`REPORT.md`)은 UTF-8로 저장된다 |
