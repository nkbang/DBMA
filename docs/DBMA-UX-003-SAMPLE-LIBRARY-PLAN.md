# DBMA-UX-003 — Sample Library 구현 Task Order

**문서 상태:** 발급됨 — 착수 전 HQ 결정 1건 필요
**작성일:** 2026-07-31
**선행 문서:** `docs/DBMA-UX-002-IMPLEMENTATION-PLAN.md` §5.1(이 Task의 근거가
된 갭 발견), `docs/DBMA-UX-DESIGN-BRIEF.md` §2.5, §4

---

## 1. 배경

UX-002 점검 중 확인된 것: `ui/pages/library.py`에는 "기본 자료(읽기 전용)
샘플" 개념 자체가 없고, 온보딩의 "샘플 자료로 시작하기" 버튼도 실제로는
아무 콘텐츠를 넣지 않는다(라벨은 이미 "바로 시작하기"로 정직하게 수정함,
`d2a21df`). 신규 사용자가 첫 실행 시 빈 Library를 보게 되는 상태이며,
이는 Design Brief §1.2 "Sample-driven Onboarding" 원칙 위반이다.

## 2. 목표

첫 실행 사용자가 Library에서 **이미 완성된 연구 예제**를 즉시 볼 수 있게
하고, "복사하여 내 자료로" 흐름으로 자유롭게 수정 가능한 자기 것으로
만들 수 있게 한다.

## 3. 착수 전 HQ 결정 필요 — 샘플을 어떻게 시스템에 넣을 것인가

두 가지 구현 경로가 있고, 비용·정합성이 다르다.

### 옵션 A — 실제 파이프라인으로 정식 처리 (권장)
샘플 원문(로마서 8장 연구 등, brief §4.1 텍스트 활용)을 RAW 폴더에 넣고
`core/processing.py`의 실제 추출→정제→청킹 흐름을 그대로 태워 registry에
등록한다. 장점: 실제 문서와 100% 동일한 방식으로 검색·연구 워크스페이스에
노출되어 별도 특수 케이스 코드가 필요 없음. 단점: 초기 셋업에 실제
처리 파이프라인 실행 필요(1회성).

### 옵션 B — registry에 직접 fixture 주입
`documents.json`/TSU 레코드를 스크립트로 직접 생성해 처리 과정을 생략한다.
장점: 빠름, 파이프라인 의존 없음. 단점: 실제 처리 결과물과 스키마가
미묘하게 어긋날 위험(발견하기 어려운 버그 소지), 파이프라인이 바뀔 때마다
fixture를 수동으로 맞춰야 함.

**본 Task Order는 옵션 A를 기본 전제로 작성한다.** 옵션 B를 원하면 착수
전에 알려줄 것.

## 4. 범위

### 포함
1. registry 스키마에 `is_sample: bool`(또는 유사) 필드 추가 —
   기존 필드(`ingest_status`, `superseded_by` 등)와 충돌 없이 확장
2. 샘플 원문 3~4건 준비 (Design Brief §4.1의 로마서 8장/주일 설교/칭의
   연구 텍스트를 실제 문서 파일로 작성 → RAW에 배치 → 처리)
3. `library.py`에 "기본 자료" 섹션 추가 — `is_sample=True` 문서를
   읽기 전용 UI로 표시 (수정/삭제 버튼 비활성화, 시각적 구분:
   `my_library.html` 목업의 `secondary-container` 뱃지 + 옅은 배경 참고)
4. "복사하여 내 자료로" 버튼 — 클릭 시 해당 문서의 processed
   .md/chunks/registry 레코드를 복제해 `is_sample=False`인 새
   document_id로 저장. 원본(샘플)은 그대로 보존
5. 온보딩 "바로 시작하기" 클릭 시 최초 1회 샘플 처리 트리거(이미
   처리돼 있으면 스킵) — 또는 별도 setup 스크립트로 미리 처리해두고
   앱은 존재 여부만 확인

### 제외
- Core 검색/청킹 로직 변경 (읽기 전용 필드 추가 외에는 손대지 않음)
- P1/P2 샘플 콘텐츠 확장 (일단 brief §4.1의 3건만)

## 5. 구현 순서

| 순서 | 작업 | 검증 |
|---|---|---|
| 1 | HQ가 §3 옵션 결정 | — |
| 2 | 샘플 원문 3건 작성 (실제 신학적으로 정확한 내용) | 육안 검수 |
| 3 | registry `is_sample` 필드 추가 + 마이그레이션 확인 | 기존 문서 영향 없음(기본값 False) 회귀 테스트 |
| 4 | 샘플 문서 처리 파이프라인 실행 (옵션 A) | registry에 정상 등록 확인 |
| 5 | Library "기본 자료" 섹션 UI 구현 | 읽기 전용 표시, 삭제 불가 확인 |
| 6 | "복사하여 내 자료로" 로직 구현 | 복사본이 독립적으로 수정 가능한지 확인 |
| 7 | 온보딩 연동 | 신규 세션 첫 진입 시 Library에 샘플 노출 확인 |

## 6. 완료 조건

- [x] §3 HQ 결정 기록 — **옵션 A** 채택 (2026-07-31)
- [x] 샘플 3건이 Library에 "기본 자료"로 표시됨 — 실 registry에 등록
      확인 (document_id 3건, `data/제련완성본/registry/sample_library.json`)
- [x] 기존 문서와 시각적으로 명확히 구분됨(읽기 전용 뱃지) —
      `_render_sample_library_section()` (secondary-container 톤 뱃지)
- [x] "복사하여 내 자료로" 정상 동작, 원본 보존 확인 — 실 데이터로
      end-to-end 검증(복사본 생성 → 독립 document_id 확인 → 검증용
      복사본은 정리함, 원본 3건은 그대로)
- [x] 기존 회귀 테스트 통과 — `pytest -k "library or registry or identity"`
      66 passed
- [ ] `docs/STATE.md` 갱신

## 8. 구현 노트

- Core 스키마(`core/identity_registry.py`)는 건드리지 않음 — `is_sample`
  플래그를 registry에 추가하는 대신 별도 side-file
  `core.config.DEFAULT_SAMPLE_LIBRARY_PATH`
  (`{output_dir}/registry/sample_library.json`, document_id 목록)로
  분리. C1 리뷰 GO 조건("Core architecture 임의 변경 금지")과 정합
- `data/`는 `.gitignore` 대상이라 샘플 원문 자체는 git에 안 잡힘 —
  대신 `scripts/sample_library_content/*.md` + `scripts/seed_sample_library.py`
  (멱등적 재실행 가능)로 버전관리, 다른 설치본(베타 배포 등)에서도
  재현 가능
- `ui/pages/library.py`: `_get_sample_source_files()`,
  `_render_sample_library_section()`, `_copy_sample_to_my_library()` 추가

## 7. 담당

**CUE 직접 수행.** 샘플 콘텐츠 저작(신학적 정확성 판단)과 registry
스키마 확장은 단순 치환이 아닌 개방형 판단이 필요해 C1 위임 대상이
아니다(C1 라우팅 기준).
