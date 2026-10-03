#!/usr/bin/env python3
"""Write edl.csv from clips/ in shooting order (creation_time from the file
metadata, falling back to file mtime). Clips whose name starts with "out_"
(outdoor footage) are woven in after every N indoor clips, and any left over go
at the end.

Usage: python3 chrono_edl.py [--every 3] [--max-seconds 8]
Then edit the captions/trim points in edl.csv if needed and run build.py.
"""
import argparse, json, os, subprocess
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO_EXT = (".mp4", ".mov", ".m4v", ".webm", ".3gp")


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", path],
                       capture_output=True, text=True)
    fmt = json.loads(r.stdout or "{}").get("format", {})
    created = (fmt.get("tags") or {}).get("creation_time")
    try:
        t = datetime.fromisoformat(created.replace("Z", "+00:00")).timestamp()
    except Exception:
        t = os.path.getmtime(path)
    return t, float(fmt.get("duration", 0) or 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--every", type=int, default=3, help="indoor clips between outdoor inserts")
    ap.add_argument("--max-seconds", type=float, default=8, help="max length taken from each clip")
    a = ap.parse_args()
    clips = []
    for name in os.listdir(os.path.join(HERE, "clips")):
        if name.lower().endswith(VIDEO_EXT):
            t, dur = probe(os.path.join(HERE, "clips", name))
            clips.append((t, name, dur))
    clips.sort()
    indoor = [c for c in clips if not c[1].startswith("out_")]
    outdoor = [c for c in clips if c[1].startswith("out_")]
    order = []
    for i, c in enumerate(indoor, 1):
        order.append((c, ""))
        if i % a.every == 0 and outdoor:
            order.append((outdoor.pop(0), "זאת איטליה"))
    order += [(c, "זאת איטליה") for c in outdoor]
    with open(os.path.join(HERE, "edl.csv"), "w", encoding="utf-8") as f:
        f.write("# file,start_sec,end_sec,caption  (generated in shooting order; edit freely)\n")
        for (t, name, dur), cap in order:
            f.write(f"{name},0,{min(dur, a.max_seconds):.2f},{cap}\n")
    print(f"{len(order)} clips written to edl.csv")


if __name__ == "__main__":
    main()
