# Task Order — MTP 전권 chspurgeon.com 현대어판 다운로드·교체·재색인 (C1)

- 발급: CUE → C1 (Cline 작업창 #1)
- 일자: 2026-09-18
- 상태: OPEN
- 선행/연계:
  - 이번 세션에서 CUE가 MTP Vol51/52/53에 먼저 적용·검증 완료 (noise 21.0/34.6/24.7 → 11.2/11.2/11.3)
  - 사용된 스크립트: `scripts/spurgeon_chspurgeon_scrape.py`, `scripts/spurgeon_reprocess_volumes.py` (둘 다 이미 작성·테스트됨, 그대로 재사용)

---

## 1. 배경

archive.org의 MTP(Metropolitan Tabernacle Pulpit) OCR 원본 일부(특히 Vol51-53)에서
글자 단위 OCR 오인식(예: `^`, `«»`)이 심해 noise score가 최대 34.6까지 나왔다.
동일 설교의 현대어 정리판이 [chspurgeon.com](https://chspurgeon.com/sermons/collections/mtp)에
Vol.7~63 전량(57권) 공개되어 있고, 실측 결과 원문과 신학적 내용은 동일하되
OCR 잡음이 전혀 없다(noise ~11 수준, 본 코퍼스 평균과 동일).

**중요한 트레이드오프**: chspurgeon.com은 고어체(thee/thou 등)를 현대어(you 등)로
다듬은 판본이다. 1905~1907년 원문과 문구가 완전히 동일하지는 않다 — 이미 사용자
승인 하에 Vol51-53에 적용됨. 이번 Task Order는 그 결정을 **MTP 전권(Vol.7-63)으로
확장 적용**하는 것이다.

---

## 2. 목적

`data/제련완성본/Spurgeon_MTP_Vol{N}.txt` (N=7..63, 총 57권)를 chspurgeon.com
현대어판으로 전량 교체·신규 확보하고, 기존 프로덕션 파이프라인으로 재청킹·재색인한다.

- **이미 보유한 volume**(현재 로컬 확인: 7,8,9,10,11,12,13,15,19,28,30,31,32,34,36,39,41,46,47,48,50,51,52,53) → 교체
- **미보유 volume**(위 목록 외 7-63 전부, 예: 14,16-18,20-27,29,33,35,37,38,40,42-45,49,54-63) → 신규 확보

**범위 밖**: NPSP(New Park Street Pulpit, Vol.1-6에 해당, 로컬 파일명 `Spurgeon_NPSP_A~F`).
chspurgeon.com의 `/sermons/collections/mtp/vol-N`은 N=7부터 시작하므로 자동으로 제외된다 — 별도 조치 불요.

---

## 3. Mutation Budget

- 허용: `data/제련완성본/Spurgeon_MTP_Vol{N}.txt` (신규 생성 또는 교체), 각 교체 시
  `.bak` 백업 필수(아래 §5 절차 참고), `data/제련완성본/registry/*`, `output/bench/tsu_dataset.jsonl`,
  `output/bench/tsu_manifest.json`, 후보 인덱스/성경 인덱스 디렉터리(파이프라인이 자동 갱신)
- **절대 금지**: `data/RAW/` 일체 접촉 금지 (CLAUDE.md "RAW 데이터는 명령 없이는 절대
  변경 금지" — 이 Task Order도 RAW 변경을 승인하지 않는다). 시스템 sandbox가
  RAW 쓰기를 자동 차단하는 것을 확인함 — 차단되면 그것이 정상 동작이니 우회 시도 금지.
- 이 Task Order 범위 밖 파일(다른 저자/볼륨, core/, ui/ 등 코드) 무접촉.
- git 커밋 여부: `data/`는 `.gitignore` 대상(비추적)이라 git 커밋 불필요. 코드 변경이
  없으므로 이 Task Order에는 git commit/push가 없다.

---

## 4. 사전 준비 (필독)

- 작업 위치: `/Users/David/DBMA` (worktree 아님, 실제 데이터 디렉터리)
- 처리 스크립트는 반드시 프로젝트 venv로 실행: `~/envs/dbma311/bin/python3`
  (homebrew python3에는 docling/langchain 등이 없어 `core.processing` import 실패함)
- 스크레이핑 스크립트(`scripts/spurgeon_chspurgeon_scrape.py`)는 System python3(`python3`)로도
  동작 가능(requests만 필요) — 편한 쪽 사용.
- 실행 전 반드시 `ps aux | grep streamlit`로 `dbma_ui.py`가 켜져 있는지 확인하고,
  켜져 있어도 그대로 진행(레지스트리는 `fcntl` 파일 락으로 직렬화됨, CUE가 51-53
  처리 시 확인 완료). 단, **동시에 여러 volume을 병렬로 돌리지 말 것** — 반드시
  순차 실행(레지스트리 락 경합 최소화, 디버깅 용이성).

---

## 5. 절차 (volume마다 반복, 배치 크기 권장 5~10권씩)

### Step 1 — 스크레이핑 (스크래치 디렉터리로, 프로덕션 직접 덮어쓰기 금지)
```
python3 scripts/spurgeon_chspurgeon_scrape.py /tmp/spurgeon_batch --range <시작>-<끝>
```
- 결과: `/tmp/spurgeon_batch/Spurgeon_MTP_Vol{N}.txt` 생성
- 각 파일 끝에 "No. ? —" 패턴이 있는지 확인(정규식 버그 재발 감시):
  ```
  grep -c "^No\. ? —" /tmp/spurgeon_batch/Spurgeon_MTP_Vol{N}.txt
  ```
  **0이 아니면 중단하고 CUE에게 보고** (2026-09-18 세션에서 이미 한 번 발견·수정된
  버그다 — 재발 시 사이트 구조가 또 바뀐 것이므로 스크립트 재점검 필요, 직접 임의
  수정하지 말고 CUE에게 알릴 것).

### Step 2 — noise score 검증 (배포 전)
```
~/envs/dbma311/bin/python3 -c "
import sys; sys.path.insert(0,'.')
from core.utils import calculate_noise_score
import glob
for f in sorted(glob.glob('/tmp/spurgeon_batch/Spurgeon_MTP_Vol*.txt')):
    with open(f, encoding='utf-8') as fh: text = fh.read()
    r = calculate_noise_score(text, file_type='txt')
    print(f, r['score'])
"
```
- 모든 volume이 noise score **20 미만**인지 확인. 20 이상이면 중단·보고
  (2026-09-18 세션 실측 기준 정상 범위는 11~12대).

### Step 3 — 배포 (기존 파일 있으면 백업 후 교체, 없으면 신규 배치)
각 파일마다 개별 명령으로 실행 (한 번에 여러 개를 for 루프로 묶지 말 것 —
CUE 세션에서 loop 형태 명령이 안전장치에 걸려 차단된 이력 있음, 파일 단위로
하나씩 승인받는 편이 안전):
```
cp data/제련완성본/Spurgeon_MTP_Vol{N}.txt data/제련완성본/Spurgeon_MTP_Vol{N}.txt.chspurgeon_replaced.bak   # 기존 파일이 있을 때만
cp /tmp/spurgeon_batch/Spurgeon_MTP_Vol{N}.txt data/제련완성본/Spurgeon_MTP_Vol{N}.txt
```

### Step 4 — 재청킹 + TSU 재색인 (기존 파이프라인 재사용, 신규 스크립트)
```
cd ~/DBMA && ~/envs/dbma311/bin/python3 scripts/spurgeon_reprocess_volumes.py --range <시작>-<끝>
```
- 이 스크립트가 각 volume에 대해 `process_one_file(force_rechunk=True)` →
  `reindex_document()` 를 순서대로 실행하고 마지막에 JSON 요약을 찍는다.
- **exit code 0이 아니면(실패/스킵 존재) 중단하고 CUE에게 보고.**

### Step 5 — 배치 검증
```
~/envs/dbma311/bin/python3 -c "
import json
seen=set()
for line in open('output/bench/tsu_dataset.jsonl', encoding='utf-8'):
    r = json.loads(line)
    src = r.get('document_id','')
    seen.add(src)
print('total unique document_id in dataset:', len(seen))
"
```
- `data/제련완성본/registry/documents.json`에서 이번 배치 volume들의
  `superseded_by`가 전부 `null`(최신)인지 확인.

---

## 6. 산출물

`docs/DBMA_SPURGEON_MTP_FULL_CORPUS_CHSPURGEON_REPORT_C1_001.md` 신규 작성. 형식:

```
STATUS / 처리 Volume 목록(신규 확보 N권, 교체 M권) / Step2 noise score 표(volume별)
/ Step4 stdout 요약(성공/실패 volume) / Step5 검증 결과 / 이상 징후 / Next
```

- noise score는 **volume별 표로 전량 기재** (요약 문장 금지, 아래 예시 형식)

| Volume | 이전 noise | 이후 noise | 상태 |
|---|---:|---:|---|
| 7 | (신규) | 11.x | OK |
| 14 | (신규) | 11.x | OK |
| 51 | 11.2(이미 처리됨) | - | 스킵(이미 완료, 재처리 불필요) |

- **Vol51/52/53은 이미 CUE가 처리 완료했으므로 재처리하지 말 것** (건드리면
  registry에 불필요한 supersede 체인만 늘어남). `--range` 사용 시 51-53을
  자동으로 건너뛰도록 `--volumes` 로 개별 지정하거나, 스킵 로직을 직접 짜지
  말고 그냥 51-53을 제외한 범위로 나눠 실행할 것(예: 7-50, 54-63).

---

## 7. 완료 조건

- [ ] Vol.7-63 중 51/52/53을 제외한 54개 volume 전부 chspurgeon.com 판으로 확보/교체
- [ ] 전량 noise score < 20
- [ ] `scripts/spurgeon_reprocess_volumes.py` exit code 0 (전량 성공)
- [ ] "No. ? —" 패턴 잔존 0건
- [ ] `data/RAW/` 무변경 (`git status`는 무의미 — RAW는 비추적 폴더이므로 대신
  각 파일 mtime 또는 `ls -la data/RAW/Spurgeon_MTP_Vol*.txt`를 작업 전/후
  캡처해 비교)
- [ ] 리포트에 volume별 noise score 표 전량 포함

## 8. 보고 규율

수치·완료 주장은 명령어 stdout 원문으로만 인정한다. "정상적으로 완료"류의
요약 문장만 쓰고 원문을 생략하는 것 금지. 스크립트가 에러를 내면 전체
traceback을 그대로 붙일 것(요약·재서술 금지). 불확실하면 "확인 불가"로
적고 CUE에게 질문할 것 — 추측 금지.

## 9. 범위 밖 (CUE)

- chspurgeon.com 출처 표기(사이트가 현대어판이라는 사실을 검색 결과/인용에
  어떻게 노출할지) 정책 결정 — 아직 미결, 이 Task Order에 포함 안 됨
- NPSP(Vol.1-6) 처리 여부 — 별도 지시 필요
- 스크립트 로직 변경(정규식 수정 등) — 문제 발견 시 CUE에게 보고만, 직접 수정 금지
