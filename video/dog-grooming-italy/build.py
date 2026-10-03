#!/usr/bin/env python3
"""Build the episode from clips/ according to edl.csv.

Usage: python3 build.py [--landscape] [--music track.mp3]
Output: out/episode.mp4 (1080x1920 by default, 1920x1080 with --landscape).
"""
import argparse, csv, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = "DejaVu Sans"  # has Hebrew glyphs


def ts(sec):
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--landscape", action="store_true")
    ap.add_argument("--music", help="background track, mixed under the original audio")
    args = ap.parse_args()
    w, h = (1920, 1080) if args.landscape else (1080, 1920)

    rows = []
    with open(os.path.join(HERE, "edl.csv"), encoding="utf-8") as f:
        for r in csv.reader(line for line in f if line.strip() and not line.startswith("#")):
            name, start, end = r[0].strip(), float(r[1]), float(r[2])
            caption = ",".join(r[3:]).strip() if len(r) > 3 else ""
            rows.append((name, start, end, caption))
    if not rows:
        sys.exit("edl.csv is empty: add clip rows first")

    out = os.path.join(HERE, "out")
    os.makedirs(out, exist_ok=True)
    parts, t, events = [], 0.0, []
    for i, (name, start, end, caption) in enumerate(rows):
        part = os.path.join(out, f"part{i:03d}.mp4")
        vf = (f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
              "setsar=1,fps=30,format=yuv420p")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(start), "-to", str(end),
                        "-i", os.path.join(HERE, "clips", name),
                        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                        "-filter_complex", f"[0:v]{vf}[v];[0:a][1:a]amix=inputs=2:duration=first[a]"
                        if has_audio(os.path.join(HERE, "clips", name)) else f"[0:v]{vf}[v];[1:a]anull[a]",
                        "-map", "[v]", "-map", "[a]", "-shortest",
                        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                        "-c:a", "aac", "-ar", "48000", "-ac", "2", part], check=True)
        dur = end - start
        if caption:
            events.append((t, t + dur, caption))
        parts.append(part)
        t += dur

    ass = os.path.join(out, "captions.ass")
    with open(ass, "w", encoding="utf-8") as f:
        f.write(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Cap,{FONT},{64 if w < h else 56},&H00FFFFFF,&H00000000,&H80000000,1,3,4,0,2,60,60,{int(h*0.18)}

[Events]
Format: Layer, Start, End, Style, Text
""")
        for a, b, text in events:
            f.write(f"Dialogue: 0,{ts(a)},{ts(b)},Cap,{text}\n")

    lst = os.path.join(out, "list.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{p}'\n" for p in parts)
    joined = os.path.join(out, "joined.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", lst, "-c", "copy", joined], check=True)

    final = os.path.join(out, "episode.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", joined]
    if args.music:
        cmd += ["-stream_loop", "-1", "-i", args.music, "-filter_complex",
                f"[0:v]subtitles={ass}[v];[1:a]volume=0.15[m];[0:a][m]amix=inputs=2:duration=first[a]",
                "-map", "[v]", "-map", "[a]"]
    else:
        cmd += ["-vf", f"subtitles={ass}"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", final]
    subprocess.run(cmd, check=True)
    print(f"done: {final}  ({t:.1f}s)")


def has_audio(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
                        "stream=index", "-of", "csv=p=0", path], capture_output=True, text=True)
    return bool(r.stdout.strip())


if __name__ == "__main__":
    main()
