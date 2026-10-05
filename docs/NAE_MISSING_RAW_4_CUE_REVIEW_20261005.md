# CUE 독립 검토 (Rev.2): M2 원본 4개 누락

**판정: HOLD 유지** — 단, 범위를 "동일 체크섬 원본 4개 복원"으로 한정하면 **조건부 실행 승인을 권고**한다(§6). 전체 문제 종료·배포 승인과는 구분.
검토일: 2026-10-05 · 읽기 전용 (다운로드·manifest/ledger 변경·코퍼스 재빌드 없음. archive.org에는 HEAD 요청만 보냄)

저장 위치: `/Users/David/DBMA/.claude/worktrees/nae-missing-raw-4-cue-review-92a61d/docs/NAE_MISSING_RAW_4_CUE_REVIEW_20261005.md`
branch `claude/nae-missing-raw-4-cue-review-92a61d` · 커밋 해시는 보고 메시지에 기재 · 프로젝트 `docs/`에도 동일 사본 제출.

## 0. Rev.1 정정

- Rev.1의 "C1 복구안 부재" 판정은 **오류**였다. 복구안은 `/Users/David/DBMA/docs/NAE_MISSING_RAW_4_C1_RECOVERY_PLAN_20261005.md`(02:22 작성)에 있고, 내가 처음 확인한 시점엔 아직 없었다. 이번에 실제 내용으로 심사한다.
- Rev.1의 "Qdrant 응답 여부 미확인 → 런타임 불명"도 방법이 부적절했다. 이번엔 호출 경로·번들·데이터로 판정한다.

## 1. C1 복구안 심사

대상 checkout: `/Users/David/DBMA`, `fix/merge-production-path-safety`, `6f311d1f`.

**통과 항목**
- 4건의 source_id·raw_path·체크섬이 manifest/ledger와 일치.
- archive.org identifier 4개가 `BAPTIST_COMMENTARY_EMBEDDING_PLAN_v1.md` §5.2/5.11/5.13/5.14 기록과 일치(Spurgeon `treasuryofdavid0001chsp_d1s7` 직접 확인).
- 계획 URL(`<id>_hocr.html`)을 HEAD로 확인: 4건 모두 200. 크기도 기록과 일치 — Spurgeon 49,123,838 B(49.1MB), Gill 189,391,563 B(189MB), Carroll 22,997,304 B(~23MB), Broadus는 302 후 200(크기 헤더 미수신). 4건의 last-modified(2021-11~2026-03)가 모두 원 다운로드(2026-09)보다 앞서므로, 이후 재생성되지 않았을 개연성이 높다. **증거일 뿐 바이트 동일의 증명은 아니다.** archive.org가 제공하는 해시는 sha1/md5라 기존 sha256과 직접 비교 불가 → 다운로드 후 sha256 비교가 유일한 판정.
- 복원 대상이 gitignored이므로 git 상태 무변경, 롤백 절차(rm)가 유효.
- 백업 탐색 범위를 과장하지 않고 NAS "미확인"으로 정직하게 기술.

**수정 필요 (REQUEST_CHANGES 성격)**
1. **§3 단계 3의 validator 테스트 경로 오류.** `tests/test_validator_v22.py::TestValidatorIntegration::test_int_01_validator_passes`는 실제 대상이 아니다. 실패한 테스트는 `tests/test_m2_source_registry_governance.py::TestValidatorIntegration::test_int_01_validator_passes`다. 그대로 실행하면 검증이 엉뚱한 파일을 가리킨다.
2. **§4 "불일치 시 재다운로드"는 잘못된 완화책.** 같은 URL의 결정적 산출물을 다시 받아도 해시는 바뀌지 않는다. 올바른 규칙: 불일치 → 파일을 `/tmp` 격리 상태로 두고 **중단·HQ 보고**, 어떤 경로에도 배치하지 않는다. (§6 조건 3.)
3. **§6-3 "M2 source_manifest.yaml 갱신" 승인 요청 삭제.** 복원 대상 체크섬이 일치하면 manifest 변경은 필요 없고, 불일치 시의 manifest/ledger 변경은 ADR-030 Amendment B 재승인 사항이다. 이번 승인 범위에 섞으면 안 된다.
4. **단계 2의 `grep`은 해시 불일치를 실패로 처리하지 않는다**(grep이 빈 결과를 돌려줘도 스크립트가 계속 진행). 비교는 `[ "$(shasum -a 256 f | cut -d' ' -f1)" = "<expected>" ] || exit 1` 형태여야 한다.
5. **임시경로 `/tmp` 다운로드와 `cp`/`wget -O` 두 방식이 §2와 §3에 섞여 있다.** 하나로 통일(/tmp 검증 → 일치 시에만 `cp`)할 것. 직접 `wget -O`로 최종 경로에 쓰면 불일치 파일이 raw 트리에 남는다.
6. **누락**: 배치 후 읽기 전용 권한(`config.RAW_READONLY_MODE`, preserve 시 chmod 적용됨)과 `raw_preservation.verify()` 재검증 경로, ledger에 무기록 확인(`git status`/ledger diff 0줄) 단계. 디스크 여유 "기존 백업에 여유 있음"은 근거가 없으므로 `df -h` 실측으로 대체.
7. Gill `original.pdf`(2.58GB)는 복원 불필요 — 계획은 hocr만 대상으로 해 적절하나, 명시적으로 "PDF 비대상"을 적을 것.

## 2. 런타임·번들 호출 경로 (코드로 확인)

README(`README.md:33-34`)는 "Qdrant는 legacy, 현재 검색 경로에서 쿼리되지 않음"이라 하나 **정확하지 않다.**

- `ui/pages/chat.py:376`은 `NAE.reference_retrieval_adapter.search_reference(search_query, top_k=3)`를 호출하고, 이는 Qdrant `QdrantClient`로 검색한다(`reference_retrieval_adapter.py:116-127`). 즉 Qdrant는 **Smith 사전 경로에서 현재 사용 중**이다.
- 그러나 이 호출은 `collection_names`를 넘기지 않아 기본값 `[REFERENCE_COLLECTION_NAME]`(nae_ref_v1, Smith)만 조회한다(`:83`). 결과도 `source_id/volume`에 "smith"가 있는 것만 통과(chat.py:386-389).
- `nae_ref_commentary_v1`(`COMMENTARY_COLLECTION_NAME`)은 `NAE/pipeline/reference/config.py`, `ingest.py`, `scripts/nae_commentary_ingest.py`, 테스트에서만 참조된다. **채팅·검색 런타임에서 조회하는 호출은 없다.**
- 결론: README는 "Qdrant 미사용"이 아니라 "TSU가 주 경로, Smith 레퍼런스만 Qdrant"로 정정돼야 한다. 이는 별도 문서 정정 사안. 4권과의 관계에서는 결론이 바뀌지 않는다 — 4권의 파생 컬렉션은 런타임 비조회.

## 3. 파생 데이터의 TSU·배포물 포함 여부 (데이터로 확인)

`output/bench/tsu_dataset.jsonl`(119,595 청크, 217MB, 9/29) 전수 스캔:

- title/source_file/author에서 *Treasury of David, Exposition of the New Testament, Commentary on Matthew, Interpretation of the English Bible, Gill, Carroll* 어느 것도 **0건**.
- `source_provenance`/`nae_metadata`에 `BAP-COMM` 또는 `archive_org/reference` **0건**. `tsu_manifest.json`·`tsu_dataset.jsonl` 내 `BAP-COMM` 문자열 0건.
- Spurgeon 청크는 다수(MTP, Sermons, Till He Come 등)이나 **다른 저작**이다. Broadus 1,524청크는 *Preparation and Delivery of Sermons* 등으로 *Commentary on Matthew*가 아니다(계획서 §5.14가 구분한 대로).
- 배포 번들(`scripts/build_corpus_bundle.sh`, `dist/nae_baseline_corpus.tar.gz` 목록): `tsu_dataset.jsonl`, `tsu_manifest.json`, `registry/documents.json`, `bible/reference.json` 4파일만. 4권 raw·canonical·Qdrant 스냅샷 모두 미포함.
- 한계: `documents.json`은 위 문자열 검색만 수행했고 구조적 대조는 하지 않음. TSU 자체가 다른 판본의 같은 저작을 포함할 가능성은 title 기준으로 배제했으나 본문 중복 검사는 하지 않음. Qdrant 컬렉션의 현재 적재량은 이번에 조회하지 않음(런타임 비조회가 확인돼 판정에 불필요).

## 4. 배포 영향 판정

| 단계 | 판정 | 근거 |
|---|---|---|
| 제한 베타 | **비차단** | 4권 파생물이 TSU·번들·검색 경로에 없음(§2, §3). 사용자 기능 영향 없음 |
| 정식 배포 | **조건부** | 사용자 기능과 무관하나, M2/ledger가 "검증됨"으로 남은 채 재검증 불가한 상태는 추적성 갭. 복원+체크섬 일치(또는 재승인)로 해소 후 정식 Gate 통과 가능 |
| 개발·CI | 비차단 | raw 없는 환경은 skip. 단 부분 트리(Smith만 존재)에서는 skip 안 되고 실패 — 개발 머신에서만 재현 |

Rev.1의 "정식 차단"은 완화한다: 영향은 사용자-facing이 아니라 **무결성 증명(provenance)** 문제다.

## 5. 재발 방지 (Rev.1 유지·보강)

1. `raw_integrity_preflight`: M2 전 레코드의 존재 + sha256↔ledger 대조, `missing/mismatch/ok` 출력, 릴리스 Gate 포함.
2. `NAE_ASSET_PROFILE=full|no_raw` 명시 프로필. `_needs_nae_corpus`는 "raw 디렉터리 존재"만 보므로 부분 트리를 못 거름 — 교체는 별도 승인.
3. 다운로드 provenance 자동 기록(identifier, URL, ETag, 크기, sha256, 일시).
4. gitignored `NAE/corpus/raw/`를 백업 범위에 명시(`backups/`에 없었음이 증거).
5. 분기 복원 훈련 1권.
6. README의 Qdrant 서술 정정, 릴리스 보고서에 "알려진 실패 2건" 명시.

## 6. 실행 승인 권고 (동일 체크섬 원본 4개 복원만)

**권고: 조건부 APPROVE (복원 한정).** 아래 조건 충족 시 C1이 실행할 수 있다.

1. §1의 수정 1~7을 반영한 **개정 계획서**를 재제출하고 CUE가 확인. (실행은 개정 후.)
2. 사용자의 명시적 다운로드 승인 — 파일명·출처·크기 고지: hocr 4개 합계 약 **335MB**(49.1 + 189 + 80 + 23, Broadus는 문서 기록값).
3. 각 파일을 `/tmp`(또는 scratchpad)에 받아 sha256 비교. **일치한 파일만** 최종 경로에 배치. **불일치 파일은 배치하지 않고 중단·보고** — 재다운로드로 해결하려 하지 않는다.
4. 일치 후: 읽기 전용 권한 설정, `git status` 무변경, ledger/manifest diff 0줄 확인.
5. 재검증: `tests/test_m2_source_registry_governance.py`의 두 테스트(올바른 경로) + `scripts/m2_source_registry_validator.py` + M2 관련 테스트 파일 전체.
6. 본 승인 범위 **외(별도 승인)**: manifest/ledger 변경, 체크섬 불일치 시의 신원 유지/재등록, 코퍼스·Qdrant 재빌드, 병합·커밋·푸시, `_needs_nae_corpus` 정책 변경, README 정정.
7. 4개 일치 + 테스트·validator PASS는 **이 문제의 종료 조건**일 뿐 정식 배포 승인이 아니다.

## 7. C1 작업 격리 주의

C1 계획서는 `/Users/David/DBMA`(`fix/merge-production-path-safety`)를 기준으로 했다. 복원은 gitignored 파일이라 브랜치와 무관하지만, 같은 체크아웃에서 CUE/C1이 동시에 작업하지 않도록 한다(`git rev-parse --abbrev-ref HEAD` 확인은 계획서 §8 그대로 유지).

## 8. 한계

- 다운로드하지 않았으므로 체크섬 일치 여부는 **미확인**. HEAD 결과는 개연성 증거만.
- TSU 중복 검사는 메타데이터 문자열 기반. 본문 수준 중복은 미검사.
- Qdrant `nae_ref_commentary_v1` 적재량·현재 상태는 조회하지 않음.
- 전체 디스크·NAS 검색은 수행하지 않음.
