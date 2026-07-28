# DBMA-UX-001 — Stitch 프로토타입 실행 계획서

**문서 상태:** 실행 승인 요청
**작성일:** 2026-07-27
**선행 문서:** `docs/DBMA-UX-DEPLOYMENT-001.md`(제안서), `docs/DBMA-UX-DESIGN-BRIEF.md`(Stitch 전달용 Brief)
**작업 원칙:** 구현(코드) 착수 금지 — 본 Task는 프로토타입 확보와 검토까지만

---

## 1. 목표

Stitch(Google AI Design Tool)를 이용해 `DBMA-UX-DESIGN-BRIEF.md`에 정의된
P0 화면 4개(Home/Dashboard, Search, Help, Sample Library)의 시각적 프로토타입을
$0 비용으로 확보하고, HQ 승인 및 C1 Architecture Review를 거쳐 구현 단계로
넘어갈 수 있는 상태를 만든다.

---

## 2. 범위

### 포함
- Stitch에 Design Brief §5.1 프롬프트 입력 → 화면 4개 생성
- 생성 결과를 §5.2 체크리스트로 자체 검증
- HQ 검토용 결과물 정리(스크린샷/링크 취합)
- C1 Architecture Review 요청 자료 준비

### 제외 (본 Task 범위 아님)
- Streamlit 코드 구현 (`ui/pages/*` 수정) — Step 4에서만
- Core architecture 변경
- P1/P2 화면 디자인

---

## 3. 실행 절차 (체크포인트) — v2 (80/20 절차로 개정, 2026-07-28)

기존 "Stitch → 즉시 C1 Review" 절차 대신, 아래 80/20 절차로 개정한다.
Stitch만으로는 구조 초안(80%)까지만 확보되고, 디테일(20%: 계층 구조·브랜드
톤·마이크로 인터랙션·접근성)은 사람 손 보강이 필요하다는 점, 그리고 Stitch
코드 내보내기는 "그대로 사용"이 아니라 "베이스로 활용"하는 편이 안정적이라는
점을 반영한다.

| 단계 | 내용 | 산출물 | 담당 |
|---|---|---|---|
| 1 | Stitch(Standard)로 화면 구조·정보 배치 80% 초안 확보 | code.html/screen.png/DESIGN.md (zip) | HQ |
| 2 | §5.2 체크리스트 1차 검증(기술 용어, 한글 라벨 등) | 검증 결과 표 | CUE |
| 3 | Figma로 내보내 팀 리뷰, 오토레이아웃 정리, 토큰/디자인 시스템 맵핑 | Figma 파일 | HQ |
| 4 | 사람 손 20% 보강: 계층 구조, 브랜드 톤(한글 라벨 통일 등), 마이크로 인터랙션, 접근성 | 보강된 디자인 | HQ + CUE |
| 5 | HQ 최종 프로토타입 승인 (Acceptance §6.1) | 승인 기록 (본 문서에 갱신) | HQ |
| 6 | C1 Architecture Review 요청 (§6.2 기준) — 코드는 "베이스"로만 참고, `ui/pages/*` 구조에 맞춰 CUE가 재작성 | 리뷰 결과 | C1 |
| 7 | 통과 시 `DBMA-UX-002 — Implementation` Task Order 발행 | 신규 Task Order | HQ |

### 3.1 현재 진행 상황 매핑 (v2 기준)

- 1단계: 완료 — Stitch 화면 5종 확보(홈/검색/연구하기/설교 준비/온보딩).
  단, 브리프가 요청한 Help·Sample Library는 Stitch가 생성하지 않아 CUE가
  Stitch 디자인 시스템(`Theological Archive System`) 그대로 보완 제작함
  (§4 참고) — 3단계(Figma)에서 두 화면도 함께 반영 필요
- 2단계: 완료 — §5.2 체크리스트 검증 + 영어 라벨(Theology Desk, Pastoral
  Scholar, INSIGHT 등) 한글 통일 완료
- 3단계: 미착수 — Figma 반입은 HQ 액션 필요 (Google 계정과 마찬가지로 웹
  로그인 필요, CUE 브라우저 자동화로 대체 불가)
- 4단계 이후: 3단계 완료 후 진행

---

## 4. 진행 상태

- [x] Design Brief 작성 완료 (`docs/DBMA-UX-DESIGN-BRIEF.md`)
- [x] HQ 승인 기록 확인 — ChatGPT 세션에서 `DBMA-UX-DEPLOYMENT` APPROVED,
      GitHub Issue [`nkbang/DBMA#1`](https://github.com/nkbang/DBMA/issues/1)로
      공식 등록 확인됨 (2026-07-27, API 조회로 실존·open 상태 검증 완료)
- [x] Stitch 프로젝트 생성 확인 — "Pastoral Research Desk"
      (`https://stitch.withgoogle.com/projects/12870241307537301484`),
      Master Design Brief 그대로 투입된 것을 네트워크 응답으로 확인
- [x] Stitch 화면 5종 생성 완료(홈/검색/연구하기/설교 준비/온보딩) — code.html
      직접 추출 가능(zip 내보내기)한 것으로 확인, 캔버스 문제 해결됨
- [x] Help·Sample Library 2화면 보완 제작 (Stitch가 생성하지 않아 CUE가
      동일 디자인 시스템으로 제작, §4-보완 참고)
- [x] §5.2 체크리스트 검증 완료 — 영어 라벨(Theology Desk, Pastoral
      Scholar, INSIGHT, Scripture, Commentary, Drafting 등) 한글 통일 완료
- [ ] Figma 반입 → 팀 리뷰, 오토레이아웃 정리, 토큰/디자인 시스템 맵핑
      (v2 절차 3단계, HQ 액션 필요)
- [ ] 사람 손 20% 보강(계층 구조, 브랜드 톤, 마이크로 인터랙션, 접근성)
- [ ] Design Freeze
- [ ] C1 Architecture Review (Stitch 코드는 베이스 참고용, `ui/pages/*`
      구조에 맞춰 CUE가 재작성하는 것을 전제로 리뷰)
- [ ] `DBMA-UX-002` Implementation Task Order 발행

**진행률: 55%** (Stitch 5화면 확보 + Help/Library 보완 + 한글 라벨 통일
완료, Figma 반입 및 20% 디테일 보강 대기)

### 4.1 보완 산출물

- `docs/assets/ux-stitch-p0/` (예정) — 한글 라벨 통일 완료된 code.html 5종
  + CUE 보완 제작한 도움말/내 자료 화면 1종(현재 스크래치패드에 있음,
  최종 확정 시 저장소로 이동 필요)

---

## 5. HQ 액션 필요 사항

Stitch와 Figma는 모두 웹 로그인이 필요한 서비스이므로, 아래 단계는 HQ가
직접 수행해야 한다. CUE는 검증·보강·문서화를 지원한다:

1. (완료) `docs/DBMA-UX-DESIGN-BRIEF.md` §5.1 프롬프트로 Stitch 화면 생성 →
   zip(code.html/screen.png/DESIGN.md) 다운로드해 CUE에게 전달
2. (완료) CUE가 §5.2 체크리스트로 검증, 한글 라벨 통일까지 완료
3. **(다음 단계)** Stitch 결과물을 Figma로 반입 → 팀 리뷰, 오토레이아웃
   정리, 기존 DBMA 디자인 토큰과의 맵핑 진행
4. Figma 단계 완료 후 CUE와 함께 20% 디테일(계층 구조, 브랜드 톤, 마이크로
   인터랙션, 접근성) 보강
5. 승인 시 본 문서 §4에 갱신 → C1 Architecture Review로 진행

---

## 6. 리스크 및 주의사항

- Stitch 무료 tier의 생성 횟수/해상도 제한 가능 — 초과 시 대체 도구(예: Uizard,
  Figma AI) 검토 필요 (제안서 §28 상한 $20–30/month 참고, 사용 전 재검증)
- Stitch 출력 코드(있는 경우)는 참고용일 뿐, 실제 구현은 CUE가 `ui/pages/*`
  기존 구조에 맞춰 재작성 (제안서 §29 "Design과 구현 분리" 원칙)
- 기술 용어 노출 여부는 자동 검증이 어려우므로 CUE가 스크린샷을 육안으로
  검토

---

## 7. 다음 문서

승인 및 프로토타입 확보 완료 후:
- `docs/DBMA-UX-002-IMPLEMENTATION-PLAN.md` (Step 4 CUE Implementation 상세 계획)
