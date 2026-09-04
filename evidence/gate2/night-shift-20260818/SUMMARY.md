# Gate 2 Night Shift — 2026-08-18 아침 요약

- 작성: CUE
- 기간: 2026-08-18 00:xx(Night Shift Directive 발행) ~ 09:13(C1 무응답 지속으로 요약 작성)
- 상태: **Phase 4~6 CLOSED/GREEN, Phase 7부터 정지(C1 무응답, Phase 7 승인 대기 중 새벽부터 진전 없음)**

---

## 한눈에 보는 결과

| Phase | 상태 | 비고 |
|---|---|---|
| 4 (Build Validation) | ✅ GREEN | DMG/앱 번들/export-ignore/체크섬 전부 확인. **C1 evidence 자체는 정확했으나 CUE가 처음엔 못 찾음(자기 정정 기록됨)** |
| 5 (Clean Install) | ✅ GREEN(재검증) | **밤샘 최대 발견**: `requirements.txt`에 `tantivy` 누락 — End-User Package가 근본적으로 설치 불가능했음. 발견·수정·재검증 완료 |
| 6 (Runtime/UI Pages) | ✅ GREEN | 9개 페이지 직접 import 검증(HTTP curl 방식 폐기 — 무효였음이 실측으로 증명됨) |
| 7 (Production Isolation) | ⏸ 미시작 | 승인 대기 중 C1 무응답 |
| 8~17 | 미착수 | |

## 🔴 가장 중요한 발견 — tantivy 누락 (수정됨, commit `0db4987`)

`core/candidate_generator.py`가 `import tantivy`를 무조건 실행하는데
`requirements.txt`엔 없었다. `ui/pages/__init__.py` → `ui.pages.library` →
`core.index_orchestrator` → `core.candidate_generator` 체인 때문에, **이 상태로는
`dbma_ui.py`가 시작부터 크래시한다** — 즉 지금까지 배포된 End-User Package
설치 경로(`install_nae_beta.command`)를 따라간 신규 사용자는 전원 이 문제를
겪었을 것으로 추정된다(라이브 태그 `beta-v1.3.0-rc3`가 이 상태를 포함하는지는
별도 확인 필요 — 아래 "다음 확인 사항" 참고).

David의 개발 환경에는 tantivy가 이미 별도 설치돼 있어 Gate 1의 모든 검증
(DoD#7 포함)이 이 버그를 놓쳤다. `requirements.txt`만으로 만든 진짜 격리
venv를 처음 사용한 Gate 2 Clean Install Test에서만 드러났다 — Gate 2 전체
작업의 존재 이유를 증명한 사례.

## ⚠️ 밤새 반복된 패턴 — evidence 경로 오류

C1이 evidence를 3회 연속(Phase 4, 5, 6) `evidence/gate2/<phase>/`가 아니라
`.automation/evidence/gate2/<phase>/`(잘못된 경로)에 작성했다. 내용 자체는
Phase 4/6에서는 정확했고 Phase 5에서는 방법론 결함(HTTP 200 검증 무효)까지
겹쳐 실제로는 RED인 상태를 GREEN으로 잘못 보고했었다. CUE가 매번 독립
재현으로 잡아 정정했다.

**CUE 자신의 실수도 하나 있었다**: Phase 4 최초 감사 시 `find / -maxdepth 6`이
실제 경로 깊이(7단계)를 놓쳐 "evidence가 아예 없다"고 오판했다 — 나중에
Phase 6 감사 중 발견해 정정 기록함.

## Protected Paths / Production Mutation

밤새 전 구간에서 `core/retrieval.py`, `pyproject.toml`, ADR-001/003/013/024,
Production TSU/Qdrant, `~/내서재_베타`(라이브 경로) — 전부 무영향 확인.
`config.yaml` 근접 사고(Phase 5 이전 세션에서 CUE 본인이 겪음, 이미 별도
기록·정정됨)를 제외하면 밤새 실제 production mutation은 0건.

## 커밋 목록(오늘 밤, 시간순)

```
598fbdc Gate1 G1-G3/DoD#7 완료
6d57014 Gate2A export-ignore
af023bb Gate2 Phase1 종료
8c9ffd0 Phase1 발견 3건 수정
239ac91 Gate2 자동화 프로토콜 + Task Order
32f708f Phase4 evidence(CUE 재현, 당시 오판 포함)
aa4434a Phase5 승인 기록
1075430 Phase5 정정판 evidence(tantivy 발견 전체 기록)
1cd8604 Phase6 승인 기록
59a0308 hunspell LIBRARY_PATH 근본 수정 + Phase B FAKE_HOME 구현
68d6530 ISOLATED_INSTALL_DIR 경로 버그 수정
cac9197 Night Shift Directive
0db4987 tantivy 누락 수정 ← 오늘 밤 최대 발견
85d324f Phase6 GREEN + Phase4 자기 정정
```

## 다음 확인 사항 (Rev. Bang 판단 필요)

1. **라이브 태그(`beta-v1.3.0-rc3`)가 tantivy 버그를 포함하는지 확인 필요** —
   포함한다면 지금 이 순간에도 신규 베타 테스터의 설치가 전부 실패하고
   있다는 뜻. 태그 시점 코드를 확인해 긴급 hotfix 릴리스가 필요한지 판단.
2. Phase 7(Production Isolation)부터 재개할지, 아니면 Gate 2 범위를
   재검토할지 결정.
3. C1이 새벽 이후 왜 무응답 상태인지 확인(세션 종료/대기 등) — 재개 시
   `evidence/gate2/phase5-clean-install/PHASE6_APPROVAL.md`류 승인 기록
   패턴을 그대로 이어가면 됨.
4. Evidence 경로 오류(3연속)에 대한 C1 측 근본 원인 파악 — 필요시 Task
   Order 템플릿에 절대 경로 예시를 더 명확히 박아넣는 것 고려.

## Night Shift 자동 확인 종료

`CronDelete e6730955`로 30분 간격 확인을 종료할지 Rev. Bang 판단 대기.
