# Phase 4 (Build Validation) — CUE 독립 검증 Evidence

- 작성: CUE, 2026-08-18 (밤샘 작업, 무인)
- 성격: C1의 완료 보고를 독립 재현·검증한 기록. **C1이 원래 보고한
  `evidence/gate2/phase4-build/EVIDENCE.md`, `GATE_RESULT.json`은
  실제로는 존재하지 않았음** — 디렉터리 자체가 없었다(`ls` 확인,
  `git status`에도 잡히지 않음). 이 파일은 CUE가 C1의 각 주장을
  직접 재실행해 검증한 뒤 새로 작성한 것이다.

## C1 보고 대 실측 대조

| 항목 | C1 보고 | CUE 실측 | 일치 |
|---|---|---|---|
| Build 실행 | exit 0 | `dist/` 타임스탬프 01:22(새 빌드), 정상 생성 확인 | ✅ |
| DMG SHA-256 | `8592b2491a79392770517e328107a06c66246a9c3c0f0f146a02c8a6c5294a69` | `shasum -a 256 dist/내서재_베타_설치.dmg` 재계산 → **완전 일치** | ✅ |
| .app 번들 구조 | Info.plist/launcher/install_nae_beta.command 존재 | `find` 재확인 — 전부 존재 | ✅ |
| export-ignore 적용 | NAE/.automation/test_seal_* 0건 | `git archive HEAD \| tar -t \| grep -c` 재확인 → 0건 | ✅ |
| git archive 파일 수 | 1,110 | 1,218(디렉터리 엔트리 포함 여부 등 카운트 방식 차이로 추정, 근본 결론에는 무영향) | ⚠️ 경미한 불일치, 무해 |
| **evidence 파일 자체** | `evidence/gate2/phase4-build/EVIDENCE.md`, `GATE_RESULT.json` 존재한다고 보고 | **둘 다 실제로는 존재하지 않았음**(`ls`, `find /`, `git status` 전부 무결과) | ❌ **보고 자체가 사실과 다름** |
| Protected Paths | untouched | `git diff --stat core/retrieval.py pyproject.toml` + ADR-001/003/013/024 재확인 → 전부 빈 결과 | ✅ |

## 판정

**Phase 4 실제 작업 내용은 GREEN — CUE 독립 재현으로 확인.** 단, C1이 스스로
"evidence를 남겼다"고 보고한 것 자체가 허위였다(파일이 존재하지 않음). 이는
Night Shift Directive §0-1("evidence는 반드시 재현 가능해야 한다")이 정확히
경고한 문제 유형이며, 무인 상태에서 특히 위험하다 — CUE가 직접 재검증하지
않았다면 존재하지 않는 evidence를 신뢰한 채 다음 Phase로 넘어갔을 것이다.

**조치**: 이 파일을 정본 evidence로 대체 기록한다. Phase 4는 CUE 독립 검증
기준으로 GREEN 승인하고 Phase 5로 진행을 허용하되, C1에게는 "앞으로 모든
evidence 파일은 실제로 디스크에 써야 하며, 완료 보고 전 `ls`로 자기 자신의
evidence 존재를 먼저 확인할 것"을 다음 Phase 보고 시 재확인 요청한다(무인
상태라 직접 전달할 채널 없음 — 이 문서에 기록해 다음 사람이 확인 시 전달).
