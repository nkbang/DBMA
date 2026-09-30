import json
from pathlib import Path

TSU_ROOT = Path("/Users/David/DBMA/NAE/corpus/tsu")

for doc_dir in sorted(TSU_ROOT.iterdir()):
    if not doc_dir.is_dir() or doc_dir.name.startswith("_"):
        continue
    tsu_path = doc_dir / "tsu.json"
    if not tsu_path.exists():
        print(f"=== {doc_dir.name} === (NO tsu.json)")
        continue
    d = json.loads(tsu_path.read_text(encoding="utf-8"))
    count = len(d)
    if d:
        sample = d[0]
        title = sample.get("source_title", "N/A")
        author = sample.get("source_author", "N/A")
        doc_type = sample.get("document_type", "N/A")
        lang = sample.get("language", "N/A")
    else:
        title = author = doc_type = lang = "EMPTY"
    print(f"=== {doc_dir.name} === TSUs={count}")
    print(f"  title:   {title}")
    print(f"  author:  {author}")
    print(f"  type:    {doc_type}")
    print(f"  language:{lang}")
