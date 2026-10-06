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
            rows.append(dict(id=s["id"], created=s["created_at"][:10],
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
    line = lambda r: f"| {r['updated'] or r['created']} | {link(r)} | {r['summary'][:120]} |"
    L = ["# מפת השיחות", "",
         f"נבנה אוטומטית מ־{len(rows)} שיחות. לחיצה על שם שיחה פותחת אותה בכל מכשיר (claude.ai/code).",
         "אל תערוך ידנית: כל שיחה מעדכנת את הקובץ בסוף העבודה (ראה CLAUDE.md).", ""]
    if clients:
        L += ["## לקוחות", ""]
        for c in sorted(clients):
            L += [f"### {c}", "", "| עודכן | שיחה | מצב אחרון |", "|---|---|---|"]
            L += [line(r) for r in sorted(clients[c], key=lambda r: r["updated"], reverse=True)] + [""]
    for cat in order:
        if not groups.get(cat):
            continue
        L += [f"## {cat}", "", "| עודכן | שיחה | מצב אחרון |", "|---|---|---|"]
        L += [line(r) for r in sorted(groups[cat], key=lambda r: r["updated"], reverse=True)] + [""]
    open(out, "w", encoding="utf-8").write("\n".join(L))
    print(f"{out}: {len(rows)} sessions")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
