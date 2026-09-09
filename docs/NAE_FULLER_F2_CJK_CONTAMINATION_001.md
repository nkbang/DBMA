# NAE Fuller F2 — TSU claim CJK 오염 및 대응

- 작성: CUE, 2026-09-09
- 발견 경로: `docs/NAE_FULLER_VOL01_SANDBOX_RETRIEVAL_TEST_001.md` (Vol.01 샌드박스 검색 테스트)
- HQ 결정: **(c) F2 완료 후 타깃 재추출/repair**

---

## 1. 현상

`my-theology-bot-v2:latest`(Qwen 계열)가 GPU 부하 상황에서 한국어 `claim`에
한자·중국어(간체/번체)·일본어 어휘를 코드스위칭으로 섞어 출력.

| 볼륨 | claim에 한자 포함 | 비율 |
|---|---|---|
| Vol.01 | 366 / 3,643 | 10.0% |
| Vol.02 (진행 중, 1,232 시점) | 103 | 8.4% |

- distinct 한자 런 233종, 총 529회.
- 소스 OCR 노이즈가 아니라 **모델 출력 결함**. 임베딩(bge-m3), 가독성, 인용 노출 모두 저하.
- 예: `깨닫고相信해야만真正한 믿음`, `구원에 대한荣耀는`, `우리的心을`, `큰 계命이다`.

## 2. 폐기된 방안 — (b) 순수 문자열 정규화

`scripts/nae_fuller_cjk_normalize.py` 구현·Vol.01 dry-run:
- 366건 중 278건(76%) 완전 치환, 88건 잔여.
- **치환의 98%(314/320)가 한글에 교착(glued)** → 조사·어미 파손:
  `荣耀는`→`영광는`(×`은`), `享受하는`→`누림하는`(×`누리는`),
  `真正로`→`진정로`(×`진정으로`), `계命이다`→`계생명이다`(×`계명이다`).
- 약 절반이 **눈에 안 띄는 문법 오류**를 주입 → 한자보다 나쁨(수정 신호 상실).
- 결론: 스크립트는 참고용으로 보존하되 **단독 적용하지 않음**.

## 3. 채택 방안 — (c) 타깃 LLM repair

`scripts/nae_fuller_cjk_reextract.py` (`--mode repair` 기본).

- 대상: `claim`에 한자가 남은 레코드만.
- 방식: 레코드당 `ollama.generate` 1회, temperature 0. 프롬프트는 **"섞인 한자
  토큰만 한글로, 구조·길이·의미 불변"** (source_text를 주지 않아 재유도 방지) +
  코드 측 drift guard(원문 1.6배 초과 출력 거부) + 출력 라벨/화살표 제거.
- **불변**: `id`·`doctrine`·`scriptures`·`citations`·`is_claim`·`page/para/sent` 무변경.
  `builder_version` 무접촉(`cjk_reextract_version` 별도 키). 원문은 `claim_raw` 보존.
- 결과별 `cjk_status`: `repaired` / `reextracted` / `residual`(한자 잔존 → `needs_review: cjk_residual`, F3行) / 실패는 무변경.
- 가드: `tsu_report.partial == true` 볼륨 거부(F2가 아직 쓰는 중) — `--allow-partial`로만 우회.
- `--mode reextract`: parser로 candidate 문맥 복원 후 실제 `claim.extract_claim`
  재호출, 새 결과가 is_claim=True·한자 없음일 때만 채택, 아니면 repair로 폴백.

### Vol.01 스모크(6건, tightened 프롬프트)

전부 한자 제거·의미 보존·길이 보존 확인:
`깨닫고 믿어야만 참된 믿음이다`, `하나님과 세상의 대립은`,
`구원에 대한 영광은 하나님께`, `우리 마음을 확신할 수 있다`.

## 4. 실행 시점 / 순서 (F2 완료 후)

1. F2 전 볼륨 `partial: false` 확인.
2. `python -m scripts.nae_fuller_cjk_reextract --all --apply` (GPU 유휴 시).
   Vol.01 ~366 + Vol.02–08 예상 ~700 ≈ 총 ~1,100건 × ~10s ≈ 3시간 내외.
3. 볼륨별 `cjk_reextract_report.json` 검토, `residual`·`failed` 건수 확인.
4. 샌드박스(`nae_tsu_fuller_sandbox_v0`) 변경분 재임베딩(디스포저블, 선택).
5. `residual`/`failed`는 F3 검수에서 `nae_fuller_review_recorder.py --redo`로 처리.
6. 커밋: 볼륨별 `tsu.json` + `cjk_reextract_report.json` + `tsu_report.json`.

## 5. 재발 방지

- F2 실행 중 다른 모델 로드·`ollama stop` 금지(기존 정책), GPU 단독 점유 유지.
- 향후 볼륨은 `-np 1` 순차(이미 확정, `NAE_FULLER_F2_PARALLEL_SPEEDUP_RESULT_001.md`).
- 장기: claim 추출 후처리에 한자 검출 게이트를 builder 파이프라인에 넣을지는
  별도 ADR Amendment 검토(현재 Architecture Freeze로 즉시 반영 불가).
