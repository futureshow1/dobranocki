#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wyszukiwarka YT dla portalu HISTORIA ANIMACJI.
Wejście: TSV (bez nagłówka), kolumny:
  section \t artist \t film \t year \t type \t min_sec \t max_sec \t query
  (type: full|fragment|documentary; min/max_sec: 0 = brak limitu)
Wyjście: JSONL — po jednej linii na wiersz wejścia:
  {"section","artist","film","year","type","query","pick":{...}|null,"alts":[...]}
Użycie: python3 search_yt.py input.tsv output.jsonl [--workers 8] [--per 6]
"""
import json, re, subprocess, sys, unicodedata, math
from concurrent.futures import ThreadPoolExecutor, as_completed

GOOD_CHANNELS = [
    "bolek i lolek", "bolek and lolek", "reksio", "studio filmow rysunkowych",
    "sfr bielsko", "se-ma-for", "semafor", "studio miniatur", "mis uszatek",
    "zaczarowany olowek", "colargol", "tvp", "wfdif", "fina", "35mm",
    "krtek", "little mole", "cheburashka", "soyuzmultfilm", "soiuzmultfilm",
    "союзмультфильм", "nu pogodi", "sandmannchen", "sandmann", "rbb",
    "die biene maja", "pszczolka maja", "maya the bee", "smurfs", "smerfy",
    "moomin", "muminki", "pat a mat", "patamat", "pat i mat", "kratky film",
    "krátký film", "ceska televize", "česká televize", "studio 100",
    "pannonia", "magyar", "mtva", "pingu", "tabaluga", "bajki",
    "dobranocka", "wieczorynka", "kreskowki", "kreskówki prl",
]
BAD_WORDS = [
    "reaction", "react", "review", "analysis", "explained", "breakdown",
    "commentary", "ranked", "tier list", "podcast", "essay", "top 10", "top10",
    "recenzja", "analiza", "omówienie", "ranking", "compilation of memes",
    "speedpaint", "tutorial", "how to draw", "ai ", " ai-", "remake by",
    "interview", "making of", "behind the scenes", "video essay", "introduces",
    "discusses", "wywiad", "documentary about", "parodia", "parody",
    "przerobka", "przeróbka", "jaka to melodia", "cover", "remix",
    "gameplay", "minecraft", "roblox", "brainrot", "ai remaster",
]
FRAG_WORDS = ["trailer", "zwiastun", "clip", "scene", "excerpt", "fragment", "opening", "intro", "sequence", "teaser"]
STOP = set("the a an le la les der die das el il lo un une und and of di de du i w na o do von des".split())


def norm(s):
    s = unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9 ]+", " ", s.lower()).strip()


def tokens(s):
    return [t for t in norm(s).split() if t not in STOP and len(t) > 1]


def score(entry, artist, film, year, typ, mn, mx):
    title = entry.get("title") or ""
    nt = norm(title)
    dur = entry.get("duration") or 0
    views = entry.get("view_count") or 0
    channel = norm(entry.get("channel") or entry.get("uploader") or "")
    s = 0.0
    ft = tokens(film)
    if ft:
        hit = sum(1 for t in ft if t in nt)
        s += 40.0 * hit / len(ft)
        if hit == 0:
            s -= 30
    at = tokens(artist)
    if at and any(t in nt or t in channel for t in at):
        s += 8
    if year and str(year) in title:
        s += 4
    if dur:
        lo = mn or 40
        hi = mx or 9000
        if lo <= dur <= hi:
            s += 20
        else:
            s -= 25
    for w in BAD_WORDS:
        if w in nt:
            s -= 45
            break
    # "Ktoś on/about Tytuł" = wideo O filmie, nie film
    if re.match(r"^[a-z]+ [a-z]+ (on|about) ", nt):
        s -= 40
    frag = any(w in nt for w in FRAG_WORDS)
    if frag:
        s += 10 if typ == "fragment" else -22
    if any(g in channel for g in GOOD_CHANNELS):
        s += 16
    s += 2.0 * math.log10(views + 1)
    return s


def search_one(row, per):
    section, artist, film, year, typ, mn, mx, query = row
    try:
        out = subprocess.run(
            ["yt-dlp", "-J", "--flat-playlist", "--no-warnings", f"ytsearch{per}:{query}"],
            capture_output=True, text=True, timeout=90,
        )
        data = json.loads(out.stdout or "{}")
        entries = [e for e in (data.get("entries") or []) if e and e.get("id")
                   and e.get("live_status") in (None, "not_live", "was_live")]
    except Exception as ex:
        entries = []
    scored = sorted(
        ((score(e, artist, film, year, typ, int(mn or 0), int(mx or 0)), e) for e in entries),
        key=lambda x: -x[0],
    )

    def rec(sc, e):
        d = int(e.get("duration") or 0)
        return {
            "id": e["id"], "title": e.get("title"), "score": round(sc, 1),
            "duration_seconds": d,
            "duration": f"{d//3600}:{d%3600//60:02d}:{d%60:02d}" if d >= 3600 else f"{d//60}:{d%60:02d}",
            "views": e.get("view_count") or 0,
            "channel": e.get("channel") or e.get("uploader") or "",
            "url": f"https://www.youtube.com/watch?v={e['id']}",
        }

    pick = rec(*scored[0]) if scored and scored[0][0] > 5 else None
    alts = [rec(sc, e) for sc, e in scored[1:4]]
    return {
        "section": section, "artist": artist, "film": film,
        "year": int(year) if str(year).isdigit() else year,
        "type": typ, "query": query, "pick": pick, "alts": alts,
    }


def main():
    inp, outp = sys.argv[1], sys.argv[2]
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 8
    per = int(sys.argv[sys.argv.index("--per") + 1]) if "--per" in sys.argv else 6
    rows = []
    with open(inp, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) != 8:
                print(f"POMIJAM (kolumny={len(parts)}): {line[:80]}", file=sys.stderr)
                continue
            rows.append(parts)
    results = [None] * len(rows)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(search_one, r, per): i for i, r in enumerate(rows)}
        done = 0
        for f in as_completed(futs):
            i = futs[f]
            results[i] = f.result()
            done += 1
            r = results[i]
            tag = "OK " if r["pick"] else "BRAK"
            print(f"[{done}/{len(rows)}] {tag} {r['artist']} — {r['film']}", file=sys.stderr)
    with open(outp, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    ok = sum(1 for r in results if r["pick"])
    print(f"GOTOWE: {ok}/{len(results)} znalezionych → {outp}", file=sys.stderr)


if __name__ == "__main__":
    main()
