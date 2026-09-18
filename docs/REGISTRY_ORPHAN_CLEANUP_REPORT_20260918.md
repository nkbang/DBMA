# 제련완성본 레지스트리 고아 레코드 정리 — 2026-09-18

## 목표
`data/제련완성본/registry/documents.json`을 실물 파일과 1:1로 일치하는
배포 가능 상태로 정리한다.

## 현재 상태
완료. 진행률: 100%

- [x] "What Is Baptism?" 사용자 등록 자료 + 처리 산출물 삭제
- [x] 고아 레코드(실물 파일 없는 registry 항목) 전수 조사
- [x] 고아 레코드 220건 제거
- [x] baptism과 무관한 실물 데이터 4건(Broadus 2, Dargan 2) 보존
- [x] 원인 규명(아래)

## 수정 내용

| 항목 | 이전 | 이후 |
|---|---|---|
| `documents.json` 문서 수 | 287 | 67 |
| 실물 파일 수 (`data/RAW` + `data/제련완성본`) | — | 67 (일치) |
| `.batch_state.json` processed 목록 | 70 | 68 |
| `documents.json.lock` | 유휴 상태로 존재 | 삭제 |

제거 220건 = baptism 테스트 문서 2건 + 고아 레코드 218건
(2026-08-25 베타 리셋 당시 정리된 파일들의 잔존 메타데이터, 실물은
`backups/pre_beta_reset_20260825/RAW/`에만 존재).

## 원인 규명 — 남은 67건의 출처

67건(Broadus, Dargan, Hovey, Keach, Maclaren Expositions, Spurgeon 계열,
Whitefield Works)은 **사용자가 업로드한 자료가 아니라 베타 배포용 기본
동봉 코퍼스**다.

- 스크립트: `scripts/reset_for_release.py`
- 매니페스트: `scripts/baseline_corpus_manifest.json` (`"count": 67`,
  전량 퍼블릭 도메인, 출처는 `docs/RELEASE_ASSET_PROVENANCE.md`,
  `docs/DBMA_S2_4_CORPUS_EXPANSION_REPORT_001.md` 참고)
- 근거 커밋: `891b84e` (2026-09-15) — "S5 선결 — reset_for_release.py가 기본
  동봉 코퍼스를 지우는 충돌 해소". 이 커밋 이후 `reset_for_release.py
  --execute` 실행 시 RAW 초기화 → 매니페스트 기준 자동 재적재가
  일어나도록 계약이 바뀌었다.
- 파일 타임스탬프(2026-09-15 11:54~15:16)가 해당 커밋 직후와 일치 —
  스크립트 실행으로 인한 자동 재적재로 판단.

결론: 67건은 설계된 기본 동봉 코퍼스로 정상이며, 사용자 지시에 따라
그대로 유지한다.

## 다음 조치
없음. 필요 시 `scripts/baseline_corpus_manifest.json` 변경 여부만
추후 판단.
