# C1 Task Order 072 — 침례교 조직신학/주석 코퍼스 공백 해소 (게이트 포함 재발주)

- 발주자: CUE
- 일자: 2026-09-28
- 유형: **조사 우선 + 조건부 구현** — 일부 항목은 Architecture Freeze Rule
  적용 대상 (STOP)
- 근거: CUE 조사(2026-09-26~28, 본 세션), C1 자체 조사 보고(2026-09-27),
  `docs/STATE.md`(2026-09-23 HQ 결정 항목), ADR-030 §7.3 M2 FROZEN BASELINE
- 교차검증 규칙 적용: [[feedback_cue_c1_cross_validation_rule]] —
  이 Task Order의 모든 산출물은 CUE가 V0-V9로 재검증한다. C1의 자체
  GREEN/완료 선언은 승인이 아니다.

---

## 0. 왜 "재발주"인가 — 이미 시작된 작업 발견

이 Task Order 없이 이미 작업이 시작됐다. `~/DBMA`(`feat/peb-v0.1`)에
**미커밋 staged 변경**이 다음과 같이 존재한다(2026-09-28 CUE 확인,
`git status --short` / `git diff --cached --stat` 원문):

```
 M  config.yaml                          (nae_pd.enabled: false → true)
 M  core/candidate_generator.py          (+31/-… , open_or_build_index 카운트 방식 변경)
 M  core/hybrid_candidate_pipeline.py    (+149/-…, tsu_by_id lazy-load, force_route 추가)
 A  scripts/merge_nae_corpus.py          (신규 224줄)
 A  scripts/process_unprocessed_nae.py   (신규 226줄)
 A  scripts/test_default_corpus_query.py (신규 91줄)
```

**지금 즉시 지켜야 할 것**: 이 6개 파일을 **커밋하지 말 것**. push도
하지 말 것. `core/candidate_generator.py`, `core/hybrid_candidate_pipeline.py`는
CLAUDE.md "반드시 지켜야 하는 사항"의 Retrieval Engine에 해당한다 —
CUE가 아래 §3 절차로 V0-V9 검증을 마치기 전에는 그대로 staged 상태로
둔다. `config.yaml`의 `nae_pd.enabled: true`도 마찬가지 — §2-B 사유로
보류.

---

## 1. 배경 (이미 확인된 사실 — 재조사 불필요)

1. 생산 TSU(`output/bench/tsu_dataset.jsonl`, 2026-09-28 CUE 실측) =
   **119,595건 / 74문서 / 100% 영어**. `doc_type` 분포: 설교 38, 기타
   35, **주석 1**(`Spurgeon_MTP_Vol50.txt` = *Metropolitan Tabernacle
   Pulpit* — 실제로는 설교집, 오분류). **실제 주석서 0권, 조직신학서
   0권.**
2. `NAE/corpus/tsu/`에 Fuller Complete Works(8권, 33,132건)·Dagg
   Church Order(3,377건)·Hiscox Standard Manual(740건)이 이미 TSU로
   처리돼 있으나 생산 파이프라인 미통합 — 게이트가
   `modules.nae_pd.enabled`(기본 `false`) 단 하나.
3. **2026-09-23 HQ 결정**(`docs/STATE.md`)이 이미 이 정확한 질문에
   답했다: "Fuller/Dagg/Hiscox 별도 편입(옵션 3)도 **이번 결정에
   포함되지 않는다** — 필요 시 별도 HQ 승인 후 착수." 즉 이 병합은
   **아직 승인된 적이 없다.**
4. ADR-030 §7.3 M2는 Fuller Vol01-08 + Dagg + Hiscox 14개 레코드를
   `historical_witness×10 + reference×4` 카운트로 **FROZEN BASELINE**
   지정했다 — Architecture Freeze Rule 대상. 이 스냅샷 구성을 바꾸는
   어떤 작업도 새 ADR Amendment 없이는 금지.
5. SLBC1689은 ADR-030 이력상 **N-8 BROKEN**, PBC1742는 **FAILED**로
   이미 판정 종료된 상태(재시도 이력 있음).
6. Smith Bible Dictionary(`nae_ref_v1`, Qdrant, 34,948건)는 이미
   완료된 별도 트랙(reference 계층, TSU 병합 대상 아님) — 단, 실제
   배포판에는 로컬 Qdrant 서버가 전혀 provisioning되지 않아(CUE
   확인, `scripts/setup_beta_tester.command`에 Qdrant/Docker 기동
   로직 없음) 이 전체 reference 계층(Smith + 새로 연결한 Baptist
   commentary, PR #89)이 **테스터 배포판에서는 항상 빈 결과**를
   반환한다.

이 6개 사실은 CUE가 이미 파일을 직접 읽어 확인했다. 이 Task Order가
요청하는 것은 아래 §2의 작업뿐이다.

---

## 2. 작업 범위 — 두 트랙

### 트랙 A — 즉시 진행 가능 (Architecture Freeze 대상 아님)

**A-1. 이미 staged된 성능 최적화 diff의 자체 문서화**
`core/candidate_generator.py`의 `open_or_build_index()` 카운트 방식
변경(라인 순회 → `tsu_manifest.json.tsu_count` 참조)에 대해:
- 변경 전/후 각각 실측 시간(초) — 명령과 출력 원문 첨부
- `tsu_manifest.json`이 없는 최초 실행 시 fallback 경로가 실제로
  동작하는지 별도 테스트로 확인
- 기존 테스트(`tests/test_candidate_generator.py`) 전체 재실행 결과

**A-2. `hybrid_candidate_pipeline.py`의 lazy-load + `force_route` 변경 근거**
- 왜 `tsu_by_id`를 lazy-load해야 했는지(무엇의 몇 초를 줄이는지) 실측
  전/후 비교
- `force_route` 파라미터가 기존 번역 재시도 로직과 정확히 어떻게
  다른지 — "로직 변경 없음"이라 적혀 있던 기존 docstring을 그대로
  지운 이유
- **삭제된 주석 복원 검토**: `_corpus_has_book_ids()`의 기존
  주석(2026-09-26, 책 이름 포함 질의 구조적 0건 문제의 근거 설명)이
  삭제됐다. 이 설명은 향후 회귀를 막는 근거 문서였다 — 삭제 사유를
  명시하거나, `[P1 최적화]` 주석에 흡수해 원래 설명을 보존할 것.
- `tests/test_hybrid_candidate_pipeline.py` 전체 재실행 결과

**A-3. "19초 지연"이 콜드스타트인지 회귀인지 재현**
같은 질의("삼위일체" 등)를 **연속 2회** 실행해 1회차/2회차 시간을
각각 기록. STATE.md는 1회성 Tantivy 부트스트랩을 최대 36초로
문서화했다 — 1회차만 느리고 2회차부터 ~1초대면 회귀 아님, 매번
느리면 별도 원인 조사가 필요하다는 뜻이니 그 결과만 보고.

**A-4. SLBC1689/PBC1742/PBC1765 재확인 (재처리 시도 금지)**
ADR-030 이력에서 BROKEN/FAILED 판정 근거를 인용만 하고, 왜 여전히
미처리 상태인지 한 문단으로 정리. **새로 처리를 시도하지 말 것**
(§STOP 8 참고).

### 트랙 B — STOP, HQ 승인 먼저 필요 (조사만, 실행 금지)

**B-1. Fuller/Dagg/Hiscox → 생산 TSU 병합** (`scripts/merge_nae_corpus.py`)
이 스크립트를 **실행하지 말 것**. 대신 다음만 제출:
- 병합했을 때 ADR-030 §7.3의 `historical_witness×10 + reference×4`
  카운트 검증(`tests/test_m2_source_registry_governance.py` 등)이
  깨지는지 정적으로 분석
- 병합 후 예상 TSU 건수/출처 수
- "2026-09-23 HQ 결정이 이 작업을 명시적으로 보류했다"는 사실을
  최종 보고서 최상단에 명시

**B-2. `modules.nae_pd.enabled: true`**
이 변경이 B-1(병합)과 독립적으로 안전한지, 아니면 활성화만으로도
`ui/pages/research.py` / `ui/components/nae_public_section.py`가
아직 병합 안 된 `NAE/corpus/tsu/`를 참조해 에러를 내는지 **읽기만
해서** 판단. 실제로 `true`로 둔 채 커밋하지 말 것 — staged된 현재
diff를 되돌리지는 말고(HQ가 볼 수 있게) 그대로 두되 커밋만 보류.

**B-3. 한국어 콘텐츠 추가**
이번 Task Order 범위 밖. 새 RAW 자료 확보·저작권 확인이 선행돼야
하는 별도 트랙(`docs/RELEASE_ASSET_PROVENANCE.md` 선례 참고) —
손대지 말 것.

---

## 3. STOP 조건

아래 중 하나라도 해당하면 계속 진행하지 말고 `STOP CONDITION
TRIGGERED`로 보고(몇 번 조건인지 + 근거 출력 포함):

1. `output/bench/tsu_dataset.jsonl`을 실제로 쓰기/교체하게 됨
2. `data/제련완성본/registry/documents.json`을 수정하게 됨
3. ADR-030 §7.3 M2 FROZEN BASELINE 14개 레코드 구성이 바뀜
4. `core/retrieval.py`(RetrievalEngine 본체)를 수정해야 함
5. B-1/B-2를 커밋하거나 push하게 됨
6. 기존 테스트(A-1/A-2 재실행분 포함)가 회귀함
7. `tests/nae/` 바깥에서 운영 데이터 경로(`NAE/corpus/`, Qdrant)를
   테스트가 직접 읽게 됨
8. SLBC1689/PBC1742/PBC1765을 새로 처리하려는 시도가 필요해 보임
9. 이 Task Order의 허용 파일(§2 목록) 밖의 파일을 만들거나 고쳐야 함

---

## 4. 공통 규칙

- **커밋 금지**: CUE GREEN + HQ 승인 전에는 트랙 A 산출물도 커밋하지
  않는다. 지금 staged된 6개 파일도 마찬가지 — 그대로 두고 되돌리지
  말 것.
- **판정 금지**: C1은 GREEN/APPROVED를 선언하지 않는다. 보고서 마지막
  줄은 `HOLD` / `CUE READ-ONLY REVALIDATION REQUESTED` /
  `STOP CONDITION TRIGGERED` 중 하나.
- **증거**: 모든 수치(초, 건수, 테스트 통과 수)에 그 수치를 만든
  명령과 출력 원문을 그대로 붙인다. 출력 없는 수치는 CUE가 무효
  처리한다.
- **실행 환경**: `~/envs/dbma311/bin/python -m pytest`, 작업 위치
  `/Users/David/DBMA`, 브랜치 `feat/peb-v0.1`.

---

## 5. 보고 형식

`docs/agents/c1/C1-TASK-ORDER-072-REPORT.md` 하나로 제출:
1. §0 staged diff에 대한 A-1/A-2 설명·재실행 결과
2. A-3 콜드스타트 재현 결과
3. A-4 SLBC1689/PBC1742/PBC1765 인용 정리
4. B-1/B-2 영향 분석(실행 없이)
5. 마지막 줄: `HOLD` / `CUE READ-ONLY REVALIDATION REQUESTED` /
   `STOP CONDITION TRIGGERED`

제출 후 CUE가 V0-V9(`docs/grounded_synthesis/GS-00-JOURNEY-INDEX.md`
§5 절차 재사용)로 교차검증한 뒤에만 트랙 A 커밋 여부를 정한다.
트랙 B는 CUE 검증과 무관하게 **HQ의 별도 승인**이 있어야 다음
Task Order로 넘어간다.
