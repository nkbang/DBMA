# NAE Periodical Issue Model Test 001

작성일: 2026-08-02
Project: NAE-PERIODICAL-CONDITION-RESOLUTION-001 Phase 4
목적: C1 Review-002 WARNING("동일 volume 내 복수 issue 시나리오 미검증") 완화
성격: **가상 검증만** — 실제 자료/Pilot 데이터 아님, Python 스크립트로 ID
스킴만 시뮬레이션(파일 생성 없음, 실행만)

---

## 1. 시나리오

```
Volume 1
 ├── Issue 001
 ├── Issue 002
 └── Issue 003
```

가상 periodical_id `hypothetical_journal`로 시뮬레이션(실존 자료
아님 — Baptist Missionary Magazine Pilot 실제 표본은 여전히 volume당
issue 1개뿐이므로 실자료 검증이 아니라 **ID 스킴 자체가 이 시나리오를
논리적으로 감당하는지**만 확인).

---

## 2. ID 생성 결과 (실행 결과, 추론 아님)

```
volume_id: hypothetical_journal_v001
issue_ids: ['hypothetical_journal_v001_i001',
            'hypothetical_journal_v001_i002',
            'hypothetical_journal_v001_i003']
source_ids: ['hypothetical_journal_v001_i001_s01',
             'hypothetical_journal_v001_i002_s01',
             'hypothetical_journal_v001_i003_s01']
```

---

## 3. 검증 결과

### 3.1 ID 충돌 여부

```
ID collision check: PASS (all unique)
```

3개 issue_id, 3개 source_id 전부 유일 — ADR-018/ID Governance ADR-017의
`{volume_id}_i{NNN}` / `{issue_id}_{scan_suffix}` 규칙이 동일 volume
내 복수 issue를 충돌 없이 표현한다.

### 3.2 Source 연결 (재스캔 포함)

```
Rescan (multi-source per issue) check: PASS
예: hypothetical_journal_v001_i002_s02
```

Issue 002가 재스캔되는 경우도 `scan_suffix`(`_s02`)로 충돌 없이
확장된다 — Pilot-001/002에서 이미 검증된 monograph의 "Different Scan
Same Edition" 패턴과 동일 메커니즘이 Issue 레벨에서도 그대로 작동함을
확인.

### 3.3 TSU 연결 가능성(체인 해석)

```
TSU chain resolution (source -> issue -> volume -> periodical): PASS for all 3 issues
```

`source_id`에서 문자열 파싱만으로 `issue_id → volume_id →
periodical_id` 전체 체인을 역산할 수 있음을 확인(ID 자체의
자기서술성, Design v1 §2 "자기서술적" 원칙 재확인) — 단, 실제 TSU
생성 로직은 문자열 파싱이 아니라 Registry FK 조회를 사용해야 한다
(문자열 파싱은 이번 스크립트의 검증 편의를 위한 방법일 뿐, 프로덕션
구현 방식을 제안하는 것은 아님 — TSU Field Readiness Report-001의
지적대로 실제 corpus manifest 계층이 아직 없으므로 이 항목은 "논리적
가능성"만 확인된 것이다).

---

## 4. 한계(가상 검증의 명확한 범위)

- **실제 RAW 자료로 검증된 것이 아니다** — Baptist Missionary Magazine
  Pilot의 실제 10개 issue는 각기 다른 volume에 속해 있어(volume당
  issue 1개), 동일 volume 내 복수 issue라는 실사례가 여전히 없다
  (TSU Field Readiness Report-001 §3, Remaining Risk 승계).
- ID 스킴이 "충돌 없이 표현 가능하다"는 것을 확인했을 뿐, 실제 등록
  절차(사람이 issue_number를 정확히 매기는 과정, 오기입 시 충돌 처리
  등 운영 절차)는 검증되지 않았다.

---

## 완료 판단

C1 Review-002 WARNING(동일 volume 내 복수 issue 미검증)에 대해:
**ID 스킴 수준의 논리적 타당성은 확인**(가상 시나리오 PASS), **실자료
기반 검증은 여전히 미해결**(3차 Pilot에서 실제 volume당 복수 issue
자료를 확보해야 완전 해소).
