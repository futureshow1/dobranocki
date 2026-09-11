#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dodaje Konika Garbuska i odcinki Pająka chwata; usuwa diafilm Frakka i reportaż."""
import json, os, re, subprocess
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEC_ZSRR = "ZSRR: Wilk i Zając, Kiwaczek, kot Leopold"
SEC_HU = "Węgry: Gustaw i Pająk chwat"
PAJAK = "Pająk chwat wszystkich brat"
KONIK = "Konik Garbusek"
MAX_EPS = 12

ADD = [
    ("tcbzzn0jFic", SEC_ZSRR, KONIK, "Film z 1947 — polski dubbing (VHS)", 1947, "full"),
    ("xS2WX1PiZuQ", SEC_ZSRR, KONIK, "Remake z 1975 (wersja oryginalna, RU)", 1975, "full"),
    ("w8E_IF8CZQ4", SEC_HU, PAJAK, "Czołówka z piosenką (HU)", None, "fragment"),
    ("2XkHwq0V6tI", SEC_HU, PAJAK, "Odcinek z retro-emisji TV (HU)", None, "full"),
    ("k4hFvRPrTu0", SEC_HU, PAJAK, "Fragment polskiej emisji (Wieczorynka, 1988)", None, "fragment"),
    ("fh-FDqBES20", SEC_HU, PAJAK, "Zapowiedź wersji odnowionej cyfrowo (HU)", None, "fragment"),
]
# diafilmy i reportaże to nie animacja: Frakk (przezrocza), Kecskeméti TV (reportaż o rekonstrukcji)
REMOVE_IDS = {"ySElAZdquTs", "keBgtuq30So"}
FIX = {"iqbpK30LwHI": {"film": "Odcinek (HU)", "year": None}}
# kolejność odtwarzania w nowych zestawach: czołówka, odcinki, fragmenty
MANUAL_ORDER = {
    PAJAK: ["w8E_IF8CZQ4", "iqbpK30LwHI", "2XkHwq0V6tI", "k4hFvRPrTu0", "fh-FDqBES20"],
    KONIK: ["tcbzzn0jFic", "xS2WX1PiZuQ"],
}


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
        capture_output=True, text=True, timeout=90)
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
    before = len(rows)
    rows = [r for r in rows if r["id"] not in REMOVE_IDS]
    removed = before - len(rows)
    for r in rows:
        r.update(FIX.get(r["id"], {}))
    seen = {r["id"] for r in rows}

    todo = [a for a in ADD if a[0] not in seen]
    with ThreadPoolExecutor(6) as ex:
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
        order = MANUAL_ORDER.get(key[1])
        if order:
            eps.sort(key=lambda r: order.index(r["id"]) if r["id"] in order else len(order))
        else:
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
    print(f"final-01.jsonl: {len(out)} odcinków (dodano {len(embed_lines)}, usunięto {removed})")


if __name__ == "__main__":
    main()
