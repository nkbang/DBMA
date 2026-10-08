import json, sys, os
from streamlit.testing.v1 import AppTest
tree, label, out = sys.argv[1], sys.argv[2], sys.argv[3]
os.chdir(tree); sys.path.insert(0, tree)
from core import module_registry as mr
res = {"label": label, "has_NAE": os.path.isdir("NAE"), "config_path": str(mr.CONFIG_PATH), "runs": []}
KEYS = ["Dashboard", "Library", "Processing", "Research", "설교 준비", "도움말"]
def run(page, view=None, enabled=False, query=None):
    mr.set_enabled("nae_pd", enabled)
    a = AppTest.from_file("dbma_ui.py", default_timeout=90)
    a.session_state["show_onboarding"] = False; a.session_state["nav_page"] = page
    if view: a.session_state["research_workspace_view"] = view
    a.run()
    rec = {"page": page, "view": view, "nae_pd": enabled}
    rec["selected"] = a.sidebar.radio(key="nav_page").value
    rec["page_selected_ok"] = rec["selected"] == page
    rec["exceptions"] = [str(e.value)[:200] for e in a.exception]
    rec["widgets"] = {"text_inputs": [t.key for t in a.text_input][:6], "buttons": len(a.button), "tabs": len(a.tabs), "radios": [r.key for r in a.radio][:4]}
    rec["has_nae_section"] = any("nae_research_query" in (t.key or "") for t in a.text_input)
    if query is not None:
        ti = [t for t in a.text_input if t.key and "nae_research_query" in t.key]
        if ti:
            pref = ti[0].key.replace("_nae_research_query", "")
            ti[0].set_value(query).run()
            btn = [b for b in a.button if b.key == f"{pref}_nae_search_btn"]
            if btn:
                if res["has_NAE"]:
                    import unittest.mock as m
                    with m.patch("NAE.retrieval_adapter.bridge_query", return_value=[]), m.patch("NAE.retrieval_adapter.bridge_query_paragraphs", return_value=[]):
                        btn[0].click().run()
                else:
                    btn[0].click().run()
                rec["search"] = {"clicked": True, "exceptions": [str(e.value)[:200] for e in a.exception], "warnings": [w.value[:90] for w in a.warning], "errors": [e.value[:90] for e in a.error]}
            else:
                rec["search"] = {"clicked": False, "reason": "no search button"}
        else:
            rec["search"] = {"clicked": False, "reason": "no nae input"}
    return rec
try:
    for p in KEYS:
        views = ["연구", "채팅"] if p == "Research" else [None]
        for v in views:
            res["runs"].append(run(p, v, False))
    for v in ["연구", "채팅"]:
        res["runs"].append(run("Research", v, True, query="로마서 3:23"))
finally:
    mr.set_enabled("nae_pd", False)
json.dump(res, open(out, "w"), ensure_ascii=False, indent=2); print("done", label)
