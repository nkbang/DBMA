# NAE C1 Current Activity — HQ Report 001

- 작성: CUE
- 작성일시: 2026-08-15 15:56 CDT (2026-08-15T20:56Z)
- 대상: Rev. Bang / HQ
- 근거: CUE가 직접 재실행·재조회로 검증한 사실만 기록. C1의 서술은 참고용으로만 인용.

---

## 한 줄 요약

C1은 지금 **NAE 신학 원문 8권(Fuller Complete Works Vol01–08)의 TSU(Theological
Statement Unit) 후보를 LLM으로 추출하는 장기 백그라운드 작업**을 수행 중이다.
Vol01이 5.5% 진행됐고, 나머지 7권은 Vol01 완료 후 자동으로 이어받도록 큐에
대기 중이다. 임베딩·Qdrant 색인(실제 검색 반영)은 **사람의 신학적 검토가
선행돼야 하는 별도 단계**이며, 이번 작업 범위가 아니다.

---

## 임무 계보 (오늘 밤 순서)

1. **NAE Production Retrieval Bridge** — 완료, CUE 재검증 통과 (커밋 `4a3e616`)
2. **ADR-023 Amendment A Host Executor** — n8n 대신 호스트 프로세스가
   `cli_driver.py`를 직접 호출하도록 구현·검증 (커밋 `f57407d`)
3. **Registration 10건**(Dagg, Hiscox, Fuller Vol01-08) — 실제 등록 완료,
   CUE 독립 재검증 통과 (커밋 `28caa7b`, `f57407d`)
4. **Night Shift Order 003(진행 중)** — Registration 완료 10건 중 아직 TSU가
   없는 것에 한해 TSU 생성 연결 (커밋 `72ff24a`, `737420e`)

## 지금 C1이 실제로 하는 일

| 항목 | 내용 |
|---|---|
| 대상 | `Fuller_Complete_Works_Vol01` (Andrew Fuller 전집 1권) |
| 실행 방식 | launchd 백그라운드 프로세스 (PID 88689) |
| 실행 커맨드 | `python -m NAE.pipeline.tsu.runner --identifier Fuller_Complete_Works_Vol01` |
| 하는 일 | 원문 5,452개 후보 문단·각주·성경구절에 대해 로컬 LLM(`my-theology-bot-v2:latest`, 42GB)으로 신학적 주장(claim)·교리 분류를 추출 |
| **현재 진행률(CUE 직접 재조회, 15:56 CDT)** | **400 / 5,452 (7.3%)**, claims 281개 추출, 오류 0건 |
| 처리 속도 실측 | 후보당 약 10.7초 |
| 예상 완료 | 이 1권만 약 16~17시간 후 |

## 왜 Dagg·Hiscox는 건드리지 않았나

착수 전 CUE가 직접 Qdrant를 조회해 **Dagg·Hiscox 2건은 이미 2026-08-09에
TSU 생성·임베딩·색인이 완료돼 있음**을 확인했다(Qdrant 실측 point 존재).
게다가 그때 쓰인 식별자 체계(`work_id`)가 어젯밤 Registration이 새로 계산한
것과 달라 **중복 임베딩 위험**이 있어, 이번 작업 대상에서 명시적으로
제외했다. 이 식별자 불일치는 별도 정리가 필요하며 이번 임무 범위가 아니다.

## 나머지 7권(Vol02-08)은 어떻게 되나

Vol01 완료를 기다리는 순차 큐를 CUE가 별도로 준비해뒀다(PID 26127). Vol01이
끝나면 자동으로 Vol02→...→Vol08 순서로 동일 작업을 이어간다. 한 권이라도
실패하면 큐는 **자동으로 멈추고** 사람의 확인을 기다리도록 설계했다(다음
권으로 그냥 넘어가지 않음).

**8권 전체 완료까지 실측 기반 예상: 약 130~170시간.**

## 이번 작업이 하지 않는 것 — 임베딩/색인은 별도 승인 필요

`scripts/nae_incremental_ingest.py`(임베딩·Qdrant 색인 담당)는 코드 자체가
`review_status == "verified"`인 레코드만 처리한다. 이건 **"사람이 신학적
검토를 완료했다"**는 뜻으로, `NAE/pipeline/tsu/review_promotion.py` 문서에
그렇게 명시돼 있다. 오늘 밤 생성되는 TSU는 전부 `"generated"` 상태로만
남고, 검색에 실제로 반영(임베딩·색인)되려면 **누군가 신학적으로 검토해서
승격시키는 별도 단계**가 필요하다. C1/CUE가 이걸 자동으로 우회하지
않았다 — 의도된 품질 게이트다.

## 감시 체계

CUE가 1시간 간격 자동 점검을 걸어뒀다. 진행률 정체·프로세스 이상 종료·큐
STOP 발생 시 1시간을 기다리지 않고 즉시 보고한다.

## Production 안전성 (CUE 독립 확인)

| 항목 | 상태 |
|---|---|
| `core/retrieval.py` | 무변경 확인 |
| DBMA 메인 코퍼스(`data/제련완성본`) | 무변경 확인(착수 전 무관한 프로세스가 실행돼 잠시 위험했으나 실제 변경 없이 종료됨을 확인) |
| Qdrant `nae_tsu_v1` | baseline 3,319 points, 아직 mutation 없음(임베딩 단계 전) |
| 사람 큐레이션 문서(`resources/theological_sources/`) | 무변경 확인 |

## 다음 사람이 결정할 사항

1. Vol01(및 이후 볼륨)의 TSU 후보 중 어떤 것을 검토·승격할지 — 이건 신학적
   판단이라 CUE가 대신할 수 없다.
2. Dagg·Hiscox의 identity 체계 불일치를 언제, 어떻게 정리할지.
3. 130~170시간 규모의 전체 배치를 계속 진행할지, 특정 권만 우선할지.
