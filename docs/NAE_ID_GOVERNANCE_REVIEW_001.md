# NAE ID Governance Review 001

**Project:** NAE-ID-GOVERNANCE-001
**Date:** 2026-08-02
**Nature:** ID 정책 설계 + 기존 Pilot ID 평가 + Migration 규칙 정의 — **전체 Registry Migration 아님**
**Git Commit:** 미수행 — 사용자 승인 대기

---

## 1. Existing ID Audit 결과

실제 `resources/theological_sources/authority/*.yaml` 실측(Authority
Registry Build-001 산출물, 3 author/3 work/4 edition/8 volume/10 source):

- **Author**: `dagg_john_l`/`hiscox_edward_t`(소문자 snake_case,
  surname_given_middleinitial) vs `FULLER-ANDREW-001`(대문자, 하이픈,
  숫자 순번 접미) — 3건 중 1건이 이질적.
- **Work/Edition/Volume/Source**: **10건 전부** 대문자-하이픈 표기이며,
  Dagg/Hiscox 계열과 Fuller 계열이 서로 다른 하위 패턴을 사용(예:
  Edition에서 Dagg는 `{work_id}-{year}`, Fuller는
  `{work_id}-ED-{place}-{year}`).
- Volume ID는 edition_id가 아니라 work_id를 접두로 사용해, Edition이
  2개인 Fuller에서 ID 문자열만으로는 소속 Edition을 알 수 없음(자기
  서술성 부족 — 신규 발견).
- v1.2 레거시 source_id(`SLBC1689` 등)는 완전히 다른 제3의 패턴(접두어
  없는 영숫자 코드)으로, 이번 감사·정책 대상에서 의도적으로 제외.

상세 표는 [`NAE_ID_GOVERNANCE_v1.md`](NAE_ID_GOVERNANCE_v1.md) §1 참고.

---

## 2. Entity별 Canonical ID Rule

| Entity | Rule | 예 |
|---|---|---|
| Author | `{surname}_{given}[_{middle_initial}]` | `dagg_john_l`, `fuller_andrew` |
| Work | `{author_id}_{title_slug}` | `fuller_andrew_complete_works` |
| Edition | `{work_id}_{year}[_{place_slug}]` | `fuller_andrew_complete_works_1824_newhaven` |
| Volume | `{edition_id}_v{NN}` | `fuller_andrew_complete_works_1824_newhaven_v02` |
| Source | `{volume_id or edition_id}_{scan_suffix}` | `..._v02_s01` |

**Author ID 순서(surname 우선)를 명령서 예시(given-name 우선)와 다르게
결정**했다 — 기존 실 데이터 2/3건과 기존 문서화된 규칙이 이미 surname
우선이라, 이 쪽을 채택해야 마이그레이션 대상이 최소화된다. 근거 상세는
[`NAE_ID_GOVERNANCE_v1.md`](NAE_ID_GOVERNANCE_v1.md) §2.1.

Volume ID는 기존(work_id 접두)에서 canonical(edition_id 접두)로
개선 — Edition이 여러 개인 Work에서도 ID만으로 소속 Edition을 알 수
있게 자기서술성을 높였다(§1의 신규 발견에 대한 직접 대응).

---

## 3. Collision Policy

| 충돌 유형 | 처리 |
|---|---|
| 동명이인 Author | 1차: 출생연도 접미, 2차: 숫자 suffix + notes 근거 기록 |
| 동일 제목 Work | 사람이 먼저 진짜 다른 저작인지 확인 → RAW 근거 기반 구분자(임의 순번 지양) |
| 동일 Edition(같은 publisher+year+title) | 기본은 Duplicate(Source scan_suffix만 증가), 실물 대조로 인쇄판 차이 확인될 때만 신규 Edition |

세 유형 모두 **최종 판단은 사람**(자동 규칙으로 확정하지 않음 —
GOVERNANCE §1 Philosophy #3 자동 병합 금지 원칙과 일관). 상세는
[`NAE_ID_GOVERNANCE_v1.md`](NAE_ID_GOVERNANCE_v1.md) §3.

---

## 4. Pilot ID 호환성 평가

| 판정 | 대상 |
|---|---|
| **유지 가능** | `dagg_john_l`, `hiscox_edward_t`(2건) |
| **변경 필요** | 나머지 26건 전부(Author 1 + Work 3 + Edition 4 + Volume 8 + Source 10) |
| **Alias 처리** | 변경 대상 26건 전부 — 실제 rename 시 `legacy_id` 필드로 구 ID 보존(완전 삭제 아님) |

**원칙 준수 확인**: 이번 평가는 판정만 내렸을 뿐, 어떤 Registry YAML
파일도 실제로 수정하지 않았다(git diff 없음 — §7에서 재확인). 기존
Registry 삭제 금지 원칙도 준수(§4 표는 "변경 필요"이지 "삭제"가 아님).

---

## 5. Migration Policy

- **원칙**: RAW/기존 Registry 미변경, `legacy_id` 보존, 원자적 rename
  (ID 필드 + 모든 FK 참조를 같은 커밋에서 함께 변경), 실행 전/후
  Reference Integrity 재검증(Registry Build-001 §Phase4 스크립트 재사용).
- **변환 매핑표**: 26개 entity 전체에 대한 Old→New 매핑을
  [`NAE_ID_GOVERNANCE_v1.md`](NAE_ID_GOVERNANCE_v1.md) §6.2에 기록 —
  **검토용 계획이며 이번 작업에서 실행하지 않았다.**
- **신규 자료 적용**: 다음 Pilot(Baptist Missionary Magazine 등)부터는
  처음부터 이 규칙으로 ID 생성 — 이중 변환 작업 회피.

---

## 6. ADR 결정

**신규 [ADR-017](architecture/ADR-017-NAE-ID-Governance-Standard.md) 채택**
(ADR-016 개정 아님). 근거: Entity 모델(ADR-016)과 ID 표기 규칙(이번
결정)은 층위가 다르고, "ADR 소급 수정 금지" 관례(GOVERNANCE §7.5에서
이미 확립)를 일관되게 적용. 상세는
[`NAE_ID_GOVERNANCE_v1.md`](NAE_ID_GOVERNANCE_v1.md) §5, ADR-017 §3.4.

---

## 7. Remaining Risks

| # | 리스크 | 설명 | 우선순위 |
|---|---|---|---|
| 1 | 실제 rename 미실행 | 정책만 확정 — Registry는 여전히 불일치 상태로 남아 있음(의도된 결과, 실행은 별도 승인) | 중간 — 별도 Migration 작업 필요 |
| 2 | 정기간행물 ID 확장 규칙 미정 | Baptist Missionary Magazine류(volume+issue)의 ID 패턴은 이번 문서 범위 밖 | 높음 — 다음 Pilot 착수 전 결정 필요 |
| 3 | Author 통합 미해결 | `fuller_andrew`(신규 canonical)와 기존 `AF1815` entry(baptist manifest)가 여전히 별도 — ID 규칙과 별개로 저자 통합 결정 필요 | 중간 |
| 4 | Edition collision 실사례 부재 | 동일 Work·동일 연도·다른 출판사 충돌 규칙(§3)은 아직 실제 사례로 검증되지 않음 | 낮음 — 발생 시 규칙 재검토 |
| 5 | `scripts/authority_validator.py` 미구현 | 이번 ID 규칙을 실제로 강제(포맷 검증)할 도구가 아직 코드로 존재하지 않음(Registry Design v1 §Phase5, 설계만) | 중간 |

---

## 완료 조건 답변

1. **Author ID 규칙 확정 여부** — 확정(`{surname}_{given}[_{middle_initial}]`, surname 우선).
2. **Work ID 규칙 확정 여부** — 확정(`{author_id}_{title_slug}`).
3. **Edition ID 규칙 확정 여부** — 확정(`{work_id}_{year}[_{place_slug}]`).
4. **Volume ID 규칙 확정 여부** — 확정(`{edition_id}_v{NN}`, edition_id 접두로 개선).
5. **Source ID 규칙 확정 여부** — 확정(`{volume_id 또는 edition_id}_{scan_suffix}`, v1.2 레거시와 별개 네임스페이스 유지).
6. **기존 Pilot ID 처리 방법** — 2건 유지(`dagg_john_l`, `hiscox_edward_t`), 26건 변경 필요 + `legacy_id` alias 보존(§4).
7. **전체 Metadata Migration 준비 여부** — **아니오, 아직 아니다.** ID 정책은 확정됐으나 (a) 실제 rename 미실행, (b) 정기간행물 ID 규칙 미정, (c) Registry Validation Tool 미구현 — 세 가지가 남아 있다.

---

## 로드맵 갱신

```
Architecture Revision       ✅
Schema v2.1.0               ✅
Validator                   ✅
Authority Registry           ✅
ID Governance                ✅ (이번 작업 — 정책 확정까지, 실제 rename 아님)

Baptist Missionary Pilot     NEXT (정기간행물 ID 규칙도 함께 확정)
ID Migration(legacy_id 보존)  NEXT (정책 실행, 별도 승인)
Authority Registry Validation Tool   NEXT
Small Metadata Migration      FUTURE
Full Corpus Migration          FUTURE
TSU Integration                 FUTURE
```

---

*Authority Registry 전체 변경, 기존 author_id/work_id rename, Pilot
YAML 수정, Corpus 수정, RAW 변경, Metadata Migration, TSU/Embedding
생성, Retrieval 변경, `scripts/source_validator.py` 변경 — 전부
수행하지 않음. Git Commit은 사용자 승인 후에만 수행한다.*
