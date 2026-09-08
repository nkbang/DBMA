# Task Order — B-2: Fuller 8권 Canonical Re-normalize (C1)

- 발급: CUE → C1
- 일자: 2026-09-08
- 근거: `NAE_FULLER_PROCESSING_RESUMPTION_PLAN_v1.md` §10 B-2; B-1 완료 (`e9cb72c`)
- 작업 위치: `/Users/David/DBMA` @ `dev/dbma-engine` `e9cb72c`, venv `~/envs/dbma311`

---

## 0. 목적

B-1로 고친 `annotate.py`(scripture 추출기)를 Fuller **8권 canonical에 반영**.
`NAE/corpus/canonical/Fuller_Complete_Works_Vol01..08/` 의 `canonical.json` /
`canonical.txt` / `normalize_report.json` 재생성.

canonical 산출물은 **gitignore 대상** → 커밋할 것은 리포트 문서뿐.

---

## 1. 절차

### T1. 사전 스냅샷 (읽기 전용)
8권 각각 현재 값을 기록:
- `normalize_report.json` 전 필드 (특히 `paragraph_count`, `sentence_count`,
  `heading_count`, `scripture_references_found`, `pipeline_version`, `status`)
- `canonical.json` 의 `len(paragraphs)` 와 각 paragraph `len(sentences)` 합계

### T2. 재-정제 (8권, 한 번에 한 identifier)
```
for id in Fuller_Complete_Works_Vol01 .. Vol08:
  ~/envs/dbma311/bin/python -m NAE.pipeline.canonical.runner --identifier <id>
```
- **`process_all()` 금지** — Smith/Dagg/Hiscox 등 다른 identifier를 건드림.
  반드시 `--identifier` 로 Fuller 8개만.
- 각 실행 `report` JSON 캡처.

### T3. 사후 비교
8권 before/after 표:

| 필드 | 기대 |
|---|---|
| `scripture_references_found` | **증가** — B-1 측정치와 일치해야: Vol01 315 / Vol02 194 / Vol03 87 / Vol04 62 / Vol05 106 / Vol06 65 / Vol07 35 / Vol08 178 (합계 1042). ±소량 편차는 허용, 자릿수 다르면 STOP |
| `paragraph_count` | **불변** (B-1은 구조 로직 미변경) |
| `sentence_count` | **불변** |
| `heading_count` | **불변** |
| `canonical.json` paragraph 수 / sentence 합 | **불변** |
| `status` | `ok` 유지 |
| `pipeline_version` | 바뀌면 값 명시 |

### T4. TSU 정합 확인 (Vol.01)
- Vol.01 기존 TSU 3,643건은 **구 canonical 기준**으로 생성·배치됨
  (`fuller_v01_batch_*`, David 검수 대기).
- 재-정제 후 Vol.01 `canonical.json` 의 paragraph/sentence 구조가 **바이트
  수준으로 동일**한지 확인 (scripture_references 필드만 추가/변경돼야 함).
- 다르면 → **즉시 STOP·보고**. TSU 재생성/재배치는 이 Task Order 밖이며
  HQ 결정 사항.

---

## 2. 금지 / STOP

- ❌ `process_all()` 실행 (Fuller 외 identifier 오염)
- ❌ TSU 재생성, `tsu.json` 수정, `fuller_v01_batch_*` 재생성
- ❌ embedding / Qdrant / retrieval / promote
- ❌ Vol.02–08 TSU 생성 (별도, P-2 이후)
- ❌ `annotate.py` 추가 수정 (B-1 확정)
- STOP: 어느 볼륨이든 `paragraph_count` / `sentence_count` 변동 /
  `status != ok` / `scripture_references_found` 가 B-1 측정과 자릿수 불일치 /
  HEAD ≠ `e9cb72c`

---

## 3. 완료 조건

- [ ] T1 사전 스냅샷 8권
- [ ] T2 8권 `--identifier` 재-정제, 각 report 캡처
- [ ] T3 before/after 표 — `scripture_references_found` 증가(B-1치 일치),
      구조 필드 전부 불변
- [ ] T4 Vol.01 paragraph/sentence 구조 불변 확인 (TSU 정합)
- [ ] `git status --porcelain` = 리포트 1개만 (canonical은 gitignore)
- [ ] 보고 첫 줄 `git rev-parse HEAD` / `remote -v` / `--show-toplevel`

## 4. 산출물

- `docs/NAE_FULLER_B2_RENORMALIZE_REPORT_C1_001.md`
  (git status/HEAD / T1 스냅샷 / T2 실행 로그 요약 / T3 8권 before/after 표 /
   T4 Vol.01 구조 정합 결과 / `pipeline_version` 변화 / Next)
- (canonical 파일 자체는 로컬/NAS 갱신 — 커밋 안 함)

## 5. 범위 밖 (CUE / HQ)

- Vol.01 TSU 재생성 필요 여부 (T4에서 구조 변동 발견 시) = HQ 결정
- Vol.02–08 TSU 생성(F2) = P-2 Amendment 후 별도 Task Order
- 출력 토큰 절약: 리포트는 파일에 직접, 채팅은 10줄 이내
