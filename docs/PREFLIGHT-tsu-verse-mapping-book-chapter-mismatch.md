# Preflight — TSU `verse_mapping`의 book_id/chapter 조합 불일치

상태: **조사·전수 실측 완료(2026-07-27), 수정 미착수**. ADR-010 Phase 2
(RAG 평가 베이스라인 측정) 실행 중 실측으로 발견 — 코드 수정 없이
원인 확정과 규모 측정만 완료된 상태.

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

## 수정 방향 (제안, 미승인 — 설계 검토 필요)

1. **"모르면 비워둔다" 원칙 적용**: 청크 안에 문서 자신의 book_id와
   일치하는 참조가 하나도 없으면 `verse_mapping.chapter`/`verse_start`를
   아예 채우지 않는다(book_id만 유지하거나, book_id도 청크 단위로
   재검토). 현재처럼 무관한 참조의 chapter/verse를 문서의 book_id에
   덧씌우지 않는다.
2. `canonical_range_valid`에 verse 범위 검사 추가(책×chapter별 최대
   verse 수 데이터 필요 — 현재 `CANONICAL_MAX_CHAPTER`만 있고 verse
   단위 정경 데이터는 없음, 신규 확보 필요).
3. 수정 후 TSU 데이터셋 재빌드 필요(`scripts/build_tsu_dataset.py`) —
   전체 코퍼스 규모 작업, 별도 세션/승인 대상.

## Next Steps

- [ ] 수정 방향 HQ 승인
- [ ] verse 단위 정경 데이터(각 책·chapter의 최대 verse 수) 확보 방법 결정
- [ ] 수정 구현 + 단위테스트
- [ ] TSU 재빌드 전/후 Hit@K 등 검색 품질 델타 실측(회귀 방지)
- [ ] 재빌드 실행(전체 코퍼스, 별도 승인 필요)

## 관련 산출물

- `scripts/audit_verse_mapping_consistency.py` — 읽기 전용 실측 스크립트(재실행 가능, 코드 미수정)
- `scripts/run_rag_eval.py` — 이 발견의 계기가 된 ADR-010 Phase 2 베이스라인 스크립트
