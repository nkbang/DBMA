# DBMA Brand Freeze Rules (NAE)

Status: FROZEN — Human HQ 승인 없이 변경 금지 (근거: `docs/governance/DBMA-BRAND-GOV-001.md`)

## 확정 브랜드

- 한국어 사용자-facing 브랜드명: **내서재**
- 영문 사용자-facing 브랜드명: **NAE** (반드시 대문자)
- 내부 엔지니어링/프로젝트 식별자: **DBMA** (계속 유지, 폐기 아님)

## 절대 금지

- `DBMA` → `NAE` 전역 코드 rename 금지 (repo, 패키지명, `dbma_ui.py`, `core/`, config key, DB 경로, Git history 등)
- `Nae`, `nae`, `N.A.E.`, `NAE AI`, `NAE Ministry`, `NAE Bible` 등 임의 파생 브랜드명 생성 금지
- `NAE`의 acronym expansion(예: Notes·Archive·Exploration)을 공식 확정처럼 문서/UI에 기재 금지 — 아직 미확정
- 브랜드 관련 파일/문서/UI 수정 요청이 있어도, 이미 동결된 이름을 다른 이름으로 바꾸는 작업으로 해석 금지

## 적용 기준

- 사용자-facing 영역(UI, README, About/Help, 문서, export, 알림 등): "내서재" 또는 "NAE" 사용
- 내부 코드/설정/저장소/Git 관련: "DBMA" 그대로 유지
- 브랜드 변경이 필요하다고 판단되면 임의 실행하지 말고 사용자에게 보고 후 승인 대기
