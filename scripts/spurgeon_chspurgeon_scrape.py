"""chspurgeon.com에서 MTP Vol51/52/53 전체 설교를 스크레이핑해
손상된 OCR 텍스트를 대체할 깨끗한 base txt를 생성한다.

이 사이트는 원문(1905~1907)을 현대어로 다듬은 판본이다(thee/thou -> you 등).
따라서 인용 시 1차 사료 원문과 완전히 동일하지는 않다 — 사용자 승인 하에 진행.
"""
import html
import os
import re
import sys
import time

import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (DBMA research bot; contact rev.bang@gmail.com)"}
BASE = "https://chspurgeon.com"

_LINK_RE = re.compile(r'href="(/sermons/[a-z0-9\-]+-(\d+))"')
_PRINT_META_RE = re.compile(
    r"Sermon No\. <!-- -->(\d+)<!-- --> . (?:<!-- -->([^<]*))?</div>"
    r"<div>Metropolitan Tabernacle Pulpit<!-- -->, Volume <!-- -->(\d+)<!-- -->"
)
_TITLE_RE = re.compile(
    r'font-size:20pt;font-weight:700;color:#1a1a1a;margin:0 0 4pt">([^<]+)</div>'
)
_SCRIPTURE_REF_RE = re.compile(r'print-accent"[^>]*>([^<]+)</p>')
_BODY_DIV_RE = re.compile(r'break-words"[^>]*><div class="mt-8">(.*?)</div>\s*</article>', re.S)
_P_RE = re.compile(r"<p[^>]*><span>(.*?)</span></p>", re.S)
_TAG_RE = re.compile(r"<[^>]+>")


def clean_html_text(s: str) -> str:
    s = _TAG_RE.sub("", s)
    s = html.unescape(s)
    return s.strip()


def get_volume_sermon_links(vol: int) -> list:
    url = f"{BASE}/sermons/collections/mtp/vol-{vol}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    seen = set()
    out = []
    for path, num in _LINK_RE.findall(r.text):
        if path in seen or "/collections/" in path:
            continue
        seen.add(path)
        out.append((path, int(num)))
    out.sort(key=lambda x: x[1])
    return out


def scrape_sermon(path: str) -> dict:
    url = BASE + path
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    text = r.text

    meta = _PRINT_META_RE.search(text)
    sermon_no = meta.group(1) if meta else "?"
    date = (meta.group(2) or "") if meta else ""
    vol = meta.group(3) if meta else "?"

    title_m = _TITLE_RE.search(text)
    title = html.unescape(title_m.group(1)) if title_m else path

    ref_m = _SCRIPTURE_REF_RE.search(text)
    scripture_ref = html.unescape(ref_m.group(1)) if ref_m else ""

    body_m = _BODY_DIV_RE.search(text)
    paras = []
    if body_m:
        for p in _P_RE.findall(body_m.group(1)):
            t = clean_html_text(p)
            if t:
                paras.append(t)

    return {
        "no": sermon_no,
        "date": date,
        "vol": vol,
        "title": title,
        "scripture_ref": scripture_ref,
        "paragraphs": paras,
    }


def format_sermon(s: dict) -> str:
    lines = [
        f"No. {s['no']} — {s['title']}",
        f"{s['scripture_ref']}",
        f"Metropolitan Tabernacle Pulpit, Volume {s['vol']} · Delivered {s['date']}",
        "",
    ]
    lines.extend(s["paragraphs"])
    return "\n\n".join(lines)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--volumes", help="쉼표구분 volume 번호 목록, 예: 51,52,53")
    ap.add_argument("--range", help="시작-끝 volume 범위, 예: 7-63")
    args = ap.parse_args()

    out_dir = args.out_dir
    if args.volumes:
        volumes = [int(v) for v in args.volumes.split(",")]
    elif args.range:
        lo, hi = args.range.split("-")
        volumes = list(range(int(lo), int(hi) + 1))
    else:
        volumes = [51, 52, 53]

    for vol in volumes:
        links = get_volume_sermon_links(vol)
        print(f"Vol{vol}: {len(links)}개 설교 발견")
        sermons_text = []
        for i, (path, num) in enumerate(links, 1):
            try:
                s = scrape_sermon(path)
            except Exception as e:
                print(f"  [{i}/{len(links)}] {path} 실패: {e}")
                continue
            if not s["paragraphs"]:
                print(f"  [{i}/{len(links)}] {path} 본문 없음(스킵)")
                continue
            sermons_text.append(format_sermon(s))
            if i % 10 == 0 or i == len(links):
                print(f"  [{i}/{len(links)}] 수집 완료")
            time.sleep(0.3)

        out_path = os.path.join(out_dir, f"Spurgeon_MTP_Vol{vol}.txt")
        full_text = ("\n\n" + "=" * 80 + "\n\n").join(sermons_text)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(full_text)
        print(f"Vol{vol}: {len(sermons_text)}편 저장 -> {out_path} ({len(full_text):,}자)\n")


if __name__ == "__main__":
    main()
