# Preflight — TSU `verse_mapping`의 book_id/chapter 조합 불일치

상태: **완전 해결(2026-07-27)** — Fix A 구현·검증 + TSU 데이터셋
전체 재빌드까지 완료, 재측정 결과 불일치 0%. Fix B(verse 범위
검증)는 낮은 우선순위 후속 과제로 남음. ADR-010 Phase 2(RAG 평가
베이스라인 측정) 실행 중 실측으로 발견.

---

## 배경

`scripts/run_rag_eval.py`(ADR-010 Phase 2)로 "Romans 8:28" 질의를
실행했더니 groundedness(생성 답변이 검색 청크에 근거했는가)가 0점이
나왔다. 원인을 추적한 결과, 검색된 유일한 청크(`TSU-ROM-...-chunk_00293`,
문서: "12 Miracles of Spiritual Growth")의 저장된 본문은 로마서와
전혀 무관한 내용(요한복음 8:58/10:30 인용)이었는데, `verse_mapping`은
`{book_id: "ROM", chapter: 8, verse_start: 58}`로 기록돼 있었다.
저장된 content를 `core.retrieval.QueryParser`로 직접 재파싱하면
JHN(요한복음) 참조만 나오고 ROM은 전혀 나오지 않는다 — 즉
`verse_mapping`이 저장된 본문으로 재현조차 안 되는 값이었다.

## 근본 원인 (코드 확정)

[`core/tsu_builder.py:298-315`](../core/tsu_builder.py#L298)에서
`verse_mapping`을 만드는 로직:

```python
verse_mapping["book_id"] = book_id  # 문서 전체 단위(파일명 기반 book_id)
...
ref, provenance = _resolve_evidence(content, book_id)  # 이 청크 안의 최고점 참조
if ref is not None:
    verse_mapping["chapter"] = ref.chapter        # 그 참조에서 뽑은 chapter
    verse_mapping["verse_start"] = ref.verse_start
```

`book_id`는 **문서 단위**(예: "이 파일은 사도행전 주석서")로 정해지고,
`chapter`/`verse_start`는 **그 청크 안에서 발견된 성경 참조 후보 중
`_score_candidate()` 최고점**에서 뽑힌다. `_score_candidate()`에
`book_id_consistent`(문서 자신의 book_id와 일치 시 +0.2) 가산점이
있지만, 그 청크 안에 문서 자신의 책과 일치하는 참조가 하나도 없으면
**무관한 책의 참조가 그대로 채택되고 문서의 book_id와 조합**된다.
결과: `{book_id: "ACT", chapter: 21}`처럼 서로 무관한 두 참조가
하나의 verse_mapping으로 합쳐지는 조합이 발생.

부수 발견: `_score_candidate()`의 `canonical_range_valid`(주석
91행)는 **chapter가 그 책의 실제 chapter 수 이내인지만 검사**하고
**verse가 그 chapter의 실제 verse 수 이내인지는 검사하지 않는다**
(로마서 8장은 39절까지인데 verse_start=58이 "유효"로 통과된 사례
확인).

## 전수 실측 결과

`scripts/audit_verse_mapping_consistency.py`(읽기 전용, 저장된
content를 QueryParser로 재파싱해 stored verse_mapping과 대조)로
`output/bench/tsu_dataset.jsonl` 전체를 검사:

```
전체 레코드:        53,231
verse_mapping 보유: 12,933 (전체의 24.3%)
일치(matched):       4,542
불일치(mismatched):  8,391 (64.88%)
  - 그중 참조 자체 미검출: 0건
```

"참조 자체 미검출 0건"이 의미하는 바: 모든 불일치 사례에서 청크
본문에 성경 참조가 발견되긴 하지만, 그게 저장된 book_id와 무관한
책을 가리킨다 — 즉 100% 위에서 서술한 book_id/chapter 조합 오류
패턴으로 설명 가능하다(별도의 "파싱 실패" 유형은 없음).

## 왜 중요한가

`core/tsu_builder.py:292-295` 주석에 명시된 대로, `core/retrieval.py`의
`_metadata_filter()`/`_scripture_alignment_score()`가 **바로 이
`verse_mapping.chapter`를 검색 필터링·랭킹에 직접 사용**한다. 즉
verse_mapping을 가진 레코드(전체의 24%)의 65%가 검색 시 잘못된
book/chapter로 필터링·정렬될 가능성이 있다 — 정량적 영향(예: Hit@K
저하폭)은 이번 조사 범위 밖이며 별도 실측 필요.

## 수정 방향

### Fix A — "모르면 비워둔다" 원칙 적용 (구현 완료, 2026-07-27)

**변경**: [`core/tsu_builder.py:309`](../core/tsu_builder.py#L309)

```python
ref, provenance = _resolve_evidence(content, book_id)
if ref is not None and ref.book_id == book_id:   # ★ 추가된 게이트
    verse_mapping["chapter"] = ref.chapter
    ...
```

청크 안에서 찾은 최고점 참조(`ref`)의 book_id가 문서 자신의 book_id와
일치할 때만 chapter/verse를 채운다. 안 맞으면 `verse_mapping`엔
`book_id`만 남고 chapter/verse는 비운다 — 무관한 참조의 chapter/verse를
문서의 book_id에 덧씌우지 않는다.

**검증**:
- 신규 재현 테스트 `tests/test_scripture_evidence_resolver.py::
  TestBuildTsuRecordsProvenance::test_cross_book_reference_does_not_
  contaminate_chapter` 추가 — 실제 코퍼스에서 발견된 패턴(문서
  book_id=2CO, 청크 본문엔 요한복음만 인용)을 합성 재현, 수정 후
  `verse_mapping == {"book_id": "2CO"}`만 남는지 확인.
- 관련 테스트 전체(`tsu`/`verse_mapping`/`scripture_evidence` 매칭)
  82건 통과, 회귀 없음.
- 실제 원본 버그 청크(`TSU-ROM-...chunk_00293`, 저장된 content 그대로)로
  `_resolve_evidence(content, "ROM")` 재실행 — `ref.book_id="JHN" != "ROM"`
  이라 chapter/verse 미채택 확인(수정 전 재현했던 버그가 실제로 해소됨).

**주의**: 이 수정은 **앞으로 새로 처리되는 문서**에만 적용된다.
기존 `output/bench/tsu_dataset.jsonl`(53,231건)은 그대로이며, Fix A
코드만으로는 기존 8,391건의 불일치가 자동으로 고쳐지지 않는다 —
아래 "재빌드"가 실행돼야 실제 검색 경로에 반영된다.

### Fix B — verse 범위 검증 (미착수)

`canonical_range_valid`에 verse 범위 검사 추가(책×chapter별 최대
verse 수 데이터 필요 — 현재 `CANONICAL_MAX_CHAPTER`만 있고 verse
단위 정경 데이터는 없음, 신규 확보 필요). Fix A로 대부분의 실질적
피해(무관한 책의 chapter/verse 채택)가 해소되므로 우선순위 낮음 —
별도 후속 과제로 분리.

### 재빌드 (완료, 2026-07-27)

`scripts/build_tsu_dataset.py`(Fix A 반영 커밋 `a0133a6` 기준) 재실행
완료:
1. 재빌드 전 `output/bench/tsu_dataset.jsonl`/`tsu_manifest.json`을
   `output/bench/backup/*_pre_fixA_20260727T014820.*`로 백업(600MB).
2. `--dry-run`으로 정상 동작(53,231건, 78개 문서, 16분 소요) 확인 후
   실제 실행 — 동일하게 53,231건 작성, manifest에
   `build_commit: a0133a6...` 기록됨(재현성 추적).
3. `scripts/audit_verse_mapping_consistency.py` 재실행(전체
   53,231건, 3분 12초) — **불일치 0%로 완전 해소**:

```
[재빌드 전] verse_mapping 보유 12,933건 → 불일치 8,391건 (64.88%)
[재빌드 후] verse_mapping 보유  4,537건 → 불일치     0건 (0.00%)
```

`chapter`를 가진 레코드 수 자체가 12,933→4,537로 줄었는데, 이는
"책이 안 맞으면 chapter를 비운다"는 Fix A 설계상 예상된 결과다 —
이전에 무관한 chapter가 잘못 채워졌던 레코드들이 이제 `book_id`만
남고, 남은 4,537건은 전부 저장된 본문으로 재현 가능한 정확한
매핑이다.

**미실행**: Hit@K 등 정식 검색 품질 벤치마크 전/후 델타는 이번
범위에서 측정하지 않음(verse_mapping 정확도 자체의 개선만 확인) —
필요 시 별도 작업으로.

## Next Steps

- [x] Fix A 구현 + 단위테스트 + 실제 버그 청크로 검증
- [x] 재빌드 전 백업
- [x] 재빌드 실행(전체 코퍼스, 사용자 승인 받음)
- [x] 재빌드 후 불일치율 재측정 — 0% 확인
- [ ] Hit@K 등 정식 검색 품질 벤치마크 전/후 델타 실측(선택, 별도 후속)
- [ ] Fix B(verse 범위 검증) 착수 여부 — 별도 후속 과제, 데이터 확보 방법 결정 필요

## 관련 산출물

- `scripts/audit_verse_mapping_consistency.py` — 읽기 전용 실측 스크립트(재실행 가능, 코드 미수정)
- `scripts/run_rag_eval.py` — 이 발견의 계기가 된 ADR-010 Phase 2 베이스라인 스크립트
