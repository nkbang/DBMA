# NAE THEOLOGY CORPUS — RESUME-POINT RECOVERY

**작업명**: 조직신학(Baptist Confessions) Corpus Acquisition/Validation — Resume-Point Recovery
**작성자**: CUE
**작성일**: 2026-08-26
**Mode**: READ-ONLY RECOVERY — 이 문서는 어떤 acquisition/processing도 수행하지 않는다.
**Mutation Budget**: Code 0 / Corpus 0 / TSU 0 / Embedding 0 / Qdrant 0 / Manifest 0 / Registry 0 / Git add NO / Git commit NO

---

## 1. Executive Summary

과거 조직신학(Baptist confessions) corpus acquisition 작업의 마지막 검증된 상태는
**STEP5-C(2026-07-31), 판정 `WAITING_FOR_SOURCE`, 대상 `NHBC1833`(New Hampshire
Baptist Confession 1833, 파일명 `nhc_1833.txt`)** 이다. Repository를 재확인한
결과 이 상태는 **오늘(2026-08-26)까지 변경되지 않았다** — `data/nae/sources/baptist/`는
여전히 `.gitkeep`만 있고 원문 파일이 없다.

다만 조사 중 **historical resume point 자체가 가리키는 트랙과, 실제로 이후
진행된 작업 트랙이 서로 다르다**는 중요한 사실을 발견했다. NHBC1833이 속한
`source_candidates.csv` 기반 STEP5 registry 파이프라인(PREPARED→ACQUIRED→
VERIFIED→INGESTED)은 2026-07-31 이후 **완전히 정지**했고, 그 대신 별도의
`NAE/corpus/raw/archive_org/` 기반 파이프라인(Internet Archive 직접 스크레이핑
→ canonical 정규화)이 2026-08-01~02에 **SLBC1689**(Second London Baptist
Confession 1689)와 **PBC1742/PBC1765**(Philadelphia Baptist Confession)를
처리했다. 즉 같은 "Baptist confession corpus" 범주 안에서 두 개의 서로 다른
acquisition 메커니즘이 조율 없이 존재했고, NHBC1833은 그 어느 쪽으로도 진행되지
않은 채 방치되어 있다.

localhost:8799 모니터는 현재 이 어느 트랙에 대해서도 활성 신호를 주지 않는다
(`C1 STOPPED`, `no active volume`) — 이는 repository 상의 "정지 상태"와
일치하며 divergence가 없다.

---

## 2. Investigation Scope

**IN SCOPE**: localhost:8799 모니터 조사, repository/filesystem 증거 수집,
NHBC1833 identity/acquisition/canonicalization/TSU/embedding 상태 확인, 관련
Baptist confession 자료(SLBC1689/PBC1742/PBC1765/BFM2000/TH1612/JS1608/AF1815)
상태 확인, historical timeline 복원, monitor↔repository reconciliation.

**OUT OF SCOPE (수행하지 않음)**: 신규 후보 발굴, 신규 acquisition, 신규
processing 실행, 기존 문서 수정, 발견된 불일치의 직접 해결, git add/commit.

---

## 3. localhost:8799 Monitor Evidence

접속 시각: 2026-08-26 13:26 (모니터 자체 표시 기준)

| 항목 | 값 |
|---|---|
| Title | NAE Observatory (내서재 작업현황모니터) |
| C1 | **STOPPED** |
| TSU Pipeline | 상태 라벨만 표시, 세부 활성 신호 없음 |
| Ollama | ONLINE |
| GPU | HEALTHY, 0% 사용률, VRAM 1.0/137.4GB |
| n8n | ONLINE |
| Pipeline Status | **"no active volume"**, 0.0%, 0/0, throughput 0/hour |
| NAE Queue | VOL.01 COMPLETE / VOL.02~08 QUEUED |
| 최근 이벤트 | n8n·Ollama 재연결 이벤트만 존재 (오늘 새벽), NAE/조직신학/NHBC1833 관련 텍스트 없음 |

**판정**: 모니터는 NHBC1833이나 Baptist confession 트랙에 대해 어떤 구체적
정보도 노출하지 않는다("VOL.01~08" 큐는 이 corpus와 무관한 별도 볼륨 처리
현황으로 보이며, 본 조사에서 그 정체를 추가로 특정하지 않았다 — scope 밖).
**"현재 아무 acquisition도 실행 중이 아니다"**는 사실만 신뢰성 있게
확인되며, 이는 repository 증거와 **일치**한다.

---

## 4. Repository / Filesystem Evidence

### 4.1 STEP5 registry 트랙 (NHBC1833이 속한 트랙)

```
data/nae/sources/baptist/   → .gitkeep 뿐, nhc_1833.txt 없음
data/nae/sources/theology/  → .gitkeep 뿐
data/nae/sources/commentary/→ .gitkeep 뿐
data/nae/sources/public_domain/ → .gitkeep 뿐
```

`resources/theological_sources/baptist/source_candidates.csv` (committed,
STEP5 이전부터 존재) — 7건 후보, 전부 `local_path: null` (다운로드 안 됨).

`resources/theological_sources/baptist/source_manifest.yaml` — NAE-SOURCE-003
(2026-07-31)에서 생성. 상태:

| source_id | status(manifest) | priority |
|---|---|---|
| SLBC1689 | approved_for_acquisition | P0 |
| PBC1742 | approved_for_acquisition | P0 |
| **NHBC1833** | **approved_for_acquisition** | **P0** |
| TH1612 | approved_for_acquisition | P1 |
| AF1815 | approved_for_acquisition | P1 |
| BFM2000 | permission_required (저작권 제한) | P0 |
| JS1608 | verification_pending | P1 |

`approved_for_acquisition`은 이 manifest 자체의 5단계(STEP5 registry의
PREPARED/ACQUIRED/VERIFIED/INGESTED와 **병존하는 별도 enum**)일 뿐, 실제
파일 확보와 무관 — "수집 승인됨, 아직 수집 안 됨"을 의미한다.

### 4.2 archive_org / canonical 파이프라인 트랙 (실제 진행된 트랙)

```
NAE/corpus/raw/archive_org/  → AF1815/, PBC1742/, TH1612/, church_order/,
                                 missions/, reference/ (NHBC1833, SLBC1689
                                 디렉터리 없음 — raw 파일 자체가 없음)
NAE/corpus/canonical/SLBC1689/canonical.txt, canonical.json,
                                normalize_report.json
                                → status: "ok", 2026-08-01, 157 pages,
                                  121,005자, TSU/embedding 미착수
NAE/corpus/canonical/PBC1742/normalize_report.json
                                → status: "failed", reason:
                                  "no_extractable_source", 2026-08-01
NAE/corpus/canonical/PBC1765/canonical.txt/.json + quarantine/PBC1765/
                                → canonicalization 완료 (별도 identifier
                                  불일치 이슈를 CUE가 2026-08-01 admit)
NAE/corpus/tsu/                → Dagg_Church_Order, Fuller_Complete_Works_Vol01,
                                  Hiscox_Standard_Manual만 존재 —
                                  SLBC1689/PBC1742/PBC1765/NHBC1833 전부
                                  TSU 디렉터리 없음
```

이 트랙을 만든 커밋: `e88b083 Commit outstanding canonical pipeline outputs
and manifest status fix` (2026-08-02). 이 트랙은 `source_candidates.csv`나
STEP5 registry 문서 체인을 참조하지 않고 Internet Archive에서 직접
raw 파일을 확보해 canonical 파이프라인으로 넣은 것으로 보인다(정확한
acquisition 경위 문서는 이번 조사에서 발견하지 못함 — `evidence/phase5_2/`
아래 관련 기록이 있을 수 있으나 이번 조사 범위를 넘어 전수 확인하지 않음).

**결론**: NHBC1833은 두 트랙 어디에도 물리적 파일이 존재하지 않는다.
SLBC1689는 canonicalization까지 진행(TSU 미착수). PBC1742는
canonicalization 실패(`no_extractable_source`) 상태로 정지.

### 4.3 identity_registry / Qdrant

`identity_registry.json` 데이터 파일 자체가 저장소에 없음(코드
`core/identity_registry.py`만 존재, 경로는 `core/config.py`의
`DEFAULT_REGISTRY_PATH`로 런타임에 결정됨 — 환경 미설정으로 이번 조사에서
직접 조회하지 못함). 단, TSU 단계에 도달한 자료가 없으므로(§4.2) INGESTED
단계(§STEP5_REGISTRY_TRANSITION.md 기준 registry 기록의 전제조건)에는
NHBC1833/SLBC1689/PBC1742 어느 것도 도달하지 못했다고 **간접적으로 확실히
판정**할 수 있다. Qdrant vector index에 대해서도 동일 — embedding 이전
단계이므로 색인 존재 가능성 없음.

---

## 5. Governing Documents

| 문서 | 상태 | 이 조사와의 관계 |
|---|---|---|
| `docs/tasks/reports/STEP5C_REPORT.md` (2026-07-31) | NHBC1833 최후 검증 상태 = `WAITING_FOR_SOURCE` | **historical resume point 원본** |
| `docs/tasks/reports/STEP5_REGISTRY_TRANSITION.md` (2026-07-31) | PREPARED→ACQUIRED 절차 명세, "현재 PREPARED" | NHBC1833의 절차적 위치 정의 |
| `docs/NAE_SOURCE_REGISTRY_REPORT.md` (2026-07-31, NAE-SOURCE-003) | 7건 manifest 생성, `local_path: null` 확인 | NHBC1833이 `baptist-confession-001`(구) ↔ `NHBC1833`(신) 두 source_id 체계로 병존한다고 명시 — **미해결 alias 이슈로 기록됨, 이번 조사에서 임의 통합하지 않음** |
| `docs/NAE_CORPUS_INVENTORY_REVIEW_001.md` (2026-08-02) | archive_org 전역 스캔 결과 문서 | **주의**: 이 문서의 "books: NHBC1833/PBC1742/PBC1765/SLBC1689/TH1612/AF1815 6건" 카탈로그는 §4.2 실제 디렉터리 스캔과 불일치(NHBC1833/SLBC1689 raw 디렉터리 없음) — 이 문서는 stale하거나 다른 시점의 스냅샷을 반영한 것으로 판단, **repository 실제 상태를 우선**함(§9 authority rule 적용) |
| `docs/architecture/ADR-029-NAE-Research-Corpus-Expansion-Pipeline-Lock.md` (ACCEPTED, 2026-08-25) | 최신 governance | Baptist confession 트랙을 **직접 참조하지 않음** — 별도 스코프(§7 참고) |
| `docs/agents/cue/CUE-PHASE1-ADR029-GATE-RECONCILIATION-TRUE-BLOCKER-AUDIT.md` (2026-08-26, 오늘) | 최신 CUE 감사 | §13.4에서 이 Baptist 트랙을 "ADR-029 밖의 별개 트랙"으로 명시적으로 분류, "세 트랙 조율 없음"을 HQ decision 필요 항목으로 지적 — **이번 보고서와 판정 일치** |

---

## 6. Historical Timeline

```
2026-07-30 이전  Candidate Selection — source_candidates.csv 작성(7건, P0 4건)
2026-07-31       STEP4: PD verification / pilot source entry
2026-07-31       STEP5: Human Acquisition Guide, Validation Script 계획,
                 Registry Transition 절차 작성
2026-07-31       NAE-SOURCE-003: source_manifest.yaml 생성(7건, 전부
                 local_path null)
2026-07-31       STEP5-C: WAITING_FOR_SOURCE 판정 (NHBC1833 대상) ← historical
                 resume point
─────────────────────────────────────────────────────────────────
2026-08-01       (별도 트랙 시작, STEP5 문서 체인과 연결 기록 없음)
                 SLBC1689 canonicalization 성공, PBC1742 canonicalization
                 실패("no_extractable_source"), PBC1765 identifier 불일치
                 admit 결정(HQ Advisory)
2026-08-02       archive_org corpus 전역 인벤토리 리뷰 문서 작성
2026-08-02       "Commit outstanding canonical pipeline outputs" 커밋(e88b083)
─────────────────────────────────────────────────────────────────
2026-08-09       NAE metadata schema 2 migration (TSU 대규모 재작업,
                 Baptist confession과 무관한 범위)
2026-08-25       ADR-029 승인 — Korean/English terminology 트랙 시작
                 (Baptist confession 트랙과 별개)
2026-08-25~26    EN-BAP-001/002, Korean Authority 관련 다수 CUE/C1 문서 —
                 전부 ADR-029 트랙, Baptist confession 트랙 언급 없음
2026-08-26 (오늘) 이번 resume-point recovery 조사
```

**핵심 관찰**: 2026-07-31 STEP5-C 이후 NHBC1833에 대한 어떤 추가 조치도
기록되지 않았다. 8월 초 활동은 NHBC1833이 아니라 **같은 카테고리의 다른
문서들**(SLBC1689, PBC1742, PBC1765)을 대상으로 한 것이었고, 그 활동조차
8월 2일 이후로는 중단된 것으로 보인다(SLBC1689가 TSU 단계로 넘어간 기록 없음).

---

## 7. NHBC1833 Status

| 항목 | 값 | 근거 |
|---|---|---|
| Canonical identity | New Hampshire Confession of Faith (1833) — CSV 원제: "The Confession of Faith adopted by the General Convention of Baptist, held at Antioch, in the State of New Hampshire" | `source_candidates.csv` |
| source_id (신) | `NHBC1833` | `source_manifest.yaml` |
| source_id (구, 병존) | `baptist-confession-001` | `docs/NAE_SOURCE_REGISTRY_REPORT.md` §"기존 산출물과의 source_id 불일치" — **미해결, 통합 여부 HQ 결정 필요, 이번 조사에서 변경하지 않음** |
| 지정 파일명 | `data/nae/sources/baptist/nhc_1833.txt` | `STEP5_REGISTRY_TRANSITION.md` |
| Alias/lineage | 임의 변경 없음 — 위 두 source_id 병존을 그대로 기록만 함 | 지시사항 §4 준수 |
| Acquisition 상태 | **미확보** — 파일 없음 (`.gitkeep`만 존재) | 직접 filesystem 확인 |
| Provenance | 전부 `null` (`acquired_from`/`acquired_url`/`acquired_date`) | `STEP5_REGISTRY_TRANSITION.md` 정의상 PREPARED 단계 특징과 일치 |
| Checksum | 없음(원문 없으므로 계산 불가) | — |
| Manifest 상태 | `approved_for_acquisition` (수집 승인, 미수집) | `source_manifest.yaml` |
| Registry(STEP5 4단계) | **PREPARED** (ACQUIRED로 전환된 기록 없음) | `STEP5_REGISTRY_TRANSITION.md` "현재 상태" 절 |
| Canonicalization | NOT STARTED (raw 파일 없어 canonical 파이프라인 대상 아님) | `NAE/corpus/canonical/`에 NHBC1833 디렉터리 없음 |
| TSU | NOT STARTED | `NAE/corpus/tsu/`에 NHBC1833 없음 |
| Embedding | NOT STARTED | 상동 |
| Vector index | NOT STARTED | 상동 |
| 관련 task | STEP4/STEP5 시리즈(`docs/tasks/reports/STEP4*`, `STEP5*`), NAE-SOURCE-003 | §5 |
| 관련 report | `STEP5C_REPORT.md` (최종), `NAE_SOURCE_REGISTRY_REPORT.md` | §5 |
| 관련 commit | STEP5 문서 체인 커밋(구체 SHA는 `docs/tasks/reports/` 디렉터리 커밋 이력 참고, 2026-07-31 무렵) | `git log -- docs/tasks/reports/STEP5C_REPORT.md` |

---

## 8. Related Theology Corpus Status

과거 작업에서 이미 등장했던 자료만 추적(신규 후보 발굴 아님):

| source_id | 문서 | Acquisition | Canonicalization | TSU/Embedding | 비고 |
|---|---|---|---|---|---|
| **NHBC1833** | New Hampshire Confession (1833) | NOT STARTED | NOT STARTED | NOT STARTED | 본 조사 주 대상, §7 |
| **SLBC1689** | Second London Baptist Confession (1689) | DONE (archive_org 트랙) | **DONE** (ok, 2026-08-01) | NOT STARTED | STEP5 registry와 무관한 별도 트랙에서 가장 진전됨 |
| **PBC1742** | Philadelphia Baptist Confession (1742) | DONE (archive_org 트랙) | **FAILED** (`no_extractable_source`, 2026-08-01) | — | 재처리 필요 여부 미결정 상태로 방치 |
| **PBC1765** | Philadelphia Baptist Confession (1765 인쇄본) | DONE | DONE | quarantine 존재(정리 완료 여부 불명) | source_candidates.csv에는 없는 별도 identifier — HQ Advisory로 admit 결정(2026-08-01) |
| BFM2000 | Baptist Faith & Message (2000) | NOT STARTED | NOT STARTED | NOT STARTED | `permission_required`(저작권 제한) — acquisition 자체가 별도 라이선스 검토 선행 필요 |
| TH1612 | Helwys, Mystery of Iniquity (1612) | 폴더만 존재(`NAE/corpus/raw/archive_org/TH1612/`), 내용물 확인 안 됨(0 파일로 확인됨) | NOT STARTED | NOT STARTED | P1, 실제 확보 여부 불확실 — 이번 조사에서 폴더 안이 비어 있음을 확인(0 files) |
| AF1815 | Fuller, Gospel Defended 등 | 폴더만 존재, 0 파일 | NOT STARTED | — | 단, `NAE/corpus/canonical/Fuller_Complete_Works_Vol01~08`가 **별도로** 존재 — 이는 AF1815(source_candidates.csv 항목)와 동일 저자(Andrew Fuller)의 **다른 작품집**으로 추정되며, 두 표기가 같은 자료를 가리키는지는 확인되지 않음(스코프 밖, alias 정리 필요 항목으로만 기록) |
| JS1608 | Smyth, Amsterdam Church Book (1608-1614) | NOT STARTED | NOT STARTED | NOT STARTED | `verification_pending`, CSV 파싱 결함(Dutch 토큰 컬럼 밀림)까지 겹쳐 있음 |

---

## 9. Acquisition / Validation Matrix

```
Candidate Selection      → DONE      (source_candidates.csv, 7건 확정)
Source Acquisition       → BLOCKED   (NHBC1833: 0/1 확보; 트랙 전체 P0 4건 중
                                       SLBC1689만 확보, PBC1742/1765는 별도
                                       identifier로 확보, NHBC1833/BFM2000 미확보)
Identity Verification    → NOT STARTED (NHBC1833 — 원문이 없어 검증 불가)
Provenance                → NOT STARTED (NHBC1833)
Registry / Manifest      → IN PROGRESS (manifest 생성은 DONE, 상태값은
                                        approved_for_acquisition에서 정지)
Canonicalization          → NOT STARTED (NHBC1833) / DONE (SLBC1689) /
                                        FAILED (PBC1742)
TSU                       → NOT STARTED (전체 Baptist confession 트랙 공통)
Embedding                 → NOT STARTED
Vector Index               → NOT STARTED
Application Integration    → NOT STARTED
Validation                 → NOT STARTED (원문 부재로 검증 자체가 불가능)
```

---

## 10. Monitor ↔ Repository Reconciliation

| Item | Monitor | Repository | Governance | Final |
|---|---|---|---|---|
| Project | "내서재 작업현황모니터"(범용, corpus 불특정) | Baptist confession 전용 트랙 다수 문서 존재 | ADR-029는 이 트랙을 다루지 않음 | Repository 기준 채택 |
| Source | 표시 없음 | NHBC1833 (미확보) | STEP5C_REPORT.md가 명시 | NHBC1833, 미확보 |
| Stage | 표시 없음("no active volume") | STEP5 PREPARED / archive_org 트랙은 canonical 단계까지 | — | 두 트랙 모두 정지 상태 |
| Acquisition | — | NOT DONE(NHBC1833) | — | NOT DONE |
| Validation | — | NOT STARTED | — | NOT STARTED |
| TSU | — | NOT STARTED(트랙 전체) | — | NOT STARTED |
| Embedding | — | NOT STARTED | — | NOT STARTED |
| Vector Index | — | NOT STARTED | — | NOT STARTED |
| Blocker | (모니터는 blocker 자체를 표시하지 않음) | 원문 미확보(Human acquisition 필요) | — | 사람의 원문 확보 |
| Next Action | (표시 없음) | STEP5_HUMAN_ACQUISITION_GUIDE.md 절차 재개 | — | Human acquisition |

**불일치**: 모니터는 이 트랙에 대해 정보를 제공하지 않으므로 "모니터가
틀린 정보를 준다"는 의미의 divergence는 없음. 다만 **모니터가 보여주는
"VOL.01~08" 큐가 어느 corpus를 가리키는지 문서화되어 있지 않다**는 점은
모니터 자체의 정보 불충분성으로 별도 기록한다(수정하지 않음, observation).

---

## 11. Historical vs Current State

```
Historical resume point   : STEP5-C, WAITING_FOR_SOURCE, NHBC1833
Current repository state  : 동일 — 변경 없음 (NHBC1833은 여전히 미확보)
                             단, 같은 카테고리의 다른 문서(SLBC1689/PBC1742/
                             PBC1765)는 완전히 별도의 파이프라인으로
                             2026-08-01~02에 진행되었다가 현재 정지된 상태
Next authorized action    : Human source acquisition (NHBC1833) — 과거
                             판정과 동일하게 유지
```

Historical resume point와 현재 repository state는 **NHBC1833 자체에 대해서는
일치**한다(둘 다 WAITING_FOR_SOURCE). 그러나 "조직신학 Baptist confession
corpus 작업" 전체를 놓고 보면, historical resume point(STEP5-C 문서 체인)가
암시하는 단일 트랙 진행 모델은 **더 이상 현재 상태를 정확히 설명하지
못한다** — 실제로는 두 개의 분기된 트랙이 존재하고 그중 하나(archive_org)가
STEP5 문서에 기록되지 않은 채 더 진전되어 있다.

---

## 12. Last Verified Resume Point

```
LAST VERIFIED STAGE : STEP 5-C (Human Source Acquisition Package 준비 완료)
CURRENT STATE        : WAITING_FOR_SOURCE — VERIFIED (2026-08-26 재확인)
```

---

## 13. Current Blocker

**TRUE BLOCKER**: NHBC1833 원문(`nhc_1833.txt`)이 아직 사람에 의해 확보되지
않음. 자동화 도구(WebFetch 등)로 verbatim 원문을 확보할 수 없다는 원칙이
STEP5-B에서 이미 확인되어 있고(§STEP5_SOURCE_COMPARISON.md), 이번 조사는
그 판단을 뒤집을 새로운 근거를 찾지 못했다.

부차적 관찰(blocker 아님, observation): 같은 트랙의 SLBC1689/PBC1742가
STEP5 registry와 무관하게 별도 경로로 확보·처리되었다는 사실은, NHBC1833도
같은 archive_org 경로로 확보 가능할 수 있음을 시사한다. 다만 이는 이번
task의 "새로운 acquisition 시작 금지" 원칙에 따라 **제안으로만 기록**하며
실행하지 않는다.

---

## 14. Next Authorized Action

```
NEXT AUTHORIZED ACTION:
Human acquisition of NHBC1833 (New Hampshire Confession of Faith, 1833)
→ docs/tasks/reports/STEP5_HUMAN_ACQUISITION_GUIDE.md 절차에 따라
  data/nae/sources/baptist/nhc_1833.txt 로 저장
→ 이후 STEP5_REGISTRY_TRANSITION.md의 PREPARED → ACQUIRED 절차부터 재개
```

CUE는 직접 acquisition을 수행하지 않는다.

---

## 15. Mutation Audit

```
Code 변경        : 0
Corpus 변경      : 0
TSU 변경         : 0
Embedding 변경   : 0
Embedding Cache  : 0
Qdrant 변경      : 0
Manifest 변경    : 0
Registry 변경    : 0
읽은 파일만 존재 — 어떤 기존 문서도 수정하지 않음
다른 session이 작업 중인 파일(NAE/smith_activation.py, docs/STATE.md,
ui/pages/chat.py 등 main worktree의 unstaged 변경)에 개입하지 않음
```

## 16. Git Status

이 recovery는 별도 git worktree(`baptist-materials-download-status-513932`,
브랜치 `claude/nae-theology-resume-point-35944a`)에서 수행했으며, 작업 시작
시점 `git status --short` 결과는 **clean**(추적되지 않은 변경 없음)이었다.
이번 문서 작성 1건을 제외하면 이 worktree에 다른 변경 없음. `git add`/
`git commit` 미실행.

메인 저장소(`/Users/David/DBMA`, 브랜치 `dev/dbma-engine`)는 다른
세션(들)이 진행 중인 unstaged 변경(`NAE/smith_activation.py`,
`docs/STATE.md`, `ui/pages/chat.py`, `docs/agents/cue/` 신규 파일 다수)을
보유하고 있었으며, 이번 조사는 이를 읽기만 하고 **되돌리거나 수정하지
않았다**.

---

## 17. Final Decision

```
NAE THEOLOGY CORPUS
RESUME-POINT RECOVERY

HISTORICAL WORK:
Baptist Confessions Corpus Acquisition (STEP4/STEP5 시리즈, NAE-SOURCE-003)

PRIMARY SOURCE:
NHBC1833 — New Hampshire Confession of Faith (1833)
(구 source_id 병기: baptist-confession-001 — 미통합, 임의 변경 안 함)

LAST VERIFIED STAGE:
STEP 5-C

CURRENT STATE:
WAITING_FOR_SOURCE

SOURCE STATUS:
미확보 (data/nae/sources/baptist/nhc_1833.txt 없음)

MONITOR ↔ REPOSITORY:
CONSISTENT (모니터가 이 트랙에 대해 정보를 제공하지 않으므로 상충 없음;
단 "VOL.01~08" 큐의 정체는 미상 — observation)

TRUE BLOCKER:
Human source acquisition 미완료 (NHBC1833 원문)

NEXT AUTHORIZED ACTION:
Human acquisition of NHBC1833 → STEP5_HUMAN_ACQUISITION_GUIDE.md 절차 재개

NEW ACQUISITION REQUIRED:
YES (단, 이번 task 범위 밖 — Human action)

CUE ACTION:
HOLD

C1 ACTION:
HOLD

CODE MUTATION:
0

CORPUS MUTATION:
0

EMBEDDING:
0

QDRANT MUTATION:
0

GIT COMMIT:
NO
```

---

## 18. Observations (별도 기록, 이번 task 범위 밖 — 처리하지 않음)

1. **병행 트랙 미조율**: `source_candidates.csv`/STEP5 registry 트랙과
   `NAE/corpus/raw/archive_org/` 트랙이 같은 Baptist confession 범주를
   조율 없이 각각 다루고 있다. `CUE-PHASE1-ADR029-GATE-RECONCILIATION-
   TRUE-BLOCKER-AUDIT.md` §13.4가 이미 "세 트랙 통합 여부는 HQ decision
   필요"로 지적한 것과 동일한 종류의 문제이며, 그 지적이 Baptist confession
   트랙에도 그대로 적용된다.
2. **source_id 이중 체계**: `NHBC1833` ↔ `baptist-confession-001`.
3. **PBC1742 canonicalization 실패**가 방치되어 있음(`no_extractable_source`,
   2026-08-01) — 재처리 필요 여부 결정된 기록 없음.
4. **NAE_CORPUS_INVENTORY_REVIEW_001.md의 카탈로그(2026-08-02)가 현재 실제
   디렉터리 구조와 불일치** — NHBC1833/SLBC1689를 "raw archive_org 145건"
   안에 있는 것처럼 나열하지만 실제로는 해당 디렉터리가 없음(SLBC1689는
   canonical에만 존재, raw는 없음 — 이미 정리/이동되었을 가능성).
5. **AF1815(source_candidates.csv)와 `Fuller_Complete_Works_Vol01~08`
   (canonical 존재)의 관계 불명확** — 동일 자료의 다른 표기인지 별개
   작품집인지 확인 필요.

이 항목들은 모두 새로운 후보 발굴이 아니라 **기존에 이미 존재가 확인된
불일치**이며, 지시사항 §7/§12에 따라 이번 task에서 수정하지 않고 기록만
한다.
