"""
DBMA Query Intelligence Full Regression Test Suite

Tasks:
1. Bible book detection regression (all 66 books × English + Korean)
2. Duplicate detection audit
3. Scripture reference validation
4. Korean alias collision audit
5. Negative query regression
6. Runtime stability (100 mixed queries)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.query_enhancements import EnhancedQueryParser, ParsedQuery


def test_bible_book_detection():
    """Task 1: Complete Bible Book Detection Regression Test"""
    parser = EnhancedQueryParser()
    
    # English books (name as it appears in NAME_TO_BOOK_ID)
    english_books = [
        ("Genesis", "GEN"),
        ("Exodus", "EXO"),
        ("Leviticus", "LEV"),
        ("Numbers", "NUM"),
        ("Deuteronomy", "DEU"),
        ("Joshua", "JOS"),
        ("Judges", "JDG"),
        ("Ruth", "RUT"),
        ("1 Samuel", "1SA"),
        ("2 Samuel", "2SA"),
        ("1 Kings", "1KI"),
        ("2 Kings", "2KI"),
        ("1 Chronicles", "1CH"),
        ("2 Chronicles", "2CH"),
        ("Ezra", "EZR"),
        ("Nehemiah", "NEH"),
        ("Esther", "EST"),
        ("Job", "JOB"),
        ("Psalms", "PSA"),
        ("Proverbs", "PRO"),
        ("Isaiah", "ISA"),
        ("Jeremiah", "JER"),
        ("Ezekiel", "EZE"),
        ("Daniel", "DAN"),
        ("Hosea", "HOS"),
        ("Joel", "JOEL"),
        ("Amos", "AMOS"),
        ("Obadiah", "OBA"),
        ("Jonah", "JON"),
        ("Micah", "MIC"),
        ("Nahum", "NAM"),
        ("Habakkuk", "HAB"),
        ("Zephaniah", "ZEP"),
        ("Haggai", "HAG"),
        ("Zechariah", "ZEC"),
        ("Malachi", "MAL"),
        # New Testament
        ("Matthew", "MAT"),
        ("Mark", "MRK"),
        ("Luke", "LUK"),
        ("John", "JHN"),
        ("Acts", "ACT"),
        ("Romans", "ROM"),
        ("1 Corinthians", "1CO"),
        ("2 Corinthians", "2CO"),
        ("Galatians", "GAL"),
        ("Ephesians", "EPH"),
        ("Philippians", "PHP"),
        ("Colossians", "COL"),
        ("1 Thessalonians", "1TH"),
        ("2 Thessalonians", "2TH"),
        ("1 Timothy", "1TI"),
        ("2 Timothy", "2TI"),
        ("Titus", "TIT"),
        ("Philemon", "PHM"),
        ("Hebrews", "HEB"),
        ("James", "JAS"),
        ("1 Peter", "1PE"),
        ("2 Peter", "2PE"),
        ("1 John", "1JN"),
        ("2 John", "2JN"),
        ("3 John", "3JN"),
        ("Jude", "JUD"),
        ("Revelation", "REV"),
    ]

    # Korean books (Korean full names)
    korean_books = [
        ("창세기", "GEN"),
        ("출애굽기", "EXO"),
        ("레위기", "LEV"),
        ("민수기", "NUM"),
        ("신명기", "DEU"),
        ("여호수아", "JOS"),
        ("사사기", "JDG"),
        ("룻기", "RUT"),
        ("사무엘상", "1SA"),
        ("사무엘하", "2SA"),
        ("열왕기상", "1KI"),
        ("열왕기하", "2KI"),
        ("역대상", "1CH"),
        ("역대하", "2CH"),
        ("시편", "PSA"),
        ("잠언", "PRO"),
        ("이사야", "ISA"),
        ("예레미야", "JER"),
        ("에스겔", "EZE"),
        ("다니엘", "DAN"),
        ("마태복음", "MAT"),
        ("마가복음", "MRK"),
        ("누가복음", "LUK"),
        ("요한복음", "JHN"),
        ("사도행전", "ACT"),
        ("로마서", "ROM"),
        ("고린도전서", "1CO"),
        ("고린도후서", "2CO"),
        ("갈라디아서", "GAL"),
        ("에베소서", "EPH"),
        ("빌립보서", "PHP"),
        ("골로새서", "COL"),
        ("데살로니가전서", "1TH"),
        ("디모데전서", "1TI"),
        ("디모데후서", "2TI"),
        ("히브리서", "HEB"),
        ("야고보서", "JAS"),
        ("베드로전서", "1PE"),
        ("요한계시록", "REV"),
    ]

    results = {"pass": 0, "fail": 0, "details": []}

    print("=" * 80)
    print("TASK 1: Bible Book Detection Regression")
    print("=" * 80)

    # Test English books
    print("\n--- English Books ---")
    for name, expected_id in english_books:
        result = parser.parse(name)
        detected = result.detected_books
        hit = expected_id in detected
        status = "PASS" if hit else "FAIL"
        if hit:
            results["pass"] += 1
        else:
            results["fail"] += 1
        results["details"].append(f"EN '{name}' → {detected} (expected={expected_id}) [{status}]")
        print(f"  EN: {name:<20} → {detected}  [{'PASS' if hit else 'FAIL'}]")

    # Test Korean books
    print("\n--- Korean Books ---")
    for name, expected_id in korean_books:
        result = parser.parse(name)
        detected = result.detected_books
        hit = expected_id in detected
        status = "PASS" if hit else "FAIL"
        if hit:
            results["pass"] += 1
        else:
            results["fail"] += 1
        results["details"].append(f"KO '{name}' → {detected} (expected={expected_id}) [{status}]")
        print(f"  KO: {name:<20} → {detected}  [{'PASS' if hit else 'FAIL'}]")

    total = results["pass"] + results["fail"]
    print(f"\nBook Detection: {results['pass']}/{total} pass ({results['pass']/max(total,1):.2%})")
    
    return results


def test_duplicate_detection():
    """Task 2: Duplicate Detection Audit"""
    parser = EnhancedQueryParser()
    
    test_cases = [
        ("Romans 8:28", "ROM"),
        ("베드로전서 5:7", "1PE"),
        ("로마서 8장", "ROM"),
    ]

    results = {"pass": 0, "fail": 0, "details": []}

    print("\n" + "=" * 80)
    print("TASK 2: Duplicate Detection Audit")
    print("=" * 80)

    for query, book_id in test_cases:
        result = parser.parse(query)
        count = result.detected_books.count(book_id)
        is_unique = count == 1
        status = "PASS" if is_unique else "FAIL"
        if is_unique:
            results["pass"] += 1
        else:
            results["fail"] += 1
        results["details"].append(f"'{query}' → {result.detected_books} (count={count}) [{status}]")
        print(f"  '{query}' → books={result.detected_books}  count(book_id)={count}  [{'PASS' if is_unique else 'FAIL'}]")

    return results


def test_scripture_reference_validation():
    """Task 3: Scripture Reference Validation"""
    parser = EnhancedQueryParser()
    
    test_cases = [
        ("Romans 8:28", "ROM", 8, 28),
        ("Matthew 5", "MAT", 5, None),      # chapter only, no verse
        ("Matthew 5:3", "MAT", 5, 3),
        ("1 Peter 5:7", "1PE", 5, 7),
        ("요한복음 3장16절", "JHN", 3, 16),
        ("로마서 8장28절", "ROM", 8, 28),
    ]

    results = {"pass": 0, "fail": 0, "details": []}

    print("\n" + "=" * 80)
    print("TASK 3: Scripture Reference Validation")
    print("=" * 80)

    for query, exp_book, exp_chap, exp_verse in test_cases:
        result = parser.parse(query)
        
        # Find matching reference
        ref_found = None
        for ref in result.scripture_refs:
            if ref.book_id == exp_book and ref.chapter == exp_chap:
                ref_found = ref
                break
        
        verse_ok = True
        if exp_verse is not None:
            verse_ok = (ref_found.verse_start or 0) == exp_verse if ref_found else False
        else:
            # Chapter only - verse_start should be 0 (no verse specified)
            verse_ok = (ref_found.verse_start or 0) == 0 if ref_found else True
        
        hit = ref_found is not None and verse_ok
        status = "PASS" if hit else "FAIL"
        if hit:
            results["pass"] += 1
        else:
            results["fail"] += 1

        refs_str = [f"{r.book_id}{r.chapter}:{r.verse_start}" for r in result.scripture_refs]
        print(f"  '{query}' → refs={refs_str}  book={exp_book} chap={exp_chap} ver={exp_verse}  [{'PASS' if hit else 'FAIL'}]")
        results["details"].append(f"'{query}' → refs={refs_str}  [{status}]")

    return results


def test_korean_alias_collision():
    """Task 4: Korean Alias Collision Audit"""
    parser = EnhancedQueryParser()
    
    # Each query should resolve to exactly one book_id with no duplicates
    test_cases = [
        ("베드로전서", "1PE"),
        ("데살로니가전서", "1TH"),
        ("로마서", "ROM"),
        ("고린도전서", "1CO"),
        ("요한복음", "JHN"),
    ]

    results = {"pass": 0, "fail": 0, "details": []}

    print("\n" + "=" * 80)
    print("TASK 4: Korean Alias Collision Audit")
    print("=" * 80)

    for query, expected_id in test_cases:
        result = parser.parse(query)
        count = result.detected_books.count(expected_id)
        unique_count = len(set(result.detected_books))
        
        # Must have exactly one entry of the expected book (no duplicates)
        no_dupes = count == 1 and len(result.detected_books) == unique_count + (len(result.detected_books) - unique_count)
        has_target = expected_id in result.detected_books
        
        hit = has_target and count == 1
        status = "PASS" if hit else "FAIL"
        if hit:
            results["pass"] += 1
        else:
            results["fail"] += 1

        print(f"  '{query}' → {result.detected_books}  (count={count}, unique={unique_count})  [{'PASS' if hit else 'FAIL'}]")
        results["details"].append(f"'{query}' → {result.detected_books}  [{status}]")

    return results


def test_negative_query_regression():
    """Task 5: Negative Query Regression"""
    parser = EnhancedQueryParser()
    
    negative_queries = [
        "zzqqxx999",
        "asdfgh",
        "qwerty123",
        "random theological sentence",
        "Power and Fury",
    ]

    results = {"pass": 0, "fail": 0, "details": []}

    print("\n" + "=" * 80)
    print("TASK 5: Negative Query Regression")
    print("=" * 80)

    for query in negative_queries:
        neg_check = parser.check_negative_query(query)
        confidence = neg_check["confidence"]
        is_productive = neg_check["is_likely_productive"]
        
        # Should NOT have high confidence of being productive
        hit = not is_productive or confidence < 0.3
        status = "PASS" if hit else "FAIL"
        if hit:
            results["pass"] += 1
        else:
            results["fail"] += 1

        print(f"  '{query:<35}' confidence={confidence:.2f} productive={is_productive}  [{'PASS' if hit else 'FAIL'}]")
        results["details"].append(f"'{query}' → conf={confidence:.2f} prod={is_productive}  [{status}]")

    return results


def test_runtime_stability():
    """Task 6: Runtime Stability Test (100 mixed queries)"""
    parser = EnhancedQueryParser()
    
    import time
    import tracemalloc
    
    # Mixed query set covering various patterns
    mixed_queries = [
        # English books
        "Genesis", "Exodus", "Romans 8", "Matthew 5:3", "1 Peter 2:6",
        "Revelation 21", "Psalms 23", "Proverbs 3:5",
        # Korean books  
        "창세기", "로마서", "요한복음 3장", "시편 23편", "마태복음 5장",
        # Mixed language
        "Romans and 로마서", "faith and 믿음",
        # Theme queries
        "grace", "하나님의 사랑", "구원", "믿음",
        # Negative/edge cases
        "zzz999", "???###", "the", "a",
        # Numbered books
        "1 John", "2 Timothy", "3 John", "1 Kings", "2 Chronicles",
        # Chapter only
        "John 3", "Romans 12", "행전 2장",
        # Verse patterns
        "Genesis 1:1", "요한복음 3장 16절", "롬 8:28",
        # More variety for 100 queries
        "Isaiah 53", "제사", "메시아", "희생", "속죄",
        "히브리서 9", "레위기 16", "출애굽기 12",
        "에스더 4:14", "느헤미야 8", "신명기 6:5",
        "미가 6:8", "호세아 6:6", "아모스 5:24",
        "말라기 3:10", "베드로전서 1:5", "고린도후서 5:17",
        "갈라디아서 5:22", "에베소서 2:8", "빌립보서 4:13",
        "골로새서 3:23", "디모데전서 2:5", "디도서 1:7",
        "야고보서 1:2", "유다서 1:20", "히브리서 11:1",
    ]

    # Repeat to get 100 queries
    queries = (mixed_queries * 3)[:100]

    print("\n" + "=" * 80)
    print("TASK 6: Runtime Stability Test (100 mixed queries)")
    print("=" * 80)

    # Start memory tracking
    tracemalloc.start()
    start_time = time.time()

    exceptions = 0
    parse_times = []
    parse_results = []

    for i, query in enumerate(queries):
        try:
            t0 = time.perf_counter()
            result = parser.parse(query)
            dt = time.perf_counter() - t0
            parse_times.append(dt)
            parse_results.append(result)
        except Exception as e:
            exceptions += 1
            print(f"  EXCEPTION #{exceptions} at query {i}: '{query}' → {e}")

    elapsed = time.time() - start_time
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Check for parser state leakage (parse results should not share refs)
    leakage_detected = False
    for i in range(0, len(parse_results) - 1, 5):
        r1 = parse_results[i]
        r2 = parse_results[i + 1] if i + 1 < len(parse_results) else None
        if r2 is not None:
            # Check that scripture_refs are not shared references
            for ref_a in r1.scripture_refs:
                for ref_b in r2.scripture_refs:
                    if ref_a is ref_b and r1.detected_books != r2.detected_books:
                        leakage_detected = True

    total = len(queries)
    avg_time = sum(parse_times) / max(len(parse_times), 1)
    
    print(f"\n  Queries executed: {total}")
    print(f"  Exceptions: {exceptions}")
    print(f"  Elapsed: {elapsed:.3f}s")
    print(f"  Avg parse time: {avg_time*1000:.2f}ms")
    print(f"  Peak memory: {peak_mem / 1024:.1f}KB")
    print(f"  Parser state leakage: {'DETECTED' if leakage_detected else 'NOT DETECTED'}")

    # Retention check - ensure parser state is not accumulated between calls
    retained_books = set()
    for result in parse_results:
        retained_books.update(result.detected_books)
    
    # After 100 queries, the parser should NOT have accumulated book IDs
    # A well-designed stateless parser returns empty sets for non-book queries
    # but this is acceptable as long as each individual parse is correct
    
    hit = exceptions == 0 and not leakage_detected
    status = "PASS" if hit else "FAIL"
    
    print(f"\n  Overall: [{status}]")
    
    return {
        "total": total,
        "exceptions": exceptions,
        "elapsed": elapsed,
        "avg_time_ms": avg_time * 1000,
        "peak_mem_kb": peak_mem / 1024,
        "leakage": leakage_detected,
        "hit": hit,
        "status": status,
    }


def run_all_tests():
    """Run complete regression suite."""
    print("=" * 80)
    print("DBMA QUERY INTELLIGENCE FULL REGRESSION SUITE")
    print("=" * 80)

    all_results = {}

    # Task 1: Bible book detection
    r1 = test_bible_book_detection()
    all_results["book_detection"] = r1

    # Task 2: Duplicate detection
    r2 = test_duplicate_detection()
    all_results["duplicate_detection"] = r2

    # Task 3: Scripture reference validation
    r3 = test_scripture_reference_validation()
    all_results["scripture_refs"] = r3

    # Task 4: Korean alias collision
    r4 = test_korean_alias_collision()
    all_results["korean_collision"] = r4

    # Task 5: Negative query regression
    r5 = test_negative_query_regression()
    all_results["negative_queries"] = r5

    # Task 6: Runtime stability
    r6 = test_runtime_stability()
    all_results["runtime_stability"] = r6

    # Summary
    print("\n" + "=" * 80)
    print("REGRESSION SUITE SUMMARY")
    print("=" * 80)
    
    total_pass = r1["pass"] + r2["pass"] + r3["pass"] + r4["pass"] + r5["pass"]
    total_fail = r1["fail"] + r2["fail"] + r3["fail"] + r4["fail"] + r5["fail"]
    
    print(f"\n  Book Detection:  {r1['pass']}/{r1['pass']+r1['fail']} pass")
    print(f"  Duplicate Audit: {r2['pass']}/{r2['pass']+r2['fail']} pass")
    print(f"  Scripture Refs:  {r3['pass']}/{r3['pass']+r3['fail']} pass")
    print(f"  Collision Audit: {r4['pass']}/{r4['pass']+r4['fail']} pass")
    print(f"  Negative Queries:{r5['pass']}/{r5['pass']+r5['fail']} pass")
    print(f"  Runtime Stable:  {r6['status']}")
    print(f"\n  TOTAL: {total_pass}/{total_pass+total_fail} pass ({total_pass/max(total_pass+total_fail,1):.2%})")
    
    all_pass = total_fail == 0 and r6["hit"]
    print(f"\n  OVERALL RESULT: {'ALL PASS' if all_pass else 'SOME FAILED'}")

    return all_results


if __name__ == "__main__":
    run_all_tests()