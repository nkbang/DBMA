# End-User Package — Gate 2 Automation Protocol (CUE ⇄ C1)

- 작성: CUE, 2026-08-17
- 성격: 설계 문서(코드 스캐폴딩 스펙) — 이 문서 자체는 코드/시스템 변경 없음
- 근거: HQ 제안(2026-08-17) + Gate 1/2A/Phase1에서 확인된 실제 저장소 사실

---

## 0. HQ 제안과 실제 저장소의 차이 (정정)

HQ 제안이 언급한 tripwire 대상 `incremental_state.json`, `registration_state.json`은
**이 저장소에 존재하지 않는다**(`find` 결과 0건). 실제 production 상태 파일로 대체:

| HQ 제안 | 실제 대체 |
|---|---|
| `incremental_state.json` hash | `NAE/corpus/tsu/tsu_id_state.json` hash |
| `registration_state.json` hash | `{DEFAULT_OUTPUT_DIR}/registry/documents.json` hash (via `core.config.DEFAULT_REGISTRY_PATH`) |
| TSU dataset hash | `output/bench/tsu_dataset.jsonl` hash (`core.config.DEFAULT_TSU_DATASET_PATH`) |
| Qdrant collection state | `nae_qdrant`(포트 7333) point count만 — `dbma_qdrant`는 ADR-003에 따라 production에서 쿼리되지 않으므로 감시 대상에서 제외(단, 존재 자체는 확인) |

또한 "9-page UI validation"(HQ §6, §Phase 6)의 페이지 수가 HQ 메시지 내에서 9개와 10개(Onboarding 포함 여부)로 오락가락한다. **Gate 1 G2가 README에 공식화한 9개는 Onboarding을 제외한다**(Dashboard/Library/Processing/Research/Chat/설교문 작성/설교 리뷰/Monitor/도움말). Onboarding은 "최초 실행 화면"으로 별도 검증 항목으로 둔다 — README 계약과 어긋나지 않게 manifest를 이 기준으로 고정한다.

---

## 1. 역할 분리 (HQ §10/§11 채택, 이 저장소 맥락으로 구체화)

| 영역 | 담당 | 근거 |
|---|---|---|
| Orchestrator/validator 스크립트 실제 작성(`scripts/gate2/*`) | **C1** | 기계적·well-specified 구현, CLAUDE.md "C1 Task Order" 패턴과 이번 세션 전례(Citation UI, installer 수정 등)와 동일 |
| Protected-files/tripwire 스펙 설계, EXPECTED_PAGES manifest 확정 | **CUE(나)** | 이 문서 §0/§2에서 이미 확정 — C1에게 그대로 지시 |
| C1 구현 결과 독립 재실행·검증, evidence 원본 대조 | **CUE(나)** | 기존 세션 전체와 동일 패턴 |
| GREEN/HOLD/RED 게이트 최종 판정 | **CUE(나)** | HQ §10 "CUE 승인 필요" |
| 실제 clean install/reinstall/uninstall **실행**(brew 설치, GB급 모델 다운로드, 파일시스템 변경 동반) | **사용자 승인 후 CUE 또는 C1이 실행** | 아래 §4 참고 — 스크립트 작성과 스크립트 실행은 별개 승인 단계로 분리 |
| Brand/naming/policy/최종 릴리스 승인 | **Human HQ** | 기존 확립된 원칙 유지 |

---

## 2. Orchestrator 구조 (HQ 제안 채택, 경로/대상만 실제 저장소 기준으로 확정)

```
scripts/gate2/
├── 00_baseline.sh          # Phase 0 — Gate 1 상태(598fbdc)/clean working tree 확인
├── 10_packaging_audit.py   # Phase 1 재실행 가능한 형태 — .gitattributes export-ignore 검증 포함
├── 20_build.sh             # scripts/build_mac_package.sh 래핑, artifact 해시 기록
├── 30_package_integrity.py # 태그 tarball 실제 다운로드 → NAE//.automation//test_seal_* 0건 검증(이미 rc4로 확인한 절차를 스크립트화)
├── 40_clean_install.sh     # /tmp/dbma-gate2-run-<id>/ 격리 환경에서만 실행 — §4 승인 필요
├── 50_runtime_smoke.py     # streamlit headless 기동 + HTTP 응답
├── 60_ui_pages.py          # EXPECTED_PAGES manifest(9개, §0 기준) 실제 import
├── 61_citation_ui.py       # response.citations[i]<->top_k_results[i] 대응 + author/source_title 렌더 확인(G4 재검증)
├── 70_production_isolation.py  # §3 tripwire — BEFORE/AFTER 해시 비교
├── 80_reinstall_upgrade.sh # §4 승인 필요
├── 90_uninstall.sh         # §4 승인 필요 — 현재 우선순위: uninstall 스크립트 자체가 없음(Phase1에서 미발견), 이번에 신규 작성
├── 95_evidence_verify.py   # 각 JSON evidence의 command/output이 실제 재실행 결과와 일치하는지 대조
└── gate2_orchestrator.py   # 위 전부를 순서대로 호출, GATE2_STATUS=GREEN|HOLD|RED 산출
```

각 스크립트는 HQ 제안 형식대로 `evidence/gate2/<run-id>/<phase>.json`에
`{test, status, command, started_at, finished_at, stdout_sha256, artifacts}`를 남긴다.
`SUMMARY.md`는 실행 결과에서 **자동 생성**(사람이 손으로 안 쓴다 — HQ 원칙 그대로 채택, DoD#7 evidence 오류 재발 방지).

---

## 3. Protected files / Production tripwire (선언적 관리, HQ §5 채택)

```yaml
# scripts/gate2/protected.yaml (C1이 생성할 파일 — 이 문서가 스펙)
protected_files:
  - core/retrieval.py
  - pyproject.toml

production_state_watch:
  - path: output/bench/tsu_dataset.jsonl
    method: sha256
  - path: output/bench/tsu_manifest.json
    method: sha256
  - path: NAE/corpus/tsu/tsu_id_state.json
    method: sha256
  - path: "{DEFAULT_OUTPUT_DIR}/registry/documents.json"
    method: sha256
  - qdrant_collection: nae_tsu_v1
    host: "localhost:7333"
    method: point_count
```

`70_production_isolation.py`는 BEFORE/AFTER 스냅샷을 비교해 하나라도 달라지면
**즉시 `GATE2_STATUS=RED`**(HQ 원칙 그대로) — 이건 테스트가 아니라 tripwire.
`core/retrieval.py`/`pyproject.toml`이 git diff에 나타나면 별도로
`ARCHITECTURE_FREEZE=FAIL`을 산출해 RED와 별개로 로그에 남긴다(원인 구분용).

---

## 4. ⚠️ 실행 단계 분리 — "스크립트 작성"과 "스크립트 실행"은 다른 승인

HQ 제안의 §1~§9는 전부 자동화 대상이 맞지만, 이 중 다음은 **실제 실행 시 사용자의 로컬
macOS 시스템을 변경**한다(Homebrew 패키지 설치, Ollama로 수 GB 모델 다운로드,
`~/내서재_베타` 또는 `/tmp/dbma-gate2-run-*` 디렉터리 생성, 백그라운드 서버 기동):

- `40_clean_install.sh` (Phase 5)
- `80_reinstall_upgrade.sh` (Phase 8)
- `90_uninstall.sh` (Phase 9)

**방침**: C1은 이 세 스크립트를 **작성**하는 것까지는 이번 Task Order 범위에 포함한다.
다만 **처음 실제로 실행하는 것은 별도 확인 후에만** 한다 — 스크립트 문법 검증(`bash -n`,
`python -m py_compile`)과 dry-run 플래그(`--dry-run`, 실제 brew/curl/ollama 호출 없이
명령어만 echo)까지는 자동 진행하되, 실제 네트워크/설치 호출이 나가는 첫 실행은 CUE가
결과를 사용자에게 보고하고 승인받은 뒤 진행한다. `10/30/50/60/61/70/95`(읽기 전용 조사·
로컬 headless 기동·해시 비교)는 production mutation이 없으므로 바로 자동 실행 가능.

이 분리는 "자동화 = 전부 자동 승인"이 아니라는 HQ §10 원칙과, 제 시스템 프롬프트의
"시스템 설정 변경/패키지 설치 등은 되돌리기 어려운 행동" 원칙 둘 다를 만족시킨다.

---

## 5. C1 ⇄ CUE 협업 절차 (매 스크립트 묶음마다 반복)

1. CUE가 Task Order 발행(이 문서 §2/§3을 스펙으로).
2. C1이 `scripts/gate2/*` 구현, 자체 `bash -n`/`py_compile` 통과 확인, evidence 스켈레톤 커밋.
3. CUE가 코드를 직접 읽고, §4의 읽기 전용 스크립트(`10/30/50/60/61/70/95`)는 **직접 재실행**해서
   evidence와 실제 출력이 1:1 일치하는지 확인(이번 세션에서 DoD#7 때 썼던 방식 그대로 — 이게
   "교차검증"의 핵심 메커니즘).
4. `40/80/90`은 코드 리뷰 + dry-run 결과만 확인, 실제 실행은 보류.
5. CUE가 GREEN/HOLD/RED 및 필요한 정정 목록을 보고 → 사용자 승인 → (승인 시) 실제 실행 1회 진행.

---

## 6. 이번에 C1에게 넘길 범위 (1차 Task Order)

`scripts/gate2/` 스캐폴딩 전체 작성 + `protected.yaml` + `gate2_orchestrator.py`.
**`40/80/90`은 코드만 작성, 실행 금지**(§4). 나머지는 작성 후 orchestrator가 자동
호출해도 되지만, 최초 1회는 CUE가 별도로 직접 재실행해 검증한다.
