#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zbiera ZESTAWY odcinków dla każdego serialu-dobranocki.
Wejście: TSV — section \t series \t type \t min_sec \t max_sec \t maxn \t query1;query2
Wyjście: JSONL — {"section","artist","type","episodes":[{id,title,duration,...}]}
Użycie: python3 search_series.py series.tsv out.jsonl [--workers 8] [--per 20]
"""
import json, math, re, subprocess, sys, unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed

GOOD_CHANNELS = [
    "bolek i lolek", "bolek and lolek", "reksio", "studio filmow rysunkowych",
    "sfr bielsko", "se-ma-for", "semafor", "studio miniatur", "mis uszatek",
    "zaczarowany olowek", "colargol", "tvp", "wfdif", "fina", "35mm",
    "krtek", "little mole", "cheburashka", "soyuzmultfilm", "soiuzmultfilm",
    "союзмультфильм", "советские мультфильмы", "nu pogodi", "sandmannchen",
    "sandmann", "rbb", "die biene maja", "pszczolka maja", "maya the bee",
    "smurfs", "smerfy", "moomin", "muminki", "pat a mat", "patamat",
    "pat i mat", "kratky film", "krátký film", "ceska televize", "bonton",
    "pohadky", "rozpravky", "studio 100", "pannonia", "magyar", "mtva",
    "pingu", "tabaluga", "bajki", "dobranocka", "wieczorynka", "pikpok",
    "tvbajkipl", "kreskowki",
]
BAD_WORDS = [
    "reaction", "react", "review", "analysis", "explained", "breakdown",
    "commentary", "ranked", "podcast", "essay", "top 10", "top10",
    "recenzja", "analiza", "omówienie", "ranking", "speedpaint", "tutorial",
    "how to draw", " ai ", "ai remaster", "remake by", "interview",
    "making of", "behind the scenes", "video essay", "wywiad", "parodia",
    "parody", "przerobka", "przeróbka", "cover", "remix", "gameplay",
    "minecraft", "roblox", "brainrot", "polski ład", "meme", "edit",
    "1 hour", "10 hours", "slowed", "reverb",
]
FRAG_WORDS = ["trailer", "zwiastun", "czołówka", "czolowka", "intro", "outro",
              "opening", "teaser", "piosenka", "theme song", "tekst"]


def norm(s):
    s = unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9 ]+", " ", s.lower()).strip()


STOP = set("the a an i w na o do z of und le la".split())


def tokens(s):
    return [t for t in norm(s).split() if t not in STOP and len(t) > 1]


def score(e, series, mn, mx, typ):
    title = e.get("title") or ""
    nt = norm(title)
    dur = e.get("duration") or 0
    views = e.get("view_count") or 0
    channel = norm(e.get("channel") or e.get("uploader") or "")
    s = 0.0
    st = tokens(series)
    hit = sum(1 for t in st if t in nt or t in channel)
    if st:
        s += 30.0 * hit / len(st)
        if hit == 0:
            s -= 25
    if dur:
        lo, hi = (mn or 40), (mx or 9000)
        s += 15 if lo <= dur <= hi else -30
    for w in BAD_WORDS:
        if w in nt:
            s -= 45
            break
    frag = any(w in nt for w in FRAG_WORDS)
    if frag:
        s += 8 if typ == "fragment" else -25
    if any(g in channel for g in GOOD_CHANNELS):
        s += 18
    s += 2.0 * math.log10(views + 1)
    return s


def rec(e, sc):
    d = int(e.get("duration") or 0)
    return {
        "id": e["id"], "title": e.get("title"), "score": round(sc, 1),
        "duration_seconds": d,
        "duration": f"{d//3600}:{d%3600//60:02d}:{d%60:02d}" if d >= 3600 else f"{d//60}:{d%60:02d}",
        "views": e.get("view_count") or 0,
        "channel": e.get("channel") or e.get("uploader") or "",
    }


def search_series(row, per):
    section, series, typ, mn, mx, maxn, queries = row
    seen, entries = set(), []
    for q in queries.split(";"):
        q = q.strip()
        if not q:
            continue
        try:
            out = subprocess.run(
                ["yt-dlp", "-J", "--flat-playlist", "--no-warnings", f"ytsearch{per}:{q}"],
                capture_output=True, text=True, timeout=120)
            data = json.loads(out.stdout or "{}")
            for e in (data.get("entries") or []):
                if e and e.get("id") and e["id"] not in seen \
                   and e.get("live_status") in (None, "not_live", "was_live"):
                    seen.add(e["id"])
                    entries.append(e)
        except Exception:
            pass
    scored = sorted(((score(e, series, int(mn or 0), int(mx or 0), typ), e) for e in entries),
                    key=lambda x: -x[0])
    eps = [rec(e, sc) for sc, e in scored if sc > 12][: int(maxn or 10)]
    return {"section": section, "artist": series, "type": typ, "episodes": eps}


def main():
    inp, outp = sys.argv[1], sys.argv[2]
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 8
    per = int(sys.argv[sys.argv.index("--per") + 1]) if "--per" in sys.argv else 20
    rows = []
    for line in open(inp, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 7:
            print(f"POMIJAM (kolumny={len(parts)}): {line[:80]}", file=sys.stderr)
            continue
        rows.append(parts)
    results = [None] * len(rows)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(search_series, r, per): i for i, r in enumerate(rows)}
        done = 0
        for f in as_completed(futs):
            i = futs[f]
            results[i] = f.result()
            done += 1
            r = results[i]
            print(f"[{done}/{len(rows)}] {len(r['episodes']):2d} odc.  {r['artist']}", file=sys.stderr)
    with open(outp, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    total = sum(len(r["episodes"]) for r in results)
    print(f"GOTOWE: {total} odcinków w {len(results)} serialach → {outp}", file=sys.stderr)


if __name__ == "__main__":
    main()
