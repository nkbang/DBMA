// deno-fmt-ignore-file
# C1 Task Order 006 — 정리된 문서 중복 정리 계획 반려 및 재제출 요청

발급: CUE (2026-07-21)
대상: C1 (Cline 작업창 #1)
성격: **계획 반려 — 실행 금지.** C1이 제출한 "정리된 문서 중복 정리"
플랜을 CUE가 실제 `data/제련완성본` 데이터와 `.batch_state.json`을
직접 대조 검증한 결과, 목표는 타당하나 제시한 메커니즘이 실제 데이터와
맞지 않아 그대로 실행하면 위험하다고 판단했다. **ACT MODE로 전환하지
말고, 아래 4가지를 반영한 새 계획을 다시 제출하라.**

---

## 1. 원래 제출한 계획의 문제

C1의 원래 계획: "clearscan_cropped 접미사로 그룹화 → 그룹당 파일 크기가
가장 큰 파일을 대표로 선택 → 나머지 삭제". CUE가 실제 파일을 열어 확인한
결과, 이 계획은 서로 다른 두 종류의 파일을 하나로 뭉뚱그리고 있다.

### 실제 확인된 사실 (2026-07-21, CUE 검증)

**케이스 A — 진짜 고아(orphan) 파일 3개** (삭제 가능, 그러나 "그룹화
후 크기 비교"가 아니라 "chunks 파일 존재 여부"로 판별해야 함):
```
5. 요한복음1clearscan_cropped_pdf.md
6. 요한복음2clearscan_cropped_pdf.md
9. 로마서1clearscan_cropped_pdf.md
```
이 3개는 `_pdf_chunks.txt`/`_pdf_chunks_meta.json`이 아예 없다 —
청킹이 안 끝난 미완성 산출물이다. 이미 완전히 처리된 원본
(`5. 요한복음1.pdf` 등, `.md`+`chunks.txt`+`chunks_meta.json` 모두
존재)이 별도로 있다. `output/registry/documents.json`에도 등록돼
있지 않다. **크기 비교가 아니라 "chunks_meta.json 존재 여부"로
판별해야 정확히 이 3개만 잡힌다.**

**케이스 B — 진짜 중복 업로드 2세트** (원래 계획이 아예 놓친 패턴):
```
7. 사도행전1 복사본.pdf  ↔  7. 사도행전1.pdf   (파일 크기 완전 동일: 9,773,094 bytes)
8. 사도행전2 복사본.pdf  ↔  8. 사도행전2.pdf
```
"clearscan_cropped"가 아니라 파일명에 "복사본"이 붙은 패턴이다. 둘 다
완전히 처리됨(각자 `.md`+`chunks.txt`+`chunks_meta.json` 보유) — 원본
PDF 크기가 바이트 단위로 완전히 일치해 같은 파일의 중복 업로드로
확인된다. 원래 계획의 "clearscan_cropped 접미사" 그룹화 키로는 이
패턴을 절대 못 잡는다.

**삭제하면 안 되는 것 (원래 계획이 실수로 지울 위험이 있던 항목)**:
```
10. 로마서2clearscan_cropped.pdf
2. 마태복음2clearscan_cropped.pdf
13. 갈라디아서,데살로니가전후서clearscan_cropped.pdf
```
이 3개는 원본 없이 이게 **유일한 소스**다(각자 완전한 `.pdf`+`.md`+
`chunks.txt`+`chunks_meta.json` 세트). "clearscan_cropped 접미사
제거 후 번호로 그룹화" 방식은 서로 다른 책을 번호 접두사만으로
잘못 묶을 위험도 있다(예: `(NICNT)10. Philippians`와
`10. 로마서2clearscan_cropped.pdf`가 둘 다 "10"으로 시작).

---

## 2. 재제출 시 반드시 반영할 4가지

### (1) 그룹화/판별 로직을 두 가지로 분리
- **Orphan 판별**: `{stem}_pdf.md`는 있는데 `{stem}_pdf_chunks.txt` 또는
  `{stem}_pdf_chunks_meta.json`이 없는 파일 → 미완성 산출물 후보.
  단, 이 경우에도 "청킹 전이라 아직 안 만들어진 정상 대기 상태"와
  구분해야 한다 — `.batch_state.json`의 `processed` 목록에 파일명이
  있는데 chunks 파일이 없으면 orphan 확정, 없으면 그냥 미처리 대기
  파일이니 건드리지 않는다.
- **진짜 중복 판별**: 원본 PDF 파일 크기(바이트)가 완전히 일치하는
  두 개 이상의 `.pdf`가 `data/제련완성본`에 있고, 각각 완전한 처리
  세트(`.md`+`chunks.txt`+`chunks_meta.json`)를 가진 경우만 "중복"으로
  분류. 파일명 패턴(공백+"복사본" 등)이 아니라 **크기 일치를 1차
  판별 기준**으로 삼아라 — 파일명 접미사만으로 그룹화하지 말 것.

### (2) `.batch_state.json` 동기화
삭제(케이스 B) 또는 정리(케이스 A) 대상 파일이 `data/제련완성본/
.batch_state.json`의 `processed` 목록에 있으면, 파일 삭제와 **같은
트랜잭션 안에서** 해당 항목도 목록에서 제거하라. 파일은 지웠는데
`.batch_state.json`에는 남아있으면, 이번 세션에서 이미 발견·수정한
"고아 registry 엔트리로 인한 처리 대기열 모순" 버그와 동일한 클래스의
문제가 재발한다.

### (3) TSU dataset 중복 콘텐츠 확인
케이스 B(사도행전1/2 복사본)가 실제로 처리되어 `output/bench/
tsu_dataset.jsonl`(RetrievalEngine이 검색에 쓰는 실제 코퍼스)에도
중복으로 임베딩돼 있는지 먼저 확인하라. 있다면 파일 삭제만으로는
검색 결과에 남아있는 중복을 못 없앤다 — TSU dataset에서도 해당
source_file의 중복 레코드를 제거하는 단계를 계획에 포함시켜라(단,
이 재산정 로직 실행은 CUE 검토 후 별도 승인).

### (4) 실제 백업 자동화
"삭제 전 백업 권장"이라는 문서상 권고가 아니라, 스크립트 자체가 삭제
직전에 대상 파일을 `backups/cleanup_duplicate_outputs_{timestamp}/`
같은 경로로 실제로 복사한 뒤에만 삭제를 실행하도록 구현하라.

---

## 3. 산출물 요구사항 (변경 없음, 재확인)

- `scripts/cleanup_duplicate_outputs.py` — **삭제 전 확인 목록을
  출력하는 dry-run 모드가 기본**이어야 한다. 실제 삭제는 별도 플래그
  (예: `--execute`)로만 실행되며, 사용자의 명시적 확인 후에만 CUE가
  그 플래그로 재실행을 승인한다.
- 이 Task Order는 **계획 수정만 요청**한다. 스크립트 작성이든 실행이든
  ACT MODE 전환은 CUE가 수정된 계획을 다시 검토·승인한 뒤에만
  진행한다.
