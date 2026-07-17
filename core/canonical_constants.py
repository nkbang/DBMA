"""core/canonical_constants.py — 성경 정경 상수 (Authority).

CANONICAL_MAX_CHAPTER를 core로 승격한 모듈. 이전에는
scripts/generate_chapter_level_gold_standard.py에 정의되어 있어,
core 로직(tsu_builder 승격 예정)이 scripts를 역방향으로 import해야 하는
의존 문제가 있었다(SPRINT20-I-C 설계, CUE-20I-C-1).

책임: CANONICAL_MAX_CHAPTER 상수 1개만 보유한다. 확장하지 않는다.
"""

# Canonical chapter counts for the books present in this corpus — fixed
# facts about the biblical text, not derived from TSU data (used to
# reject implausible chapter values SPRINT18-C's parser could not itself
# distinguish from real ones).
CANONICAL_MAX_CHAPTER: dict[str, int] = {
    "MRK": 16,
    "JHN": 21,
    "ACT": 28,
    "ROM": 16,
    "1CO": 16,
    "2CO": 13,
    "2KI": 25,
    "2CH": 36,
}
