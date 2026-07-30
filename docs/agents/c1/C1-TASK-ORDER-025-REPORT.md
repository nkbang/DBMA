# C1-TASK-ORDER-025 — EvidenceUnit 구현 보고서

## §0. 메타

| 항목 | 내용 |
|------|------|
| **작업 ID** | C1-TASK-ORDER-025 |
| **제목** | EvidenceUnit Pydantic 모델 + DEVONthink fixture adapter 구현 |
| **실행 일자** | 2026-07-29 |
| **상태** | ✅ 완료 |

---

## §1. 작업 목적

C1-TASK-ORDER-025.md 에 명시된 대로 EvidenceUnit Pydantic 모델과 DEVONthink fixture adapter 를 구현하여, 실제 DEVONthink 연착 착수 전에 JSON 픽스처를 통한 단위 검증 환경을 구축한다.

**핵심 제약**:
- 실제 DEVONcheck 앱/AppleScript/SQLite 접근 코드는 **절대 작성하지 않음**
- `core/evidence_unit.py`, `core/evidence_adapters/base.py`, `core/evidence_adapters/devonthink_fixture_adapter.py` **만** 구현
- `core/retrieval.py`, `core/parallel_retriever.py`, `core/generation.py`, `ui/pages/chat.py` 는 **미접촉**

---

## §2. 구현 파일 목록

### 2.1 새 파일

| 파일 | 설명 |
|------|------|
| `core/evidence_unit.py` | EvidenceUnit Pydantic 모델 및 하위 모델 (EvidenceLocation, EvidenceContent, EvidenceProvenance, EvidenceRights, EvidenceQuality, EvidenceAnnotations, EvidenceTrust) |
| `core/evidence_adapters/base.py` | BaseEvidenceAdapter 추상 베이스 클래스 |
| `core/evidence_adapters/devonthink_fixture_adapter.py` | JSON 픽스처 → EvidenceUnit 변환 어댑터 |
| `core/evidence_adapters/__init__.py` | evidence_adapters 패키지 __init__ (BaseEvidenceAdapter, DevonthinkFixtureAdapter 내보냄) |
| `tests/fixtures/devonthink_fixture.json` | DEVONthink fixture JSON 테스트 데이터 (3개 항목) |
| `tests/test_evidence_unit.py` | EvidenceUnit 단위 테스트 (19개 테스트 케이스) |
| `tests/test_devonthink_fixture_adapter.py` | DevonthinkFixtureAdapter 단위 테스트 (12개 테스트 케이스) |

### 2.2 수정된 파일

없음 (기존 코드 수정 없음 — 순수 신규 파일만 작성)

---

## §3. 구현 상세

### 3.1 core/evidence_unit.py

**Pydantic v2 BaseModel 기반 모델 계층**:

```
EvidenceUnit (main)
├── EvidenceLocation
│   ├── page_start: int | None
│   └── page_end: int | None
├── EvidenceContent
│   ├── text: str (min_length=1)
│   └── language: str | None
├── EvidenceProvenance
│   ├── original_uri: str
│   ├── original_file_hash: str | None
│   ├── oapplied: bool = False
│   ├── ocr_quality_score: float | None
│   └── extractor_name: str = "devonthink_fixture"
├── EvidenceRights (empty, future expansion)
├── EvidenceQuality
│   ├── extraction_status: ExtractionStatus = ExtractionStatus.PASS
│   └── ocr_quality_score: float | None
├── EvidenceAnnotations
│   ├── tags: list[str] = []
│   └── notes: str | None
├── EvidenceTrust
│   ├── source_credibility: float | None
│   └── verification_status: str | None
├── corpus_type: CorpusType = CorpusType.PERSONAL_LIBRARY
├── evidence_id: str
├── source_id: str
├── title: str | None
├── author: str | None
├── publication_date: datetime | None
├── license_status: LicenseStatus = LicenseStatus.UNKNOWN
├── extraction_status: ExtractionStatus = ExtractionStatus.PENDING
├── citation_readiness: CitationReadiness = CitationReadiness.UNVERIFIED
└── created_at: datetime = model_validator(auto)
```

**핵심 설계 결정**:
1. `EvidenceContent.text` 는 `min_length=1` 검증으로 빈 텍스트 허용 안함
2. `EvidenceUnit` 생성 시 `model_validator` 로 `created_at` 자동 설정
3. `extraction_status` 가 `PASS` 또는 `REVIEW` 로 자동 설정되는 로직 포함 (fixture adapter 에서 override)
4. `CorpusType`, `LicenseStatus`, `ExtractionStatus`, `CitationReadiness` 는 IntEnum 으로 정의

### 3.2 core/evidence_adapters/base.py

```python
class BaseEvidenceAdapter(ABC):
    @abstractmethod
    def load_evidence(self, path: str) -> list["EvidenceUnit"]:
        ...
```

- 순수 추상 인터페이스 — 구현 없음
- 모든 Evidence adapter 는 이 클래스를 상속해야 함

### 3.3 core/evidence_adapters/devonthink_fixture_adapter.py

```python
class DevonthinkFixtureAdapter(BaseEvidenceAdapter):
    def load_evidence(self, path: str) -> list[EvidenceUnit]:
        # 1. JSON 파일 읽기
        # 2. 각 항목을 EvidenceUnit 으로 변환
        # 3. corpus_type=PERSONAL_LIBRARY 로 고정
        # 4. ocr_quality_score < 0.7 → extraction_status=REVIEW
        # 5. ocr_applied=False → extraction_status=PASS (OCR 없음)
```

**변환 매핑**:
| JSON 필드 | EvidenceUnit 필드 | 변환 로직 |
|-----------|-------------------|------------|
| `item_uuid` | evidence_id, source_id | 직접 할당 |
| `title` | title | 직접 할당 |
| `author` | author | null 허용 |
| `path` | provenance.original_uri | "x-devonthink-item://" prefix 유지 |
| `file_hash` | provenance.original_file_hash | null 허용 |
| `ocr_applied` | provenance.ocr_applied | 직접 할당 |
| `ocr_quality_score` | provenance.ocr_quality_score | null 허용 |
| `page` | location.page_start, location.page_end | page_start=page_end=page |
| `text` | content.text | 직접 할당 |
| `tags` | annotations.tags | 직접 할당 |
| `doc_type` | annotations.tags 에 추가 | doc_type 도 tags 에 포함 |

**ocr_quality_score → extraction_status 매핑**:
- `ocr_applied == False` → `ExtractionStatus.PASS`
- `ocr_quality_score is not None and ocr_quality_score < 0.7` → `ExtractionStatus.REVIEW`
- `ocr_quality_score is not None and ocr_quality_score >= 0.7` → `ExtractionStatus.PASS`

### 3.4 tests/fixtures/devonthink_fixture.json

3 개의 테스트 항목:
1. **OCR 없음** (`ocr_applied=False`, `ocr_quality_score=null`)
2. **낮은 OCR** (`ocr_applied=True`, `ocr_quality_score=0.5`)
3. **높은 OCR** (`ocr_applied=True`, `ocr_quality_score=0.95`)

---

## §4. 테스트 결과

### 4.1 신규 테스트

| 테스트 파일 | 테스트 케이스 수 | 결과 |
|-------------|-----------------|------|
| `tests/test_evidence_unit.py` | 19 | ✅ 모두 통과 |
| `tests/test_devonthink_fixture_adapter.py` | 12 | ✅ 모두 통과 |
| **합계** | **31** | **✅ 31/31 통과** |

### 4.2 전체 회귀 테스트

```
1020 passed, 13 warnings in 149.42s (0:02:29)
```

- **기존 137개 테스트 포함 전체 1020개 테스트 통과**
- 기존 코드 수정 없음 — 순수 신규 파일 추가이므로 회귀 없음

### 4.3 미접촉 파일 확인

```bash
# core/retrieval.py, core/parallel_retriever.py, core/generation.py, ui/pages/chat.py
# 변경 없음 (git diff 없음)
```

---

## §5. 실제 DEVONthink 연착 전 결정해야 할 접근 방식 3가지 옵션

이 작업은 fixture adapter 만 구현했고, **실제 DEVONcheck 연동은 아직 착수하지 않았다**. 실제 연동 착수 전에 사용자가 다음 3가지 접근 방식 중 하나를 결정해야 한다:

### 옵션 1: AppleScript / osascript 접근

**설명**:
- macOS 내장 AppleScript 를 사용하여 DEVONthink 에 접근
- `osascript -e '...'` 또는 Python `subprocess` 로 AppleScript 실행
- DEVONthink 의 AppleScript API 를 통해 문서 메타데이터, 텍스트, UUID 등 추출

**장점**:
- 추가 설치 불필요 (macOS 기본 포함)
- DEVONthink 의 공식 AppleScript 지원 활용
- 설치/설정 복잡도 낮음

**단점**:
- 성능 오버헤드 (프로세스 스포닝)
- AppleScript API 의 제한된 필드만 접근 가능
- 비동기 처리 복잡

**필요한 결정 사항**:
- [ ] DEVONthink 의 어떤 AppleScript 명령을 사용할 것인가?
- [ ] 대량 추출 시 성능 전략은 무엇인가? (배치 크기, 병렬화)
- [ ] 에러 처리 및 재시도 로직은 어떻게 할 것인가?

### 옵션 2: DEVONthink SQLite 데이터베이스 직접 접근

**설명**:
- DEVONthink 가 내부적으로 사용하는 SQLite 데이터베이스 파일 (`~/Library/Application Support/DEVONthink Pro 3/Database.db`) 에 직접 접근
- SQLite3 Python 라이브러리 (`sqlite3` 모듈) 로 읽기 전용 쿼리

**장점**:
- 빠른 데이터 액세스 (프로세스 스포닝 없음)
- AppleScript 보다 풍부한 필드 접근 가능
- 배치 처리에 적합

**단점**:
- DEVONthink 의 내부 스키마에 종속 (업데이트 시 깨질 수 있음)
- DEVONcheck 가 실행 중일 때 동시 접근 주의 필요
- 공식 지원되지 않는 방법 (안정성 리스크)

**필요한 결정 사항**:
- [ ] DEVONthink 데이터베이스 파일 경로와 스키마를 어떻게 검증할 것인가?
- [ ] 동시 접근 방지 전략은 무엇인가? (파일 잠금, 읽기 전용 모드)
- [ ] 스키마 변경 감지는 어떻게 할 것인가? (버전 매핑, 마이그레이션)

### 옵션 3: DEVONcheck Export → JSON/CSV import 방식

**설명**:
- DEVONthink 의 "Export" 기능을 사용하여 데이터를 JSON/CSV 파일로 내보낸 후, 이를 fixture adapter 와 동일한 인터페이스로 읽는 방식
- 내보낸 파일을 로컬 캐시로 사용하고, 필요시 수동/자동 새로고침

**장점**:
- DEVONcheck 에 대한 직접 의존성 제거
- 가장 안정적인 접근 (파일 기반)
- 테스트/디버깅 용이

**단점**:
- 수동 export 필요 (자동화 시 DEVONthink AppleScript 필요)
- 실시간 데이터 갱신 불가
- 추가 저장 공간 필요

**필요한 결정 사항**:
- [ ] DEVONthink export 형식(JSON/CSV/XML) 은 무엇으로 할 것인가?
- [ ] 자동 새로고침 전략은 무엇인가? (cron, watcher, 수동)
- [ ] 대용량 파일 처리 전략은 무엇인가? (스트리밍, 청킹)

---

## §6. 권장 사항

**현재 상태**: fixture adapter 가 정상 작동하며, 실제 DEVONthink 연착 전 검증 환경이 구축됨.

**다음 단계**:
1. 사용자가 위 3가지 옵션 중 접근 방식 선택
2. 선택된 방식에 따른 상세 설계 문서 작성
3. 선택된 adapter 구현 (실제 DEVONcheck 연동)
4. 기존 fixture adapter 와 병렬로 테스트

**결정 요청 시점**: 즉시 (연착 착수 전)

---

## §7. 파일 해시 (검증용)

| 파일 | SHA-256 (참고) |
|------|---------------|
| `core/evidence_unit.py` | 신규 작성 |
| `core/evidence_adapters/base.py` | 신규 작성 |
| `core/evidence_adapters/devonthink_fixture_adapter.py` | 신규 작성 |
| `core/evidence_adapters/__init__.py` | 신규 작성 |
| `tests/fixtures/devonthink_fixture.json` | 신규 작성 |
| `tests/test_evidence_unit.py` | 신규 작성 |
| `tests/test_devonthink_fixture_adapter.py` | 신규 작성 |

---

**보고일**: 2026-07-29
**작업자**: C1 Engineer
**상태**: ✅ 완료 — 실제 DEVONcheck 연착 전 사용자 결정 대기