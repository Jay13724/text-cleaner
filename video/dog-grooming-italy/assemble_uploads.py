#!/usr/bin/env python3
"""Rebuild videos sent through the gallery-upload page.

The page stores each file as chunks (assets) plus a manifest row in db
collection "uploads". Save the manifests with ArtifactData list (out_dir)
and the chunks with Artifact read (path=<asset id>), then run:

  python3 assemble_uploads.py <manifest_dir> <chunk_dir> <out_dir>
"""
import base64, glob, json, os, sys

man_dir, chunk_dir, out_dir = sys.argv[1:4]
os.makedirs(out_dir, exist_ok=True)
for mf in sorted(glob.glob(os.path.join(man_dir, "**", "*.json"), recursive=True)):
    m = json.load(open(mf, encoding="utf-8"))
    m = m.get("data", m)
    if not m.get("done"):
        print("skip (incomplete):", m.get("name")); continue
    dest = os.path.join(out_dir, os.path.basename(m["name"]))
    with open(dest, "wb") as out:
        for c in m["chunks"]:
            src = glob.glob(os.path.join(chunk_dir, "**", c["id"] + ".*"), recursive=True)[0]
            data = open(src, "rb").read()
            out.write(base64.b64decode(data) if c["enc"] == "base64" else data)
    ok = os.path.getsize(dest) == m["size"]
    print(("ok  " if ok else "SIZE MISMATCH  ") + dest)
