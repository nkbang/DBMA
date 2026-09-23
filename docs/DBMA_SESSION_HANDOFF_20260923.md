# 세션 이양 — 2026-09-23

## 1. 한 줄 요약

코퍼스 트랙 결정(Spurgeon 67종 채택)이 확정되고 S6-4(Release 발행)까지
끝났다. **다음 세션은 S6-2(P0-5 24건 인적 채점)부터 시작한다.**

---

## 2. 이번 세션에서 끝난 일

1. **코퍼스 트랙 HQ 결정** — C1 Task Order 070(사실조사)을 CUE가 전량
   독립 재검증(grep/`wc -l`/`stat` 실측 전부 일치) 후 사용자에게 3개
   옵션 제시 → **옵션 (1) Spurgeon 67종/130,401건을 기준선으로 확정**.
   `docs/STATE.md`(2026-09-23 HQ 결정 항목), PR #68.
   - Track A(125종, 한글 자료·Fuller/Dagg/Hiscox) 복구는 **채택 안 함**.
   - Fuller/Dagg/Hiscox 별도 편입도 이번 결정에 **포함 안 됨** — 필요
     시 별도 HQ 승인 후 착수.
2. **S6-4 — GitHub Release 발행** — `beta-v1.3.0-rc6` 태그 생성, 코퍼스
   번들(`nae_baseline_corpus.tar.gz`, 48MB) 빌드·업로드,
   `BETA_LATEST_TAG.txt` 갱신(PR #69). `install_nae_beta.command`가
   실제로 쓰는 두 URL(manifest raw, release asset)을 curl로 직접 검증—
   둘 다 정상.
3. **미커밋 문서 5건 정리** — 이전 세션들에서 `~/DBMA`에만 존재하던
   C1 리뷰 결과 3건 + P0-5 재실행 결과 + 보안 체크리스트 재실행 결과를
   정식 커밋(PR #70).

---

## 3. 다음 세션이 할 일 — S6-2 (최우선)

**P0-5 대표 질의 24건 인적 채점.** 실행은 사용자만 할 수 있는 임계
경로이므로, 다음 세션은 **채점을 시작/진행하는 것 자체가 작업**이다
(CUE가 대신 채점할 수 없음 — 준비는 이미 끝나 있음).

### 채점 자료 (이미 준비됨, 코퍼스 확정 이후 상태로 최신)

- `docs/NAE_GOLD_QUERY_SET_P0_5_RAW_ANSWERS_001.json` — 원본 답변
  24건(사이드카 백필 이후 재실행 결과, 이번 세션에 커밋됨).
- `docs/NAE_GOLD_QUERY_SET_P0_5_RESULT_001.md` — **주의**: 이 문서는
  아직 위 JSON 기준으로 재생성되지 않았을 수 있다(코퍼스 트랙 결정
  대기 중이라 보류했었음). 다음 세션 시작 시 먼저 이 문서가
  `RAW_ANSWERS_001.json`과 실제로 일치하는지(생성 시각·건수 대조)
  확인하고, 불일치하면 `scripts/p0_5_run_all.py` 재실행 여부를 판단할
  것.
- 채점 도구(Artifact) — `docs/NAE_GOLD_QUERY_SET_P0_5_001.md` 상단
  `scoring_tool` 링크.

### 채점 시 특히 봐야 할 것 (과거 실측 결함, 재현 여부 확인)

- `_DENOMINATION_DIRECTIVE` 교리 주입 (A3/B1에서 과거 관측,
  [[project_p0_5_a1_grounding_leak]])
- "그러나 일반적으로 신학적 관점에서"류 전환구 (`_GROUNDING_DIRECTIVE`
  §2가 막아야 함, 과거 1회 재발)
- 문자 오염(한자·키릴 등) — 과거 24건 중 6건, 재실행 결과에서 재확인
  필요
- 정직 유보 답변(근거 0건 인정)은 슬라이더 무시, 수동 PASS

### S6-2 완료 후

- **S6-3** — 외부 테스터 3~5명 섭외·안내 Artifact 공유
  (`docs/DBMA_S6_2_S6_3_READINESS_001.md` 참고, 준비 완료 상태).
  S6-4가 끝났으므로 이제 실행 가능.
- S6-2 채점 결과에 결함이 재현되면(교리 주입·오염 등) 그 처리가 S6-3
  착수보다 우선일 수 있음 — 사용자 판단.

---

## 4. 확인된 사실 (다음 세션이 재조사할 필요 없음)

- 코퍼스 기준선: Spurgeon 67종/130,401건, `docs/STATE.md` 2026-09-23
  HQ 결정 항목 참고.
- `output/bench/tsu_dataset.jsonl`의 Vol10~13 chunk 수가
  `spurgeon_119595`(09-17 백업) 대비 약 2배 증가한 정확한 원인·시점은
  **증거 없음**(C1 Task Order 070 RQ-2 "빈 구간" 참고) — 배포 차단
  사유 아니므로 조사 없이 진행 중, 필요 시 추후 재조사.
- Release 배포 체계(설치 스크립트 → GitHub Release 바이너리 자산)는
  end-to-end 검증 완료, 추가 확인 불필요.

---

## 5. 미해결/보류 항목 (참고, 급하지 않음)

- `docs/DBMA_SPURGEON_MTP_FULL_CORPUS_CHSPURGEON_TASK_ORDER_C1_001.md`,
  `scripts/spurgeon_chspurgeon_scrape.py`,
  `scripts/spurgeon_reprocess_volumes.py` — `~/DBMA`에 untracked 상태로
  존재하는 **다른 세션의 작업**(MTP 볼륨 chspurgeon.com 재스크래핑).
  이번 세션은 건드리지 않음. 코퍼스 트랙 결정(§4)과 관련 있을 수
  있으므로 다음 세션에서 사용자에게 진행 상황을 물어볼 것.

---

```
STATUS:      코퍼스 트랙 HQ 결정 확정, S6-4 완료, S6-2 착수 대기
Changed:     docs/STATE.md, BETA_LATEST_TAG.txt, docs/*.md 5건(§2-3),
             GitHub Release beta-v1.3.0-rc6
Next:        S6-2(P0-5 24건 인적 채점) 시작 → S6-3(외부 테스터)
```
