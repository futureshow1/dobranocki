#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dokłada polskie odcinki Kubusia Puchatka, Smerfów i Gumisiów; usuwa zbędne EN."""
import json, os, re, subprocess
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEC_AM = "Ameryka w Wieczorynce: Smerfy, Gumisie, Disney"
MAX_EPS = 12

ADD = [
    # Nowe przygody Kubusia Puchatka — po polsku
    ("NK89TEiYg2c", SEC_AM, "Nowe przygody Kubusia Puchatka", "Kubuś aktorem (cały odcinek, Disney Channel PL)", 1988, "full"),
    ("JZ3bpp19lSA", SEC_AM, "Nowe przygody Kubusia Puchatka", "Hu! Hu, Puchatku (dubbing PL)", 1996, "full"),
    ("rpZkbAK2jFw", SEC_AM, "Nowe przygody Kubusia Puchatka", "Kubuś i pogromcy goblunów (film, dubbing PL)", None, "full"),
    ("0mb6F2sZZBI", SEC_AM, "Nowe przygody Kubusia Puchatka", "Poduszka (fragment, Disney Junior PL)", None, "fragment"),
    ("JWr6GONjNN8", SEC_AM, "Nowe przygody Kubusia Puchatka", "Grządki (fragment, Disney Junior PL)", None, "fragment"),
    # Smerfy — pełne odcinki po polsku (kanał oficjalny)
    ("F48GDa4CK8g", SEC_AM, "Smerfy", "Ślub Papy Smerfa", None, "full"),
    ("DbKbQdDF2FI", SEC_AM, "Smerfy", "Siostra Smerf", None, "full"),
    ("cticG6vXP6g", SEC_AM, "Smerfy", "Fioletowe Smerfy (zremasterowany)", None, "full"),
    ("_QCoRI1OcCg", SEC_AM, "Smerfy", "Magiczne jajo", None, "full"),
    ("hilRZHww_Bs", SEC_AM, "Smerfy", "Trufle dla wszystkich", None, "full"),
    ("ynlE2yYMzcM", SEC_AM, "Smerfy", "Źródło smerfności", None, "full"),
    ("hNDEuP5lDPc", SEC_AM, "Smerfy", "Olbrzym Gargamela", None, "full"),
    ("ZdKak10t7V4", SEC_AM, "Smerfy", "Czasem, podczas pełni (zremasterowany)", None, "full"),
    ("3kWnnL9zkpA", SEC_AM, "Smerfy", "Wiosenne kłopoty smerfów", None, "full"),
    ("QCk6sLv2FSk", SEC_AM, "Smerfy", "Pół żartem, pół Smerfem", None, "full"),
    # Gumisie — fragmenty po polsku
    ("BCbJOxQtpFc", SEC_AM, "Gumisie", "Odcinek 1, część 1 (PL)", None, "fragment"),
    ("ufNzZw0vg5E", SEC_AM, "Gumisie", "Odcinek 2, część 1 (PL)", None, "fragment"),
    ("v4NW3JyPnXw", SEC_AM, "Gumisie", "Odcinek 5, część 1 (PL)", None, "fragment"),
]
# angielski odcinek Smerfów ustępuje miejsca polskim
REMOVE_IDS = {"RgTpFaAm2f4"}


def ep_num(title):
    t = (title or "").lower()
    for pat in (r"odc\.?\s*(\d+)", r"odcinek\s*(\d+)", r"выпуск\s*(\d+)", r"серия\s*(\d+)",
                r"vypusk[^0-9]*(\d+)", r"[se]\d+\s*e(\d+)", r"folge\s*(\d+)",
                r"episode\s*(\d+)", r"\bep\.?\s*(\d+)", r"^(\d+)\b", r"\((e?\d+)\)"):
        m = re.search(pat, t)
        if m:
            try:
                return int(re.sub(r"\D", "", m.group(1)))
            except ValueError:
                pass
    return None


def fetch_meta(vid):
    out = subprocess.run(
        ["yt-dlp", "--no-warnings", "--ignore-no-formats-error",
         "--extractor-args", "youtube:player_client=web_safari", "--print",
         "%(duration)s|%(view_count)s|%(channel)s|%(playable_in_embed)s|%(availability)s",
         f"https://www.youtube.com/watch?v={vid}"],
        capture_output=True, text=True, timeout=60)
    line = (out.stdout or "").strip().splitlines()
    if not line:
        return vid, None
    dur, views, channel, emb, avail = (line[0].split("|", 4) + [""] * 5)[:5]
    return vid, {"duration_seconds": int(dur) if dur.isdigit() else 0,
                 "views": int(views) if views.isdigit() else 0, "channel": channel,
                 "embed": emb == "True", "ok": avail in ("public", "unlisted")}


def dur_str(d):
    return f"{d//3600}:{d%3600//60:02d}:{d%60:02d}" if d >= 3600 else f"{d//60}:{d%60:02d}"


def main():
    src = os.path.join(ROOT, "results", "final-01.jsonl")
    rows = [json.loads(l) for l in open(src, encoding="utf-8") if l.strip()]
    rows = [r for r in rows if r["id"] not in REMOVE_IDS]
    seen = {r["id"] for r in rows}

    todo = [a for a in ADD if a[0] not in seen]
    with ThreadPoolExecutor(8) as ex:
        metas = dict(ex.map(fetch_meta, [a[0] for a in todo]))
    embed_lines = []
    for vid, section, artist, film, year, typ in todo:
        m = metas.get(vid)
        if not m or not m["ok"]:
            print(f"POMIJAM (niedostępny): {artist} — {film} ({vid})")
            continue
        rows.append({"section": section, "artist": artist, "film": film, "year": year,
                     "type": typ, "id": vid, "duration": dur_str(m["duration_seconds"]),
                     "duration_seconds": m["duration_seconds"], "views": m["views"],
                     "channel": m["channel"]})
        embed_lines.append({"id": vid, "playable_in_embed": m["embed"],
                            "availability": "public", "age_limit": 0, "ok": True})

    by_series = {}
    for r in rows:
        by_series.setdefault((r["section"], r["artist"]), []).append(r)
    out = []
    for key, eps in by_series.items():
        def k(r):
            n = ep_num(r["film"])
            return (0 if n is not None else 1, n if n is not None else 0,
                    r["year"] or 9999, -(r["views"] or 0))
        eps.sort(key=k)
        if len(eps) > MAX_EPS:
            print(f"LIMIT {MAX_EPS}: {key[1]} — obcięto {len(eps) - MAX_EPS}")
        out.extend(eps[:MAX_EPS])

    with open(src, "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(os.path.join(ROOT, "results", "embed_report.jsonl"), "a", encoding="utf-8") as f:
        for r in embed_lines:
            f.write(json.dumps(r) + "\n")
    print(f"final-01.jsonl: {len(out)} odcinków (dodano {len(embed_lines)}, usunięto {len(REMOVE_IDS)})")


if __name__ == "__main__":
    main()
