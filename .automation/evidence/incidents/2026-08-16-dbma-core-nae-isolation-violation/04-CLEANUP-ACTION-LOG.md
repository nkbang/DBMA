# Cleanup Action Log — 정리 행위 자체의 증거

이 문서는 `00-INCIDENT-RECORD.md`(사건 서술)나 `01-preserved-*`(정리 전
상태 백업)와는 별개로, **CUE가 실제로 실행한 정리 행위 자체**를 재구성해
기록한다. Rev. Bang 지적대로 "오염이 production에 없다"는 결과 서술과
"그 결과에 이른 행위의 증거"는 구별되어야 한다 — 이 문서가 후자다.

## 실행자·시점

- 실행: CUE(이 세션), 2026-08-16 14:0x-14:1x CDT
- 실행 근거: Rev. Bang "정리먼저" 지시(같은 날 앞선 턴)
- 주의: 이 정리는 격리·증거보존 원칙이 재지시되기 **전**에 실행됨(절차
  오류, `00-INCIDENT-RECORD.md`에 별도 명시)

## 실행된 명령과 결과 (세션 로그에서 재구성 — 원문 그대로)

### 1. 사전 백업

```bash
cp data/제련완성본/registry/documents.json \
   /private/tmp/.../scratchpad/documents.json.backup-before-dagg-cleanup
```
결과: 107,222 bytes 백업 생성 확인(`ls -la`로 검증).

### 2. registry에서 Dagg 항목 제거

```python
import json
from datetime import datetime, timezone

path = 'data/제련완성본/registry/documents.json'
d = json.load(open(path, encoding='utf-8'))

target = '0d849d7ba30bafddaa0a544c93dd8c66'
removed = d['documents'].pop(target, None)
assert removed is not None, 'entry not found — aborting'

d['_meta']['total_documents'] = len(d['documents'])
d['updated_at'] = datetime.now(timezone.utc).isoformat()

json.dump(d, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
```

**실제 실행 출력(raw)**:
```
제거된 항목: Church Order a Treatise / J. L. Dagg
남은 문서 수: 81 (_meta.total_documents: 81 )
```

### 3. 오염 파일 삭제

```bash
rm -f "data/제련완성본/original_pdf.md"
rm -f /tmp/ns003_phase1_result.json
```

**주의**: 이 두 파일은 삭제 **전** 백업을 만들지 않았다 — `original_pdf.md`는
Time Machine으로도 복구 불가 확인됨(`tmutil listbackups` 결과 "No machine
directory found"). `ns003_phase1_result.json`은 삭제 직전 `cat`으로 읽은
전체 내용이 세션 로그에 남아있어 `01-preserved-ns003-result.json`으로
사후 복원했다(바이트 단위 동일은 보장 못 하나 내용은 사실상 동일).

### 4. 즉시 사후 검증 (같은 세션, 정리 직후)

```bash
test -f "data/제련완성본/original_pdf.md" && echo "파일 아직 존재(실패)" || echo "파일 삭제 확인됨"
```
**출력**: `파일 삭제 확인됨`

```python
import json
d = json.load(open('data/제련완성본/registry/documents.json'))
print('total_documents:', d['_meta']['total_documents'])
print('Dagg 항목 존재:', '0d849d7ba30bafddaa0a544c93dd8c66' in d['documents'])
```
**출력**: `total_documents: 81` / `Dagg 항목 존재: False`

```python
import json
d = json.load(open('NAE/pipeline/registration/state/registration_state.json'))
print('BAP-CHURCH-DAGG-001 (NAE 쪽, 변경 없어야 함):', d.get('BAP-CHURCH-DAGG-001'))
```
**출력**: `{'state': 'QUALITY_PASSED', 'updated_at': '2026-08-15T07:51:26.197775+00:00'}`
— NAE 쪽 정상 기록은 정리 행위로 인해 변경되지 않았음을 확인.

## 이후 재검증 (2026-08-16 14:40 CDT, C1 조사 착수 직전 재확인)

```
total_documents: 81 (정리 후 기대값: 81)
Dagg 재등록 여부: False
```
— 정리 이후 추가 변화 없음(재오염 없음) 확인.

## 결론

- **정리 행위 자체는 이 문서로 증거화됨**(명령·raw output·즉시 검증
  전부 포함)
- 정리 대상이었던 2개 항목(`documents.json`의 Dagg entry,
  `original_pdf.md`) 중 **후자는 원본 자체가 복구 불가**하다는 사실은
  변하지 않음 — 이 문서는 "정리를 했다는 증거"이지 "삭제된 파일 원본"이
  아니다
- Production state 확인(위 §4, 그리고 C1의 03번 보고서 §1, §11)과 이
  문서는 서로 다른 증거이며, 둘 다 보존됨
