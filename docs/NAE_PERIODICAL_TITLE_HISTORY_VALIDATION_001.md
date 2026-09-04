# NAE Periodical Title History Validation 001

작성일: 2026-08-02
Project: NAE-PERIODICAL-CONDITION-RESOLUTION-001 Phase 3
목적: C1 Review-002 WARNING("제호 계승 관계 서지 미검증") 해소 시도
성격: **검증(읽기 전용)** — Pilot 데이터 변경 없음, 결과만 기록

---

## 1. 신규 실측 증거

`NAE/corpus/raw/archive_org/missions/Baptist_Missionary_Magazine_1817_v1i1/ocr.txt`
87~101행을 재검토한 결과, 이전 분석(Pilot Report-001, Design v1)에서는
발견하지 못했던 **직접적 계승 증거**를 확인했다:

```
MASSACHUSETTS
Baptist Missionary Magazine.

ENCOURAGED and assisted by your liberal support, the Editor
has been enabled to complete the fourth volume. ...
... the Trustees of the
Baptist Missionary Society of Massachusetts to propose this period-
ical work. ...
```

이 문단은 1817년 발행물(제호: "American Baptist Magazine, and
Missionary Intelligencer. New Series") **본문 안에 "Massachusetts
Baptist Missionary Magazine"의 4권 완결 에디터 서문이 그대로 포함**되어
있다 — 즉 1817년판이 이전 간행물("Massachusetts Baptist Missionary
Magazine", 4권까지 발행)의 후신임을 발행물 스스로 명시하고 있다.

---

## 2. 검증 기준별 결론

### 2.1 동일 간행물인가?

**결론: 계승 관계 확인됨(직접 증거).** "Massachusetts Baptist
Missionary Magazine"(1803년 창간, 최소 4권까지 발행)과 "American
Baptist Magazine, and Missionary Intelligencer, New Series"(1817년
재창간)는 **동일 발행 조직(Baptist Missionary Society of
Massachusetts)이 제호를 바꿔 계속한 동일 계보의 간행물**이다.

이는 이전 문서(Design v1/Pilot Report-001)가 "volume 번호 불연속에
근거한 추정(judgement call)"으로 남겨뒀던 부분을, **RAW 원문 자기
증언(self-attestation)이라는 1차 사료 증거로 격상**시킨 것이다 — 다만
이것이 "사서/서지 전문가의 전수 검증"을 대체하지는 않는다(§4 재확인).

### 2.2 New Series 처리 방법

"New Series"는 **동일 간행물의 재출발(relaunch)을 나타내는 관례적
표기**로 확인된다(archive.org/도서관학에서 흔한 패턴 — 제호 변경 또는
장기 휴간 후 속간 시 "New Series"로 표기하고 volume 번호를 1부터
다시 매김). 이번 사례는:

```
구간(Old Series): "Massachusetts Baptist Missionary Magazine" — 최소 Vol. 1(1803)~Vol. 4(연도 미상, RAW 미확보)
신간(New Series):  "American Baptist Magazine, and Missionary Intelligencer" — Vol. I(1817)~Vol. LXXXVII(1907, masthead "Missionary Magazine")
```

**처리 방법 결정**: 두 구간을 **별도 Work로 유지**하되(자동 병합하지
않음, Governance §1 Philosophy #3), `continues_work_id`/
`continued_by_work_id`로 명시적 연결을 **적용 가능**하다고 판단한다.

### 2.3 Volume Reset 처리

**결론: 설계 변경 불필요.** 기존 ADR-018 설계(`title_history[]` +
`continues_work_id`)가 이미 이 사례를 정확히 표현할 수 있음을 재확인
했다 — Volume 번호가 리셋되어도 각 Work는 자신의 `volume_number`를
독립적으로 가지므로 충돌이 없고(Reference Integrity는 Work 단위로
검사되므로 Work가 분리되어 있는 한 volume_number 중복 자체가 문제
되지 않음), `continues_work_id`가 "리셋 이전 Work"를 가리키기만 하면
된다. **신규 필드나 모델 변경이 필요하지 않다.**

---

## 3. Pilot 데이터 반영 여부

**이번 작업에서는 반영하지 않는다**(명령서 금지 사항 "pilot 데이터
변경" 준수). 아래는 §1의 증거가 뒷받침하는, **향후 적용 시** 사용할
값을 기록만 해 둔다:

```yaml
# resources/theological_sources/authority/pilot_periodical/periodicals.yaml (향후 적용안, 미실행)
- periodical_id: american_baptist_missionary_magazine
  continues_work_id: massachusetts_baptist_missionary_magazine   # 신규 필드값(설계만)
  title_history:
    - title: "American Baptist Magazine, and Missionary Intelligencer. New Series"
      start_date: "1817"
      end_date: null
    - title: "Missionary Magazine"   # masthead 축약형, 1837~1907 실측
      start_date: "1837"   # 첫 실측 확인 연도(그 이전 축약 여부는 미확인)
      end_date: null

- periodical_id: massachusetts_baptist_missionary_magazine
  continued_by_work_id: american_baptist_missionary_magazine   # 신규 필드값(설계만)
```

---

## 4. Remaining Risk (완전 해소 아님)

- 1803~1817 사이(Vol. 2~4로 추정)의 실제 발행 이력은 이번 RAW 확보분에
  없어 완전히 재구성하지 못했다 — "4권까지 발행"은 1817년판 서문의
  자기 증언만으로 확인된 사실이다.
  - **책임 있는 유보(uncertainty disclosure)**: 서문 저자가 4권을
    "완결"이라고 표현한 것이 반드시 "그 다음 volume부터 즉시 신제호로
    전환됐다"는 뜻인지, 아니면 그 사이에 공백기가 있었는지는 이
    문단만으로 단정할 수 없다.
- "Missionary Magazine"(축약 masthead)으로의 전환 시점도 1837년
  실측(가장 이른 확보 자료)일 뿐, 1817~1837 사이 정확한 전환 연도는
  미확인.
- **따라서 여전히 "사서/서지 전문가의 전수 검증 권고"를 유지한다** —
  이번 발견은 그 검증의 부담을 크게 줄여주는 강력한 1차 증거이지,
  완전한 대체가 아니다.

---

## 완료 판단

C1 Review-002 WARNING(제호 계승 관계 서지 미검증)에 대해: **실질적으로
강하게 뒷받침되었으나(RAW 1차 사료 자기 증언 확보), 완전 해소는
아님** — Pilot 데이터에 실제 반영(§3 향후 적용안 실행)과 남은 공백
기간(1803~1817 사이 volume 2~4) 확인이 필요하다.
