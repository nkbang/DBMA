# 배포 전 보안 체크리스트 판정 — S1-3

- 생성: 2026-09-21T18:12:50
- 모드: 판정만(dry-run)
- 근거: `project_rag_security_pre_deploy.md`(2026-07-28) 5개 항목, `scripts/security_preflight.py`로 자동 판정

| # | 항목 | 판정 | 근거 |
|---|---|---|---|
| 1 | Qdrant 로컬 인증 | **해당없음** | core/retrieval.py에 QdrantClient/qdrant_client 사용 코드가 없다 — self.qdrant_url은 저장만 되고 읽는 코드가 없는 죽은 파라미터(3회 등장: __init__ 시그니처 1 + 대입문 2, 전부 core/retrieval.py:1403,1409). 배포판 실행 경로는 TSU 전량 메모리 적재 방식이라 Qdrant 자체를 쓰지 않는다. 인증 설정 대상이 없다. |
| 2 | 디스크 암호화(FileVault) | **적용됨** | FileVault is On. |
| 3 | RAW 디렉터리 권한(700) | **적용됨** | data/RAW = 0700 |
| 4 | 인제스트 로그 출처+타임스탬프 | **적용됨** | core/identity_registry.py::register_document()가 record['source_file']과 record['created_at']을 기록한다(문서별 registry 레코드 = 인제스트 감사 로그 역할). |
| 5 | 업로드 문서 최소 스캔 | **부분 충족** | core/noise_classifier.py 존재(True) — content_quality.quality_score로 노이즈/저품질 텍스트는 걸러내지만, 프롬프트 인젝션 패턴(반복 지시문 등) 전용 탐지는 없다. 별도 기능으로 백로그에 남긴다(이번 preflight 범위 밖 — 새 스캐너 구현은 S1-3의 '점검'이 아니라 별도 설계 작업). |

## 배포 판정 (R7)

R7 통과 — '사용자 조치 필요'는 항목 2(FileVault, 목회자 개인 기기 설정이라 앱이 강제 불가)뿐이며 INSTALL.md 권고 문구로 대응한다. 항목 5(부분 충족)는 배포를 막는 결함이 아니라 별도 백로그다.
