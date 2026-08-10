# STEP5 Source Validation Script Plan

작성일: 2026-07-31
목적: 사람이 확보한 원문 파일을 ingest 전에 자동으로 1차 검증할 스크립트의 설계 계획. **이번 문서는 계획만 제공하며 스크립트 코드는 작성하지 않는다.**

## 목표

STEP5_SOURCE_MANUAL_VERIFY.md의 4개 수동 검증 항목 중, 기계적으로 자동화 가능한 부분을 스크립트화하여 사람의 검증 부담을 줄인다. 단, "원문이 실제로 정확한가"라는 의미 판단까지 자동화하지는 않음(그 부분은 여전히 사람 검증 영역).

## 검증 항목 (자동화 대상)

### 1. Encoding

- 파일이 UTF-8(또는 UTF-8 호환 ASCII)로 인코딩되었는지 확인
- Python 구현 방향: `open(path, encoding="utf-8").read()`가 `UnicodeDecodeError` 없이 성공하는지로 판정
- 실패 시: "UTF-8 아님, STEP5_HUMAN_ACQUISITION_GUIDE.md의 변환 절차 재수행 필요" 메시지 출력

### 2. Empty Section

- 조항 사이 또는 도입부에 비정상적으로 빈 구간(연속 공백 줄 과다, 또는 "Article N." 다음 본문이 없는 경우)이 있는지 확인
- 구현 방향: 정규식으로 `Article \d+\..*?(?=Article \d+\.|$)` 패턴을 매칭해 각 조항 블록을 추출, 블록 내 실제 텍스트 길이(공백 제외)가 최소 임계값(예: 20자) 미만이면 경고

### 3. Article Numbering

- 조항 번호가 1부터 연속으로 존재하는지(건너뛴 번호 없는지) 확인
- 구현 방향: 위에서 추출한 "Article N." 번호 목록을 정수로 변환해 `sorted(set(numbers)) == list(range(1, max(numbers)+1))` 검증
- 실패 시: 어떤 번호가 누락/중복되었는지 구체적으로 출력

### 4. Checksum

- 파일의 SHA-256을 계산해 출력 — provenance 기록(STEP5_HUMAN_ACQUISITION_GUIDE.md)에 채워 넣을 값을 자동 생성
- 구현 방향: `hashlib.sha256(path.read_bytes()).hexdigest()` (기존 `core/tsu_builder.py::_sha256_of_file()`와 동일 로직 재사용 가능 — 신규 구현 없이 함수 임포트만으로 충족 가능)

## 예상 인터페이스 (설계 초안, 미구현)

```
python scripts/validate_nae_source.py --file data/nae/sources/baptist/nhc_1833.txt

출력 예:
[PASS] encoding: utf-8
[PASS] checksum: 3f2a...  (registry provenance에 기록할 것)
[WARNING] empty_section: Article 12와 Article 13 사이 본문이 30자 미만
[PASS] article_numbering: 1~18 연속 확인
=== 결과: PASS=2 WARNING=1 FAIL=0 ===
```

- `core/tsu_builder.py::_sha256_of_file()`(기존 함수) 재사용 검토 — 신규 해시 로직 중복 구현 지양
- `scripts/check_environment.sh`(STEP1)와 유사한 PASS/WARNING/FAIL 출력 스타일 재사용 — 프로젝트 내 일관된 검증 스크립트 관례 유지

## 이번 단계에서 하지 않는 것

- 조항 내용의 신학적 정확성 검증 — 이는 여전히 사람이 원문 대조로 수행(STEP5_SOURCE_MANUAL_VERIFY.md 영역)
- 실제 스크립트 파일(`scripts/validate_nae_source.py`) 작성 — 코드 구현은 별도 승인 필요
- CI/자동 실행 연동 — 이번 계획 범위 밖

## 다음 단계

- 이 계획에 대한 HQ 승인 이후, 별도 Task Order로 실제 스크립트 구현 착수 가능
- 구현 시 `core/tsu_builder.py::_sha256_of_file()` 재사용 여부를 코드 조사로 재확인 필요(현재는 설계 문서 기준 재사용 가능성만 언급)
