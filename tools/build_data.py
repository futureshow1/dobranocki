#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scala results/final-*.jsonl -> data.js portalu.
- dedupe po id (zostaje pierwsze wystąpienie wg kolejności rozdziałów),
- sortowanie w rozdziale po roku, potem po twórcy,
- nakłada embed_report.jsonl (jeśli istnieje): usuwa niedostępne, flaguje noembed,
- waliduje nazwy sekcji względem listy SECTIONS_PL.
Użycie: python3 build_data.py
"""
import glob, json, os, sys, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECTIONS_PL = [
    "Bielsko-Biała: Bolek i Lolek, Reksio",
    "Se-ma-for: Miś Uszatek i dobranocki z Łodzi",
    "Studio Miniatur Filmowych: dobranocki z Warszawy",
    "Czechosłowacja: Krecik, Rumcajs, Sąsiedzi",
    "ZSRR: Wilk i Zając, Kiwaczek, kot Leopold",
    "NRD i RFN: Piaskowy Dziadek i Pszczółka Maja",
    "Węgry: Gustaw i Wodnik Szuwarek",
    "Ameryka w Wieczorynce: Smerfy, Gumisie, Disney",
    "Europa Zachodnia i koprodukcje lat 90.",
]
ORDER = {s: i for i, s in enumerate(SECTIONS_PL)}


def main():
    rows = []
    for path in sorted(glob.glob(os.path.join(ROOT, "results", "final-*.jsonl"))):
        with open(path, encoding="utf-8") as f:
            for ln, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"BŁĄD JSON {path}:{ln}: {e}", file=sys.stderr)

    # embed report (opcjonalny)
    embed = {}
    ep = os.path.join(ROOT, "results", "embed_report.jsonl")
    if os.path.exists(ep):
        with open(ep, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    embed[r["id"]] = r

    bad_sections = sorted({r["section"] for r in rows if r["section"] not in ORDER})
    for s in bad_sections:
        print(f"NIEZNANA SEKCJA (pomijam filmy): {s!r}", file=sys.stderr)

    seen, out, dropped_dupe, dropped_avail = set(), [], 0, 0
    rows.sort(key=lambda r: (ORDER.get(r["section"], 99),
                             r.get("year") if isinstance(r.get("year"), int) else 9999,
                             r.get("artist", "")))
    for r in rows:
        if r["section"] not in ORDER:
            continue
        vid = r.get("id")
        if not vid or vid in seen:
            dropped_dupe += 1
            continue
        e = embed.get(vid)
        if e is not None and not e.get("ok"):
            dropped_avail += 1
            print(f"NIEDOSTĘPNY: {r['artist']} — {r['film']} ({vid})", file=sys.stderr)
            continue
        seen.add(vid)
        if isinstance(r.get("year"), int) and r["year"] < 1830:
            r["year"] = None  # umowne daty zjawisk przedfilmowych — nie pokazujemy
        d = int(r.get("duration_seconds") or 0)
        rec = {
            "section": r["section"],
            "artist": r.get("artist", ""),
            "film": r.get("film", ""),
            "year": r.get("year"),
            "url": f"https://www.youtube.com/watch?v={vid}",
            "id": vid,
            "duration": r.get("duration") or (f"{d//3600}:{d%3600//60:02d}:{d%60:02d}" if d >= 3600 else f"{d//60}:{d%60:02d}"),
            "duration_seconds": d,
            "views": int(r.get("views") or 0),
            "channel": r.get("channel", ""),
            "thumbnail": r.get("thumbnail") or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
            "type": r.get("type", "full"),
        }
        if r.get("source"):
            rec["source"] = r["source"]
            rec["url"] = r.get("url") or rec["url"]
        if e is not None and not e.get("playable_in_embed") or (e or {}).get("age_limit", 0) >= 18:
            rec["noembed"] = True
        out.append(rec)

    per = {}
    for r in out:
        per[r["section"]] = per.get(r["section"], 0) + 1
    today = datetime.date.today().isoformat()
    with open(os.path.join(ROOT, "data.js"), "w", encoding="utf-8") as f:
        f.write(f"// Wygenerowane {today} przez tools/build_data.py — {len(out)} filmów, {len(per)} rozdziałów.\n")
        f.write("window.FILMS = ")
        f.write(json.dumps(out, ensure_ascii=False, indent=1))
        f.write(";\n")
    print(f"\ndata.js: {len(out)} filmów, {len(per)}/{len(SECTIONS_PL)} rozdziałów; duplikaty: {dropped_dupe}, niedostępne: {dropped_avail}")
    for s in SECTIONS_PL:
        n = per.get(s, 0)
        mark = "  " if n >= 10 else ("!!" if n < 6 else " !")
        print(f"{mark} {n:3d}  {s}")


if __name__ == "__main__":
    main()
