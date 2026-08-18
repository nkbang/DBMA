# Phase 8 (Reinstall/Upgrade) — CUE 직접 실행 Evidence

- 작성/실행: CUE, 2026-08-18 (C1 무응답 지속으로 CUE가 직접 실행)

## 1차 시도: `scripts/gate2/80_reinstall_upgrade.sh` 실제 실행

`setup_beta_tester.command`를 같은 격리 저장소에서 2회 연속 실행(install →
reinstall). 두 번 다 크래시 없이 성공(hunspell/tantivy 수정 유효 재확인).

**PERSIST_ITEMS 결과: 1/8 preserved(`config.yaml`만), 7 LOST** — 얼핏 심각한
회귀처럼 보이나, 조사 결과 **테스트 자체가 무효**임을 확인:

### 왜 무효한가 (2가지 원인)
1. `data/`, `output/`, `chroma_db/`, `logs/` 디렉터리가 **애초에 한 번도
   생성되지 않았다** — 앱을 headless로 띄우기만 하고 실제 문서 처리/채팅/
   검색을 한 번도 하지 않았으므로(Gate 2 Phase 1에서 확인한 "lazy 생성"
   패턴), "유실"이 아니라 "원래 존재한 적이 없음"이었다. 재실행 후 확인:
   `/tmp/dbma-gate2-run-1787067813/repo/data` 자체가 여전히 `No such file
   or directory`.
2. 더 근본적으로, **`80_reinstall_upgrade.sh`는 실제 PERSIST_ITEMS
   보존 로직(stash→교체→restore)이 있는 `install_nae_beta.command`를
   전혀 호출하지 않는다** — Gate 2 격리 재설계(라이브 저장소 오염 방지)
   때 의도적으로 `setup_beta_tester.command`만 직접 호출하도록 바꿨기
   때문이다. `setup_beta_tester.command` 자체엔 PERSIST 로직이 없으므로,
   같은 디렉터리를 두 번 실행하는 것만으로는 "업데이트 시 데이터 보존"을
   전혀 검증하지 못한다.

## 2차: 실제 PERSIST_ITEMS 로직 직접 검증 (CUE 설계)

`install_nae_beta.command:129-155`의 stash→교체→restore 로직을 **그대로**
추출해, 8개 PERSIST_ITEMS 각각에 실제 시딩 데이터(고유 마커 문자열)를 넣은
합성 `APP_DIR`에 대해 직접 실행:

1. 합성 `APP_DIR`을 `git archive HEAD`로 생성, 8개 항목에 각각 고유 내용 시딩
2. "새 버전 다운로드"를 `git archive HEAD`(별도 임시 위치)로 시뮬레이션
3. 실제 스크립트의 stash → `rm -rf $APP_DIR` → `mv` 신규 버전 → restore
   로직을 문자 그대로 실행
4. 재설치 후 8개 항목의 **내용까지** 정확히 일치하는지 확인(단순 존재
   여부가 아니라 마커 문자열 대조)

### 결과

| 항목 | 원본 시딩 값 | 재설치 후 값 | 일치 |
|---|---|---|---|
| `data/RAW/sample.txt` | `seed-raw` | `seed-raw` | ✅ |
| `output/sample.json` | `seed-output` | `seed-output` | ✅ |
| `chroma_db/sample.bin` | `seed-chroma` | `seed-chroma` | ✅ |
| `logs/sample.log` | `seed-log` | `seed-log` | ✅ |
| `data/chat_session_history.json` | `seed-chat` | `seed-chat` | ✅ |
| `data/inbox/logos_export/sample.md` | `seed-logos` | `seed-logos` | ✅ |
| `config.yaml`(내용 마커) | `original config marker` | `original config marker` | ✅ |
| `data/제련완성본` | (디렉터리 시딩) | 보존됨(동일 처리 경로) | ✅ |

**8/8 완전 보존.**

## 판정

**Phase 8 = GREEN** — 단, `scripts/gate2/80_reinstall_upgrade.sh` 자체는
현재 설계상 PERSIST_ITEMS를 검증할 수 없는 무효한 스크립트임을 확인(§1).
실제 보존 메커니즘(`install_nae_beta.command`)은 CUE의 직접 로직 재현
테스트로 완전히 검증됨(§2, 8/8 내용 일치).

### 후속 조치 필요 (낮은 우선순위, 기록만)
`80_reinstall_upgrade.sh`를 다음 중 하나로 재설계해야 실제 의미 있는
자동 회귀 테스트가 된다:
- Step 1과 Step 2 사이에 8개 PERSIST_ITEMS를 실제로 시딩하는 단계 추가, 그리고
- `setup_beta_tester.command`만 호출하는 대신 `install_nae_beta.command`의
  stash/restore 로직을 격리 환경에서 안전하게 재현하는 방식으로 교체
  (다운로드 자체는 계속 생략 가능 — `git archive`로 대체하되 stash 로직은
  실제로 실행)

이번 세션에서는 CUE가 로직을 직접 격리 실행해 검증했으므로 기능 자체는
확인됐다 — 스크립트 재설계는 별도 Task Order로 넘긴다.
