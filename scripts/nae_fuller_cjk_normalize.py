"""NAE Fuller F2 — post-processing CJK normalization for TSU `claim` fields.

WHY: `my-theology-bot-v2` (Qwen-family) code-switches into Chinese/Japanese
under GPU load, leaving Han characters in the Korean `claim` text
(~10% of Vol.01, ~8% of Vol.02). This is a MODEL-OUTPUT defect, not source
OCR. This script is a *post-processing* step — it does NOT touch
`NAE/pipeline/tsu/builder.py` or `builder_version` (stays 3.0.0), and does
NOT re-run extraction by default.

WHAT:
  1. For each maximal Han run in `claim`, replace it ONLY if the whole run
     is an exact key in `_HANJA_KO` (curated Sino-Korean readings). Partial
     matches are never guessed — safer to flag than mis-translate.
  2. Records fully cleared of Han  -> `cjk_status = "normalized"`.
     Records with Han left over    -> `cjk_status = "residual"` + `needs_review`.
     Records that never had Han     -> untouched (no new keys).
  3. Original text preserved in `claim_raw` (only added when a change is made).
  4. Per-volume `cjk_normalize_report.json` written next to tsu.json.
  5. `tsu_report.json` gets a top-level `cjk_normalize_version` key
     (NOT `builder_version`).

Idempotent: rows already `cjk_status=="normalized"` are skipped; `residual`
rows are re-attempted (map may have grown).

Guard: refuses a volume whose `tsu_report.json` has `partial: true`
(F2 may still be writing it) unless `--allow-partial`.

Usage:
  python -m scripts.nae_fuller_cjk_normalize --identifier Fuller_Complete_Works_Vol01           # dry-run
  python -m scripts.nae_fuller_cjk_normalize --identifier Fuller_Complete_Works_Vol01 --apply
  python -m scripts.nae_fuller_cjk_normalize --all --apply
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TSU_ROOT = REPO_ROOT / "NAE" / "corpus" / "tsu"
NORMALIZE_VERSION = "1.0.0"

# Maximal Han run  ->  Korean. Applied only on EXACT whole-run match.
# Curated from the observed Vol.01+Vol.02 inventory (clean Sino-Korean /
# shinjitai readings only; ambiguous fragments like 人的 / 者的 / 之X are
# deliberately absent so they fall through to "residual").
_HANJA_KO: dict[str, str] = {
    "人": "사람", "徳": "덕", "德": "덕", "義": "의", "者": "자",
    "真正": "진정", "真的": "참", "本当": "참으로", "眞正": "진정",
    "同時": "동시", "同": "같음", "伟大": "위대", "偉大": "위대",
    "益": "유익", "普遍": "보편", "普及": "보급", "傲慢": "오만",
    "拒絶": "거절", "拒絕": "거절", "盲目": "맹목", "盲人": "맹인",
    "自身": "자신", "自己": "자기", "頑固": "완고", "固執": "고집",
    "未": "아직", "善": "선", "善行": "선행", "善意": "선의",
    "行": "행함", "行为": "행위", "行爲": "행위", "真理": "진리",
    "呼唤": "부름", "呼": "부름", "优秀": "우수", "優秀": "우수",
    "否認": "부인", "否认": "부인", "設計": "설계", "计劃": "계획",
    "計劃": "계획", "計画": "계획", "至高": "지고", "至上": "지상",
    "至": "지극히", "誰": "누구", "严厉": "엄격", "嚴厲": "엄격",
    "严厳": "엄격", "嚴嚴": "엄격", "严": "엄격", "如此": "이와 같이",
    "罪": "죄", "仁慈": "인자", "仁惠": "인혜", "仁": "인",
    "幸福": "행복", "幸": "복", "聖書": "성경", "聖経": "성경",
    "相信": "믿음", "荣耀": "영광", "榮耀": "영광", "荣誉": "영예",
    "榮譽": "영예", "嘲笑": "조소", "警告": "경고", "顯現": "나타남",
    "显現": "나타남", "显现": "나타남", "自然": "자연", "宗教": "종교",
    "宗": "종교", "更加": "더욱", "屈服": "굴복", "憎": "미움",
    "描述": "서술", "慷慨": "관대", "理": "이치", "柔軟性": "유연성",
    "柔軟": "유연", "作者": "저자", "著者": "저자", "神": "신",
    "道": "도", "世間": "세상", "世俗": "세속", "命": "생명",
    "享受": "누림", "誠實": "성실", "诚實": "성실", "誠心": "진심",
    "誠": "정성", "仕事": "일", "磐石": "반석", "経験": "경험",
    "經驗": "경험", "實際": "실제", "实际": "실제", "実際": "실제",
    "惡": "악", "悪": "악", "意见": "의견", "意識": "의식",
    "意识": "의식", "変化": "변화", "变化": "변화", "回答": "답",
    "省略": "생략", "悔改": "회개", "改悛": "회개", "悔": "뉘우침",
    "放下": "내려놓음", "適切": "적절", "适切": "적절", "忍耐": "인내",
    "品質": "품질", "遠": "멂", "远": "멂", "天堂": "천국",
    "醜陋": "추함", "肉體": "육체", "身體": "몸", "体": "몸",
    "矛盾": "모순", "過去": "과거", "过去": "과거", "概念": "개념",
    "停止": "그침", "停滞": "정체", "欺": "속임", "信念": "신념",
    "事項": "사항", "事业": "사업", "事業": "사업", "疑問": "의문",
    "永遠": "영원", "永生": "영생", "洗净": "씻음", "洗淨": "씻음",
    "功": "공로", "功徳": "공덕", "功德": "공덕", "作用": "작용",
    "感": "느낌", "寻求": "구함", "人们": "사람들", "人類": "인류",
    "人类": "인류", "你们": "너희", "子供": "자녀", "终": "마침",
    "鼓勵": "격려", "鼓励": "격려", "容認": "용인", "繁栄": "번영",
    "以及": "및", "羊群": "양 떼", "局": "국면", "平": "평안",
    "生": "삶", "義務": "의무", "聖潔": "성결", "因此": "그러므로",
    "頭": "머리", "譴責": "견책", "惩罰": "징벌", "惩罚": "징벌",
    "灭亡": "멸망", "涉及": "관련됨", "犧牲": "희생", "犠牲": "희생",
    "推論": "추론", "曲解": "곡해", "買": "삼", "持": "가짐",
    "猛烈": "맹렬", "残忍": "잔인", "殘忍": "잔인", "嫌悪": "혐오",
    "嫌惡": "혐오", "听衆": "청중", "聽衆": "청중", "声音": "목소리",
    "聲音": "목소리", "衰退": "쇠퇴", "衰亡": "쇠망", "品格": "품격",
    "犯罪者": "범죄자", "党": "당", "派": "파", "唯一": "유일",
    "握": "쥠", "教示": "교시", "採用": "채용", "采用": "채용",
    "驳": "반박", "介绍": "소개", "介紹": "소개", "逃": "피함",
    "得": "얻음", "先": "먼저", "先行": "선행", "歴史家": "역사가",
    "歷史家": "역사가", "竟然": "마침내", "違": "어긋남", "廣": "넓음",
    "广": "넓음", "永久": "영구", "普通": "보통", "積累": "축적",
    "积累": "축적", "积極": "적극", "积极": "적극", "赞同": "찬동",
    "贊同": "찬동", "赞成": "찬성", "赞扬": "찬양", "讚揚": "찬양",
    "献": "드림", "献上": "드림", "獻上": "드림", "祈": "기도",
    "冒": "무릅씀", "省": "살핌", "受": "받음", "入": "들어감",
    "誠實心": "진실한 마음", "真理를": "진리를", "真心": "진심",
    "过程": "과정", "過程": "과정", "机会": "기회", "機會": "기회",
    "真相": "진실", "信徒": "신자", "特征": "특징", "特徴": "특징",
    "光": "빛", "身体": "몸", "身份": "신분", "程度": "정도",
    "决定": "결정", "決定": "결정", "选择": "선택", "選擇": "선택",
    "关系": "관계", "關係": "관계", "问题": "문제", "問題": "문제",
    "能力": "능력", "责任": "책임", "責任": "책임", "态度": "태도",
    "態度": "태도", "情况": "상황", "情況": "상황", "结果": "결과",
    "結果": "결과", "原因": "원인", "目的": "목적", "方法": "방법",
    "意味": "의미", "价值": "가치", "價値": "가치", "证明": "증명",
    "證明": "증명", "真实": "진실", "真實": "진실",
}

_HAN_RUN = re.compile(r"[㐀-䶿一-鿿豈-﫿々〆]+")


def normalize_claim(text: str) -> tuple[str, bool, list[str]]:
    """Return (new_text, changed, residual_runs)."""
    residual: list[str] = []
    changed = False

    def _sub(m: re.Match) -> str:
        nonlocal changed
        run = m.group(0)
        if run in _HANJA_KO:
            changed = True
            return _HANJA_KO[run]
        residual.append(run)
        return run

    new_text = _HAN_RUN.sub(_sub, text)
    return new_text, changed, residual


def process_volume(identifier: str, *, apply: bool, allow_partial: bool) -> dict:
    vol_dir = TSU_ROOT / identifier
    tsu_path = vol_dir / "tsu.json"
    rpt_path = vol_dir / "tsu_report.json"
    if not tsu_path.exists():
        return {"identifier": identifier, "error": "tsu.json not found"}

    if rpt_path.exists():
        rpt = json.loads(rpt_path.read_text(encoding="utf-8"))
        if rpt.get("partial") is True and not allow_partial:
            return {"identifier": identifier, "error": "tsu_report.partial=true (pass --allow-partial to override)"}
    else:
        rpt = None

    records = json.loads(tsu_path.read_text(encoding="utf-8"))
    total = len(records)
    had_han = 0
    normalized = 0
    residual_rows = 0
    skipped_done = 0
    residual_tokens: dict[str, int] = {}
    residual_ids: list[str] = []

    for r in records:
        claim = r.get("claim", "")
        if r.get("cjk_status") == "normalized":
            skipped_done += 1
            continue
        if not _HAN_RUN.search(claim):
            continue
        had_han += 1
        new_claim, changed, residual = normalize_claim(claim)
        if changed and "claim_raw" not in r:
            r["claim_raw"] = claim
        r["claim"] = new_claim
        if residual:
            residual_rows += 1
            r["cjk_status"] = "residual"
            r["needs_review"] = "cjk_residual"
            residual_ids.append(r.get("id"))
            for tok in residual:
                residual_tokens[tok] = residual_tokens.get(tok, 0) + 1
        else:
            normalized += 1
            r["cjk_status"] = "normalized"
            r.pop("needs_review", None)

    summary = {
        "identifier": identifier,
        "normalize_version": NORMALIZE_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_records": total,
        "already_normalized_skipped": skipped_done,
        "had_han_this_run": had_han,
        "fully_normalized": normalized,
        "residual_rows": residual_rows,
        "residual_distinct_tokens": len(residual_tokens),
        "residual_token_freq": dict(sorted(residual_tokens.items(), key=lambda kv: -kv[1])),
        "residual_tsu_ids": residual_ids,
        "applied": apply,
    }

    if apply:
        tsu_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        (vol_dir / "cjk_normalize_report.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        if rpt is not None:
            rpt["cjk_normalize_version"] = NORMALIZE_VERSION
            rpt_path.write_text(json.dumps(rpt, ensure_ascii=False, indent=2), encoding="utf-8")

    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Fuller TSU claim CJK normalization (post-processing)")
    ap.add_argument("--identifier", help="single volume, e.g. Fuller_Complete_Works_Vol01")
    ap.add_argument("--all", action="store_true", help="every Fuller_Complete_Works_Vol* with a tsu.json")
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry-run)")
    ap.add_argument("--allow-partial", action="store_true", help="also process volumes still being written by F2")
    args = ap.parse_args(argv)

    if args.all:
        targets = sorted(d.name for d in TSU_ROOT.iterdir()
                         if d.is_dir() and d.name.startswith("Fuller_Complete_Works_Vol")
                         and (d / "tsu.json").exists())
    elif args.identifier:
        targets = [args.identifier]
    else:
        ap.error("pass --identifier or --all")
        return 2

    for ident in targets:
        s = process_volume(ident, apply=args.apply, allow_partial=args.allow_partial)
        if s.get("error"):
            print(f"[{ident}] SKIP — {s['error']}")
            continue
        print(f"[{ident}] {'APPLIED' if args.apply else 'DRY-RUN'} — "
              f"total={s['total_records']} had_han={s['had_han_this_run']} "
              f"fully_normalized={s['fully_normalized']} residual_rows={s['residual_rows']} "
              f"(skipped_done={s['already_normalized_skipped']})")
        if s["residual_token_freq"]:
            top = list(s["residual_token_freq"].items())[:15]
            print("        residual top:", ", ".join(f"{t}×{c}" for t, c in top))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
