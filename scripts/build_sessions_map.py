#!/usr/bin/env python3
"""בונה את sessions-map.md מתוך פלט של list_sessions (קובץ JSON אחד או יותר).

שימוש: python3 scripts/build_sessions_map.py out.md page1.txt [page2.txt ...]
הסיווג לפי מילות מפתח בכותרת. שיחה של לקוח מזוהה לפי התבנית "לקוח: שם" בכותרת,
כך שכל לקוח חדש מקבל אוטומטית סעיף משלו, בלי לעדכן את הסקריפט.
"""
import json, re, sys
from collections import defaultdict

CATEGORIES = [
    ("מכירות ושיחות התאמה", r"ומכרת|מכרת|תסריט|שיחת מכירה|שיחות מכירה|מהלך השכנוע|התנגדויות|לירון|מכירות|הצעה|חבילה"),
    ("וובינר סוויץ' - שיווק ומשפך", r"וובינר סוויץ|webinar switch|VSL|משפך|פופאפ|לוגו|דף התודה|almost-finished|לקוח אידאלי|מסר|פודקאסט|קידום|E5|דף מכירה"),
    ("וובינרים של לקוחות", r"וובינר|webinar"),
    ("תמלול ותוכן", r"תמלול|transcri|zoom|SRT|סרטונ|וידאו|video|ivrit|Turboscribe|Gemini"),
    ("אתר, וורדפרס ודפים", r"וורדפרס|ווירדפרס|wordpress|Elementor|Vimeo|Bunny|דף|אתר|redirect|responsive"),
    ("כלים, אוטומציות ותשתית", r"WhatsApp|ווטסאפ|וואטסאפ|Gmail|Cloudflare|Cal\.com|קלנדלי|token|טוקנים|Remote Control|Claude|VS Code|instance|gcloud|webhook|AudD|אנטי וירוס|Edge|Ymio|access"),
]
LIMIT = 65  # אחוז מאורך השיחה שמעליו פותחים שיחה חדשה
CLIENT_RE = re.compile(r"^\s*לקוח\s*:\s*([^|·\-–]+)")

def load(paths):
    rows, seen = [], set()
    for p in paths:
        t = open(p, encoding="utf-8").read()
        d, _ = json.JSONDecoder().raw_decode(t[t.find("{"):])
        data = d.get("ccr", d).get("data", [])
        for s in data:
            if s["id"] in seen:
                continue
            seen.add(s["id"])
            ps = s.get("post_turn_summary") or {}
            cu = (s.get("external_metadata") or {}).get("context_usage") or {}
            pct = round(100 * cu["used_tokens"] / cu["max_tokens"]) if cu.get("max_tokens") and cu.get("used_tokens") else None
            rows.append(dict(id=s["id"], created=s["created_at"][:10], pct=pct,
                             archived=s.get("session_status") == "SESSION_STATUS_ARCHIVED",
                             pc=s.get("environment_kind") == "bridge",
                             updated=(s.get("updated_at") or "")[:10],
                             title=(s.get("title") or "").strip(),
                             summary=(ps.get("status_detail") or "").replace("\n", " ").strip()))
    return rows

def classify(title):
    m = CLIENT_RE.match(title)
    if m:
        return "לקוחות", m.group(1).strip()
    if title.startswith("yesh-pc-") or not title:
        return "שיחות מהמחשב בלי כותרת", None
    for name, pat in CATEGORIES:
        if re.search(pat, title, re.I):
            return name, None
    return "שונות (כולל שיחות לקוח שעוד לא קיבלו כותרת בתבנית)", None

def main(out, paths):
    rows = load(paths)
    groups = defaultdict(list)
    clients = defaultdict(list)
    for r in rows:
        cat, client = classify(r["title"])
        (clients[client] if client else groups[cat]).append(r)
    order = ["מכירות ושיחות התאמה", "וובינר סוויץ' - שיווק ומשפך", "וובינרים של לקוחות",
             "תמלול ותוכן", "אתר, וורדפרס ודפים", "כלים, אוטומציות ותשתית",
             "שונות (כולל שיחות לקוח שעוד לא קיבלו כותרת בתבנית)", "שיחות מהמחשב בלי כותרת"]
    link = lambda r: f"[{r['title'] or r['id']}](https://claude.ai/code/{r['id']})"
    def fill(r):
        if r["pct"] is None:
            return "?"
        mark = "✅" if r["pct"] < LIMIT else "⛔"
        return f"{mark} {r['pct']}%" + (" (בארכיון)" if r["archived"] else "")
    line = lambda r: f"| {r['updated'] or r['created']} | {link(r)} | {fill(r)} | {r['summary'][:110]} |"
    head = ["| עודכן | שיחה | מלאה | מצב אחרון |", "|---|---|---|---|"]
    L = ["# מפת השיחות", "",
         f"נבנה אוטומטית מ־{len(rows)} שיחות. לחיצה על שם שיחה פותחת אותה בכל מכשיר (claude.ai/code).",
         "אל תערוך ידנית: כל שיחה מעדכנת את הקובץ בסוף העבודה (ראה CLAUDE.md).",
         f"✅ = מתחת ל־{LIMIT}% מהאורך, אפשר להמשיך בה. ⛔ = מלאה, פותחים חדשה.", ""]
    open_rows = [r for r in rows if r["pct"] is not None and r["pct"] < LIMIT and not r["archived"]
                 and r["title"] and not r["title"].startswith("yesh-pc-")]
    if open_rows:
        L += [f"## ✅ שיחות פתוחות שאפשר להמשיך (מתחת ל־{LIMIT}%)", ""] + head
        L += [line(r) for r in sorted(open_rows, key=lambda r: r["updated"], reverse=True)] + [""]
    if clients:
        L += ["## לקוחות", ""]
        for c in sorted(clients):
            L += [f"### {c}", ""] + head
            L += [line(r) for r in sorted(clients[c], key=lambda r: r["updated"], reverse=True)] + [""]
    for cat in order:
        if not groups.get(cat):
            continue
        L += [f"## {cat}", ""] + head
        L += [line(r) for r in sorted(groups[cat], key=lambda r: r["updated"], reverse=True)] + [""]
    open(out, "w", encoding="utf-8").write("\n".join(L))
    print(f"{out}: {len(rows)} sessions")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
