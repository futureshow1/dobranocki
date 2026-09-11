#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scala kuratorowane final-01.jsonl + series.jsonl (z regułami) + MANUAL2 → final-01.jsonl."""
import json, os, re, shutil, subprocess, unicodedata
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_EPS = 12


def norm(s):
    s = unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9 ]+", " ", s.lower()).strip()


# artist -> reguły akceptacji nowych odcinków z series.jsonl
# "t": tytuł (raw lowercase) musi zawierać któryś wzorzec; "c": albo kanał (norm);
# "ban": odrzuć, gdy tytuł/kanał zawiera; brak reguł = nic nie przyjmuj (tylko kuratorowane).
RULES = {
    "Bolek i Lolek": {"t": ["bolek", "lolek"], "c": [], "ban": []},
    "Reksio": {"t": ["reksio"], "c": [], "ban": []},
    "Porwanie Baltazara Gąbki": {"t": ["baltazar", "porwanie", "deszczowc"], "c": [], "ban": []},
    "Pampalini łowca zwierząt": {"t": ["pampalini"], "c": [], "ban": []},
    "Miś Kudłatek": {"t": ["kudłatek", "kudlatek"], "c": [], "ban": []},
    "Marceli Szpak dziwi się światu": {"t": ["marceli szpak"], "c": [], "ban": []},
    "Zaczarowany ołówek": {"t": ["zaczarowany"], "c": ["zaczarowany olowek"], "ban": []},
    "Przygody Misia Colargola": {"t": ["colargol"], "c": [], "ban": []},
    "Mały pingwin Pik-Pok": {"t": ["pik pok", "pik-pok", "pikpok"], "c": [], "ban": ["audiob", "czytanie"]},
    "Przygody kota Filemona": {"t": ["filemon"], "c": [], "ban": []},
    "Krecik": {"t": ["krtek", "krecik", "mole"], "c": [], "ban": ["trailer", "promo"]},
    "Rozbójnik Rumcajs": {"t": ["rumcajs"], "c": [], "ban": []},
    "Sąsiedzi (Pat i Mat)": {"t": ["pat a mat", "pat & mat", "pat i mat"], "c": [], "ban": []},
    "Żwirek i Muchomorek": {"t": ["żwirek", "muchomorek", "křemílek", "vochomůrka"], "c": [], "ban": []},
    "Makowa panienka": {"t": ["makowa"], "c": [], "ban": []},
    "O wróżce Amałce": {"t": ["amálka", "amálce", "amalka"], "c": [], "ban": []},
    "Bob i Bobek": {"t": ["bobek"], "c": [], "ban": []},
    "Maxipes Fík": {"t": ["maxipes"], "c": [], "ban": []},
    "Wilk i Zając (Nu, pogodi!)": {"t": ["погоди", "pogodi"], "c": [], "ban": []},
    "Piaskowy Dziadek": {"t": ["sandmann"], "c": [], "ban": []},
    "Pszczółka Maja": {"t": ["maja"], "c": [], "ban": []},
    "Maurycy i Hawranek": {"t": ["maurycy"], "c": [], "ban": []},
    "Pomysłowy Dobromir": {"t": ["pomysłowy", "pomyslowy"], "c": [], "ban": ["hity", "bolek"]},
    "Smerfy": {"t": ["smerf", "smurf"], "c": [], "ban": ["polski ład", "polski lad"]},
    "Gumisie": {"t": ["gumisie", "gummi"], "c": [], "ban": []},
    "Chip i Dale: Brygada RR": {"t": ["rescue rangers", "chip"], "c": [], "ban": []},
    "Miś Yogi": {"t": ["yogi"], "c": [], "ban": ["nostalgia critic", "commercials", "bumpers"]},
    "Muminki (1990)": {"t": ["muminki", "moomin"], "c": [], "ban": []},
    "Pingu": {"t": ["pingu"], "c": [], "ban": []},
    "Tabaluga": {"t": ["tabaluga"], "c": [], "ban": []},
    "Bouli": {"t": ["bouli"], "c": [], "ban": []},
    "Wicky Wiking": {"t": ["wickie"], "c": [], "ban": []},
    "SimsalaGrimm": {"t": ["simsala"], "c": [], "ban": []},
}

# ręcznie dobrane odcinki (id, section, artist, film, year, type)
MANUAL2 = [
    ("sgtazEgrmJY", "ZSRR: Wilk i Zając, Kiwaczek, kot Leopold", "Przygody kota Leopolda", "Lato kota Leopolda (odc. 7)", 1983, "full"),
    ("6wM7UDioBAs", "ZSRR: Wilk i Zając, Kiwaczek, kot Leopold", "Przygody kota Leopolda", "Spacer kota Leopolda (odc. 5)", 1982, "full"),
    ("yPMONydyu3w", "ZSRR: Wilk i Zając, Kiwaczek, kot Leopold", "Przygody kota Leopolda", "Automobil kota Leopolda (odc. 11)", 1987, "full"),
    ("aWUB9qmiK5o", "ZSRR: Wilk i Zając, Kiwaczek, kot Leopold", "Przygody kota Leopolda", "Kot Leopold — wszystkie serie", 1975, "full"),
    ("NiYj3uD8vic", "ZSRR: Wilk i Zając, Kiwaczek, kot Leopold", "Malec i Karlsson", "Karlsson wraca", 1970, "full"),
    ("TZTjr-DN9xY", "ZSRR: Wilk i Zając, Kiwaczek, kot Leopold", "Malec i Karlsson", "Malec i Karlsson — wszystkie części", 1968, "full"),
    ("qrE8OERXtVU", "Węgry: Gustaw i Pająk chwat", "Gustaw", "Gustaw pesymista", 1970, "full"),
    ("a74nS2eAN4A", "Węgry: Gustaw i Pająk chwat", "Gustaw", "Gustaw łamie prawo", 1970, "full"),
    ("JhkEq3fDQzI", "Węgry: Gustaw i Pająk chwat", "Gustaw", "Gustaw oszukuje", 1970, "full"),
    ("-d06Bz3U2OQ", "Węgry: Gustaw i Pająk chwat", "Gustaw", "Gustaw odpoczywa (emisja PTK)", 1970, "full"),
    ("iqbpK30LwHI", "Węgry: Gustaw i Pająk chwat", "Pająk chwat wszystkich brat", "Pająk chwat wszystkich brat — odcinek", 1978, "full"),
    ("bcr7mRXMA_E", "Ameryka w Wieczorynce: Smerfy, Gumisie, Disney", "Kacze opowieści", "Gruba ryba ma nawet wieloryba (odc. 28, stary dubbing)", 1987, "full"),
    ("ZhlZOO1io9Y", "Ameryka w Wieczorynce: Smerfy, Gumisie, Disney", "Kacze opowieści", "Wielka burza w głowie Bubby (odc. 77, stary dubbing)", 1987, "full"),
    ("KVQeQ8fYoC8", "Ameryka w Wieczorynce: Smerfy, Gumisie, Disney", "Kacze opowieści", "5 minut odcinka (Disney Channel PL)", 1987, "fragment"),
]

FRAG_HINTS = ["czołówka", "czolowka", "intro", "outro", "piosenka", "theme",
              "scena", "scenka", "promo", "trailer", "zwiastun", "opening", "tekst"]


def clean_title(title, artist):
    t = title or ""
    t = re.sub(r"\s*-\s*SERIA:.*$", "", t, flags=re.I)
    t = t.split("|")[0].strip()
    t = re.sub(r"^Seria:.*?odcinek:\s*", "", t, flags=re.I)
    t = re.sub(r"\s*,?\s*Q=\d+p\]?", "]", t)
    t = re.sub(r"\s*\[\]\s*$", "", t)
    t = re.sub(r"\s*-?\s*full episode.*$", "", t, flags=re.I)
    t = re.sub(r"\s*-\s*YouTube\.\w+$", "", t, flags=re.I)
    t = re.sub(r"^\d+\.\s*", "", t)
    # zdejmij powtórzony tytuł serialu z początku
    for pref in (artist, artist.split(" (")[0]):
        if len(pref) > 4 and norm(t).startswith(norm(pref)):
            stripped = t[len(pref):].lstrip(" -–—:.•")
            if len(stripped) > 3:
                t = stripped
            break
    t = re.sub(r"\s{2,}", " ", t).strip(" -–—")
    return t or title


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
         "%(duration)s|%(view_count)s|%(channel)s",
         f"https://www.youtube.com/watch?v={vid}"],
        capture_output=True, text=True, timeout=60)
    line = (out.stdout or "").strip().splitlines()
    if not line:
        return vid, None
    dur, views, channel = (line[0].split("|", 2) + ["", "", ""])[:3]
    return vid, {"duration_seconds": int(dur) if dur.isdigit() else 0,
                 "views": int(views) if views.isdigit() else 0, "channel": channel}


def dur_str(d):
    return f"{d//3600}:{d%3600//60:02d}:{d%60:02d}" if d >= 3600 else f"{d//60}:{d%60:02d}"


def main():
    src = os.path.join(ROOT, "results", "final-01.jsonl")
    shutil.copy(src, os.path.join(ROOT, "results", "curated.bak"))
    curated = [json.loads(l) for l in open(src, encoding="utf-8") if l.strip()]
    seen = {r["id"] for r in curated}
    sec_of = {}
    for r in curated:
        sec_of.setdefault(r["artist"], r["section"])

    added = []
    for l in open(os.path.join(ROOT, "results", "series.jsonl"), encoding="utf-8"):
        s = json.loads(l)
        artist = s["artist"]
        rules = RULES.get(artist)
        if not rules:
            continue
        for e in s["episodes"]:
            if e["id"] in seen:
                continue
            tl = (e["title"] or "").lower()
            cn = norm(e["channel"])
            hay = tl + " " + cn
            if any(b in hay for b in rules["ban"]):
                continue
            if not (any(p in tl for p in rules["t"]) or any(p in cn for p in rules["c"])):
                continue
            seen.add(e["id"])
            d = e["duration_seconds"]
            typ = "fragment" if (d and d < 180) or any(w in tl for w in FRAG_HINTS) else "full"
            ym = re.search(r"\((19\d\d)\)", e["title"] or "")
            added.append({
                "section": s["section"], "artist": artist,
                "film": clean_title(e["title"], artist),
                "year": int(ym.group(1)) if ym else None,
                "type": typ, "id": e["id"], "duration": e["duration"],
                "duration_seconds": d, "views": e["views"], "channel": e["channel"],
            })

    with ThreadPoolExecutor(8) as ex:
        metas = dict(ex.map(fetch_meta, [m[0] for m in MANUAL2 if m[0] not in seen]))
    for vid, section, artist, film, year, typ in MANUAL2:
        if vid in seen:
            continue
        m = metas.get(vid)
        if not m:
            print(f"POMIJAM (brak metadanych): {artist} — {film} ({vid})")
            continue
        seen.add(vid)
        added.append({"section": section, "artist": artist, "film": film, "year": year,
                      "type": typ, "id": vid, "duration": dur_str(m["duration_seconds"]),
                      "duration_seconds": m["duration_seconds"], "views": m["views"],
                      "channel": m["channel"]})

    # sortowanie odcinków w obrębie serialu: numer odcinka, potem rok, potem popularność
    all_rows = curated + added
    by_series = {}
    for r in all_rows:
        by_series.setdefault((r["section"], r["artist"]), []).append(r)
    out = []
    for key in by_series:
        eps = by_series[key]
        def k(r):
            n = ep_num(r["film"])
            return (0 if n is not None else 1, n if n is not None else 0,
                    r["year"] or 9999, -(r["views"] or 0))
        eps.sort(key=k)
        dropped = len(eps) - MAX_EPS
        if dropped > 0:
            print(f"LIMIT {MAX_EPS}: {key[1]} — obcięto {dropped}")
        out.extend(eps[:MAX_EPS])

    with open(src, "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    n_series = len(by_series)
    print(f"final-01.jsonl: {len(out)} odcinków, {n_series} seriali (dodano {len(added)})")


if __name__ == "__main__":
    main()
