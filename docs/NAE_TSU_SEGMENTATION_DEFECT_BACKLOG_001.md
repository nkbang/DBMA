# NAE TSU Segmentation Defect Backlog 001

**작성일:** 2026-08-10
**성격:** Architecture 영역 backlog 기록(코드 변경 없음). Forensic
disposition 과정에서 발견된 TSU 생성 파이프라인의 문장 분할 결함을
추적하기 위한 문서.

---

## 결함 설명

TSU 생성(문장 분할) 단계가 각주 삽입("(Denkw. VII, p. 216)")이나
각주 표시("*")를 문장 경계로 오인해, canonical 상 하나의 완전한
문장을 두 개의 별도 TSU로 쪼개는 사례가 확인됨. 이 경우 앞쪽 TSU는
문법적으로 불완전한 인용 귀속 표지나 문장 파편만 남고, claim이
성립할 실질적 근거를 자체적으로 갖지 못함.

## 확인된 사례

| 앞 TSU | 뒤 TSU | Paragraph | 분할 원인 | 확인 방법 |
|---|---|---|---|---|
| TSU-0000256 | TSU-0000257 | 259 | 각주 `(Denkw. VII, p. 216)`가 문장 중간에 삽입 | canonical.json paragraph 259 전문 대조 |
| TSU-0000265 | TSU-0000266 | 263→264 경계 | 각주 표시 `*`가 문장 중간(“raised him*from the dead”)에 삽입, 마침 paragraph 경계와 겹침 | canonical.json paragraph 263/264 전문 대조 |
| TSU-0000271 | TSU-0000272 | 265 | 골로새서 2:12 인용 중 각주 번호 목록("1 Rom. vi. 3,4. 2 Col ii,12. 3 1 Peter iii,21. 4 Rom. x.9.")이 문장 중간에 삽입 | Batch 2 forensic disposition(TSU-0000269~0308) |

## 권장 후속 조치(구현하지 않음, 기록만)

1. TSU 생성 파이프라인의 문장 분할 로직이 각주 마커(`*`, `(...)"`,
   숫자 위첨자 등)를 문장 종결부호로 오인하지 않도록 하는 정규식/
   휴리스틱 검토.
2. 이미 생성된 4,107건 전체에서 유사 패턴(문장이 각주로 시작/종결)
   재스캔 필요 여부 검토.
3. 이미 분할된 레코드에 대한 처리 정책 결정 필요: (a) 병합해 단일
   TSU로 재생성, (b) 두 TSU를 논리적으로 연결된 쌍으로 유지하되
   메타데이터에 링크 필드 추가, (c) 둘 다 individually verified
   대상에서 제외.

이 문서는 감사 기록용이며, 위 권장 사항 중 어느 것도 사용자 승인
없이 구현하지 않는다(Architecture Freeze Rule).

## 관련 Exception Queue 항목

`NAE/review/human/exception_queue.json`: TSU-0000256, TSU-0000257,
TSU-0000265, TSU-0000266(참고, non-blocking) — status: `STRUCTURAL_EXCEPTION`
