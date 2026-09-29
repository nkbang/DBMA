# CW-04 Gate 2B — Runtime Investigation 최종 기록

- **Status**: HQ 판정 완료 — Gate 2B `[HOLD — FINAL DISPOSITION PENDING]`
- **선행**: [GS-FINAL-RPV-CW04-GATE2B-CLEANROOM-REAUTH.md](GS-FINAL-RPV-CW04-GATE2B-CLEANROOM-REAUTH.md),
  CUE Independent Audit(1차, Runtime FAIL 판정 포함), CUE Root-Cause
  Investigation(2차)

## 1. 정정 — 최초 Runtime FAIL 판정 철회 (CUE Tooling Error — Retracted Finding)

**철회 대상**: CUE Independent Audit §10에서 내린 "실제 Streamlit RPV-06a/06b FAIL" 판정.

**철회 사유**: CUE가 `preview_start` 도구로 앱을 실행했을 때, 의도한
`/Users/David/DBMA-cw04-nae-app`가 아니라 **CUE 자신의 세션
워크트리**(`/Users/David/DBMA/.claude/worktrees/trusting-wilson-b6904e`
— 우연히 동일한 이름의 `.claude/launch.json`과 별도의 `output/bench`/
`data/제련완성본` 디렉터리를 갖고 있었음)에서 앱이 기동됐다. 이
워크트리에는 AD-01/AD-02 코드도, TSU dataset도, registry도 없어
모든 질문에 대해 무조건 0건이 반환됐다. 이는 **CW-04 구현의 결함이
아니라 CUE의 도구 사용 실수**였다.

```text
preview_start → CUE session worktree(trusting-wilson-b6904e)
             → AD-01/AD-02 없음, G5 dataset 없음 → 빈 corpus → 0 results
```

**[✓ HQ] 이전 Runtime FAIL 판정 철회 확정.**

## 2. 올바른 워크트리에서의 재검증 결과

`/Users/David/DBMA-cw04-nae-app`에서 Streamlit을 명시적 cwd로 직접
재기동(`streamlit run dbma_ui.py --server.port 8599`)해 재검증:

- **RPV-06a**: 정상 — 5개 candidate 반환(직접 Python 호출과 완전
  일치), fixture A는 rank 6이라 top-5 밖 → "현재 등록된 자료로는
  답할 수 없습니다"로 **정직하게 응답**. 이는 결함이 아니라 정상
  동작 — "Personal이라고 해서 강제로 rank 1로 올리지 않는다"는
  AD-02 invariant와 정확히 일치함. UI에 내부 구현 정보(corpus_type,
  score, class명) 노출 없음도 확인.
- **RPV-06b**: `core/search_cache.py`의 SQLite thread-safety 오류로
  예외 발생 — "검색 중 문제가 있었습니다" 응답.

**[✓ HQ] RPV-06a correct runtime 확정.**

## 3. 신규 발견 — search_cache.py SQLite thread-safety 결함

```text
core/search_cache.py:123
sqlite3.ProgrammingError: SQLite objects created in a thread can only
be used in that same thread. (created in thread 12969013248, used in
thread 13664940032)
```

- `d202238d`(CW-04 구현)가 전혀 건드리지 않은 파일
- AD-01/AD-02, GS, retrieval ranking과 무관
- production mutation 없음(registry mtime/hash 전 과정 불변 재확인)

**HQ 판정**: CW-04 결함으로 귀속하지 않음. 단, 실제 runtime에서
발생하는 예외이므로 **별도 pre-existing infrastructure defect**로
기록하고, 별도 corrective work로 분리 처리한다. CW-04 범위에
unrelated fix를 섞지 않는다(provenance 오염 방지).

## 4. Gate 2B 최종 상태 (HQ 확정)

```text
GS-FINAL-RPV                  [✓ HQ]
CW-04 Recovery                [✓ HQ]
Clean-Room Re-Authorization   [✓ HQ]
AD-01                         [✓ CUE]
AD-02                         [✓ CUE]
G5 Isolation                  [✓ CUE]
GS Protection                 [✓ CUE]
Regression                    [✓ CUE]
Production Mutation           [0]

RPV-06a correct runtime       [✓ CUE]
RPV-06b correct runtime       [BLOCKED — unrelated SQLite defect]

CW-04-specific defect         [NONE FOUND]

Gate 2B                       [HOLD]
Reason                        [External/pre-existing search_cache.py
                                thread-safety defect — CW-04 범위 밖]
Next                          [별도 search_cache.py corrective work
                                → 완료 후 격리 환경에서 RPV-06b만 재검증
                                → Gate 2B 최종 판정]
```

## 5. 다음 단계 (HQ 지시)

```text
CW-04
  ├── AD-01 ✓
  ├── AD-02 ✓
  ├── G5 ✓
  ├── RPV-06a ✓
  └── RPV-06b
          ↓
     search_cache.py 별도 corrective work (미착수, 별도 문서로 발행 예정)
          ↓
     완료 후 격리 환경에서 RPV-06b만 재검증
          ↓
     Gate 2B 최종 판정
```

C1에게 `search_cache.py`를 즉시 수정시키지 않는다 — 별도 작업 지시서
발행 후 착수. 현재 C1/CUE 모두 대기.
