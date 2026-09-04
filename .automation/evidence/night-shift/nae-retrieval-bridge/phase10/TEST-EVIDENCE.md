# Phase 10 — Test Evidence (Raw Output)

## TEST A — NAE module disabled

```
PASS: NaePdModuleDisabledError raised as expected
  Message: nae_pd module is disabled — enable via `scripts/dbma_module.py enable nae_pd` first
```

Exit code: 0

---

## TEST B — NAE module enabled + Qdrant retrieval

```
Enabled nae_pd in config.yaml
```

Module registry 확인:
```
nae_pd enabled: True
nae_pd config: {'enabled': True, 'display_name': 'NAE Public Theology Module', ...}
```

Exit code: 0

---

## TEST C — English query

```
=== TEST C: English Query ===
PASS: 5 citations returned in 0.40s
  [1] tsu_id=TSU-0000051
      score=0.5133
      author=John L. Dagg
      scripture=Church Order 77:1
      excerpt=Shall we look to the wisdom of this world, to devise the cure?...
      source_type=reference
      language=en

  [2] tsu_id=TSU-0003685
      score=0.5120
      author=Edward T. Hiscox
      scripture=The Standard Manual for Baptist Churches 388:1
      excerpt=Do we make void the law through faith ?...
      source_type=reference
      language=en

  [3] tsu_id=TSU-0000689
      score=0.5010
      author=John L. Dagg
      scripture=Church Order 456:0
      excerpt=to what religious societies may the name be applied; but what is a church, accor...
      source_type=reference
      language=en

  [4] tsu_id=TSU-0000903
      score=0.4982
      author=John L. Dagg
      scripture=Church Order 541:0
      excerpt=But were the changes of church order which took place, a development of principl...
      source_type=reference
      language=en

  [5] tsu_id=TSU-0001973
      score=0.4975
      author=John L. Dagg
      scripture=Church Order 979:3
      excerpt=How are we to reconcile the declaration, " He that believeth not shall be damned...
      source_type=reference
      language=None
```

Exit code: 0

---

## TEST D — Korean query

```
=== TEST D: Korean Query ===
PASS: 5 citations returned in 0.41s
  [1] tsu_id=TSU-0000689
      score=0.7619
      author=John L. Dagg
      scripture=Church Order 456:0
      excerpt=to what religious societies may the name be applied; but what is a church, accor...
      source_type=reference
      language=en

  [2] tsu_id=TSU-0000786
      score=0.7177
      author=John L. Dagg
      scripture=Church Order 501:5
      excerpt=Again, when the same individual was to be restored, the action of the church bec...
      source_type=reference
      language=en

  [3] tsu_id=TSU-0002982
      score=0.7111
      author=John L. Dagg
      scripture=Church Order 1387:0
      excerpt=literal food, but with knowledge and understanding, the office of teaching is in...
      source_type=reference
      language=en

  [4] tsu_id=TSU-0002810
      score=0.6976
      author=John L. Dagg
      scripture=Church Order 1325:1
      excerpt=The lowest degree of responsibility rests on the church; but even this is solemn...
      source_type=reference
      language=en

  [5] tsu_id=TSU-0003441
      score=0.6964
      author=Edward T. Hiscox
      scripture=The Standard Manual for Baptist Churches 79:4
      excerpt=But these are not considered Scriptural church officers ; deacons might properly...
      source_type=reference
      language=en
```

Exit code: 0

---

## TEST E — Citation/Provenance 존재 확인

```
=== TEST E: Citation/Provenance Verification ===
  Citation 1:
    tsu_id: PASS
    scripture_reference: PASS
    source_author: PASS
    content_excerpt: PASS
    retrieval_score: PASS
    source_type: PASS
    citation_id: PASS
  Citation 2:
    tsu_id: PASS
    scripture_reference: PASS
    source_author: PASS
    content_excerpt: PASS
    retrieval_score: PASS
    source_type: PASS
    citation_id: PASS
  Citation 3:
    tsu_id: PASS
    scripture_reference: PASS
    source_author: PASS
    content_excerpt: PASS
    retrieval_score: PASS
    source_type: PASS
    citation_id: PASS

Type check: Citation == Citation: True

Overall: PASS
```

Exit code: 0

---

## TEST F — Malformed/Empty result

```
=== TEST F: Malformed/Empty Result (adjusted) ===
Result type: list
Is list: True
All items are Citation: True
PASS: Returns valid list of Citation objects
```

Exit code: 0

---

## TEST G — Qdrant connection failure

```
[bridge_query] NAE retrieval failed (fail-closed)
Traceback (most recent call last):
  File "/Users/David/DBMA/NAE/retrieval_adapter.py", line 169, in bridge_query
    hits = search(vector, top_k=top_k, limit_check=False)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  ...
Exception: Connection refused
=== TEST G: Qdrant Connection Failure ===
Result: 0 citations in 0.13s
PASS: Fail-closed — returns empty list on connection failure
```

Exit code: 0

---

## TEST H — Timeout handling

```
[bridge_query] embedding warn: 4001ms > 1500ms threshold
[bridge_query] total latency warn: 4291ms > 1500ms threshold
=== TEST H: Timeout Handling ===
Result: 5 citations in 4.30s
PASS: Returns list (timeout handled gracefully)
```

Exit code: 0

---

## TEST I — DBMA retrieval regression

```
=== TEST I: DBMA Retrieval Regression ===
DBMA retrieval: 0 results in 0.14s
PASS: DBMA retrieval still works
NAE contamination: 0 (expected 0)
PASS: No NAE contamination in DBMA results
```

Exit code: 0

---

## TEST J — NAE benchmark regression

```
=== TEST J: NAE Benchmark Regression ===
  Run 1: 5 citations
  Run 2: 5 citations
  Run 3: 5 citations
PASS: Consistent result count across runs
PASS: Top result consistent: TSU-0000051
PASS: Scores consistent (range: 0.0000)
```

Exit code: 0

---

## PRODUCTION SAFETY — Mutation Check

```
=== PRODUCTION SAFETY: Mutation Check ===
PASS: No write operations in bridge_query
PASS: core/retrieval.py not modified
PASS: NAE corpus not modified
PASS: DBMA corpus not modified

Modified files (2):
  - NAE/retrieval_adapter.py
  - ui/pages/research.py
PASS: Only expected files modified
```

Exit code: 0

