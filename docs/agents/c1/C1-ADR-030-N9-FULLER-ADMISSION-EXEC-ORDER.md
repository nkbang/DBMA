# 쳗 → C1 EXEC ORDER — ADR-030 N-9 Fuller Vol01–08 Admission (문서 한정)

> **baseline**: `dev/dbma-engine` @ `9c617b6` (worktree `claude/fuller-admission-n9-docs`).
> **권위**: 본 명령서. 설계 근거 = `docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md` (v2.1) §12 N-9,
> `docs/agents/cue/CUE-ADR-030-M3-CORPUS-ADMISSIONS.md` §3.3.
> **HQ 승인**: Fuller Vol.01–08 = ADMIT (in-principle). 모든 처리(TSU/verification/human review/embedding/
> production ingestion) = HOLD. existing 3,319 baseline = FROZEN. commit = NO.
> **CUE**: Fuller Readiness Package 독립 spot-verify = GREEN (재감사 금지).
> **운영**: single EXEC. **C1 commit 금지.** documentation only.
> **작성**: 쳗 · 2026-09-02

---

## AUTHORITY

- HQ(David): Fuller Vol.01–08 admission-in-principle 승인. 처리 5종 전부 HOLD. baseline FROZEN. no commit.
- CUE: Fuller readiness GREEN (검증 완료, 재실행 불필요).
- 본 명령서 = 쳗 발행, 실행 범위 = 아래 DO 2건뿐.

## TASK

ADR-030 N-9(Fuller Vol01–08)에 대한 **문서 전용** 조치 2건:
1. ADR-030 N-9 row 최소 correction — admission 결정 사실 + 처리 HOLD 명시.
2. provenance disclosure 문서 신규 작성.

`corpus_admissions.jsonl` ledger 기입 + `tests/test_corpus_admissions.py` 갱신은
**본 태스크 범위 아님** (§DEFERRED). M3 게이트 모델 확장이 선행돼야 하며 CUE 설계 단계임.

## DECISION (근거)

- `CUE-ADR-030-M3-CORPUS-ADMISSIONS.md` §3.3 / §5: admission 기록이 생기면 수기 게이트상
  TSU review→embedding **진행 가능** 상태가 된다. 지금은 처리 전면 HOLD이므로 ledger 기입은 부적합.
- `tests/test_corpus_admissions.py`: record 수 == 6, `BAP-MISS-FULLER*` 금지, date == 2026-08-28,
  tsu-track `theological_category` 필수 — Fuller VOL03–07은 M2에 `theological_category` 없음.
  → ledger 기입 시 governance 테스트 4건 파손 + CUE 설계 문서와 충돌.
- 따라서 이번엔 markdown 2파일만. 테스트·스키마·게이트 무접촉.

## DO (정확히 2파일)

### 1. `docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md` — N-9 row 1개 치환

OLD (verbatim, §12 NOT YET 표):
```
| N-9 | Fuller Vol01–08 TSU/embedding, M3 CLAIM-ONLY 19건 acquisition | backlog, ADR-029 PHASE 순서 |
```
NEW:
```
| N-9 | Fuller Vol01–08 TSU/embedding, M3 CLAIM-ONLY 19건 acquisition | admission-in-principle 승인 (HQ, 2026-09-02) — TSU generation / TSU verification / human review / embedding / production ingestion 전부 HOLD 유지. corpus_admissions.jsonl ledger 기입 + 수기 게이트 활성화는 M3 모델 확장(별도 CUE 단계) 후. provenance: `docs/NAE_FULLER_ADMISSION_PROVENANCE_DISCLOSURE_001.md`. backlog, ADR-029 PHASE 순서 |
```
OLD이 정확히 일치하지 않으면 조정 말고 STOP·보고. 다른 행·다른 파일 수정 금지.

### 2. `docs/NAE_FULLER_ADMISSION_PROVENANCE_DISCLOSURE_001.md` — 신규 파일

포함 항목 (사실만, 추론·평가 금지):
- 제목/목적: Fuller Vol01–08 admission-in-principle 결정 + provenance 공개 기록. 작성 2026-09-02.
- 결정: "HQ(David) 승인 — Fuller Vol.01–08 admission-in-principle. 처리 5종(TSU generation,
  TSU verification, human review, embedding, production ingestion) 전부 HOLD. 3,319 production
  baseline FROZEN. 본 문서 시점 mutation 0 (markdown 전용)."
- 8권 표 — 각 행: `source_id`(BAP-MISS-FULLER-VOL01..08), M2 `title`, `year`, `license`
  (전부 public_domain), `archive_source`(archive_org), `raw_checksum`(M2에서 verbatim 복사),
  `edition_id`(M2에서 복사).
- registration 증거: 각 권 `.automation/evidence/NAE-REG-BAP-MISS-FULLER-VOL0X.jsonl`
  (상태 VALIDATION_PASSED, `production_mutation: false`), M2 = `NAE/pipeline/registration/state/source_manifest.yaml`.
- classification (M2 기준, verbatim): authority_class = historical_witness (8/8);
  content_genre = VOL01–04 [theology], VOL05–06 [commentary], VOL07 [sermon],
  VOL08 [theology, sermon, mission]; theological_category = VOL01/02 [soteriology],
  VOL08 [missions], VOL03–07 미지정(M2에 키 없음); tradition = Particular Baptist (8/8).
- 미결 항목 명시: `NAE/governance/corpus_admissions.jsonl` 기입 안 됨 — 사유:
  M3 게이트 모델(admission 기록 = 처리 적격)과 "admission 하되 처리 HOLD" 상태 불일치,
  `tests/test_corpus_admissions.py` governance 가드(6건/Fuller 금지/date/tsu-meta)와 충돌.
  → M3 모델 확장 CUE 설계 후 별도 단계에서 처리.
- 값은 전부 M2 / evidence 파일에서 그대로 옮길 것. 새 수치 생성 금지.

## DO NOT

TSU generation · TSU verification · human review · embedding · Qdrant mutation ·
production mutation · 3,319 baseline 변경 · `corpus_admissions.jsonl` 편집 ·
`tests/**` 편집 · `NAE/**` 편집 (M2 읽기만) · runtime/config 변경 ·
무관 미커밋 항목 stage/revert/수정 · **commit / push**.

무관 미커밋 항목 발견 시 건드리지 말고 그대로 둔다.

## VERIFY (C1 self-check, 편집 후)

```bash
pwd                                   # …/.claude/worktrees/claude/fuller-admission-n9-docs 계열
git rev-parse --abbrev-ref HEAD       # claude/fuller-admission-n9-docs
git status --porcelain                # 기대: 2줄만
#   M docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md
#   ?? docs/NAE_FULLER_ADMISSION_PROVENANCE_DISCLOSURE_001.md
git diff --stat                       # ADR-030 = 1 row 변경만
grep -c . NAE/governance/corpus_admissions.jsonl   # 기대: 6 (불변)
```

하나라도 불일치 → STOP·보고. 테스트 실행 불필요(테스트·코드 무접촉).

## REPORT (아래 형식만, 장문 금지)

```text
C1 RESULT

STATUS: GREEN / BLOCKED

FILES:
- docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md
- docs/NAE_FULLER_ADMISSION_PROVENANCE_DISCLOSURE_001.md

ADMISSION:
Fuller Vol.01–08 = ADMITTED (in-principle, doc-only)

PROCESSING:
TSU generation = HOLD
TSU verification = HOLD
human review = HOLD
embedding = HOLD
production ingestion = HOLD

MUTATION:
production = 0
qdrant = 0
tsu = 0
canonical = 0
config = 0
unrelated WIP = 0

BASELINE:
3,319 production TSUs = UNCHANGED
corpus_admissions.jsonl = 6 records (UNCHANGED)

GIT:
commit = NO
diff = EXPECTED / UNEXPECTED

EXCEPTION:
NONE / <one-line>
```
