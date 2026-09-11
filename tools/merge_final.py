#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scala raw.jsonl z ręcznymi korektami → results/final-01.jsonl."""
import json, os, subprocess
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# klucz: (artist, film) z lista.tsv
DROP = {
    ("Bolek i Lolek", "Wielka podróż Bolka i Lolka (fragmenty filmu kinowego)"),
    ("Pampalini łowca zwierząt", "Pampalini — zestaw odcinków"),
    ("Przygody Błękitnego Rycerzyka", "Przygody Błękitnego Rycerzyka — odcinek"),
    ("Miś Uszatek", "Zabawa w chowanego"),
    ("Miś Uszatek", "Pierwszy śnieg"),
    ("Miś Uszatek", "Miś Uszatek — zestaw odcinków"),
    ("Miś Uszatek", "Czołówka i piosenka końcowa"),
    ("Przygody Misia Colargola", "Colargol na Dzikim Zachodzie"),
    ("Zaczarowany ołówek", "Zaczarowany ołówek — zestaw odcinków"),
    ("Trzy misie", "Trzy misie — odcinek"),
    ("Plastusiowy pamiętnik", "Plastusiowy pamiętnik — odcinek"),
    ("Dziwne przygody Koziołka Matołka", "Koziołek Matołek — zestaw odcinków"),
    ("Wędrówki Pyzy", "Wędrówki Pyzy — odcinek"),
    ("Proszę słonia", "Proszę słonia — odcinek"),
    ("Pomysłowy Dobromir", "Pomysłowy Dobromir — odcinek"),
    ("Smerfy", "Smerfy — czołówka po polsku"),
}

# klucz → nadpisywane pola (film = faktyczny tytuł odcinka; czasem inne)
FIX = {
    ("Bolek i Lolek", "Wyścig po złote runo — Zawody łucznicze"): {"film": "Wakacyjne szlaki (Przygody Bolka i Lolka)", "year": 1977},
    ("Bolek i Lolek", "Bolek i Lolek wyruszają w świat — W puszczy afrykańskiej"): {"film": "Na tropach Yeti (Bolek i Lolek wyruszają w świat)", "year": 1970},
    ("Bolek i Lolek", "Bolek i Lolek na Dzikim Zachodzie"): {"film": "W Hiszpanii (Bolek i Lolek w Europie)", "year": 1985},
    ("Bolek i Lolek", "Olimpiada Bolka i Lolka"): {"film": "Morska wyprawa (Przygody Bolka i Lolka)", "year": 1977},
    ("Bolek i Lolek", "Bajki Bolka i Lolka"): {"film": "Prima aprilis (Przygody Bolka i Lolka)", "year": 1977},
    ("Reksio", "Reksio śpioch"): {"film": "Reksio sportowiec", "year": 1972},
    ("Reksio", "Reksio — zestaw odcinków"): {"film": "Reksio remontuje", "year": 1980},
    ("Porwanie Baltazara Gąbki", "Porwanie Baltazara Gąbki — odcinek"): {"film": "W zbójeckim obozie", "year": 1969},
    ("Porwanie Baltazara Gąbki", "Wyprawa profesora Gąbki"): {"film": "Przez kraj Deszczowców", "year": 1970},
    ("Marceli Szpak dziwi się światu", "Marceli Szpak dziwi się światu — odcinek"): {"film": "Wizyta w borsuczej jamie (odc. 1)"},
    ("Zaczarowany ołówek", "Zaczarowany ołówek — odcinek 1"): {"film": "Worek prezentów"},
    ("Opowiadania Muminków", "Opowiadania Muminków (lalkowe) — odcinek"): {"film": "Czołówka (serial lalkowy Se-ma-for)", "type": "fragment"},
    ("Opowiadania Muminków", "Muminki lalkowe — zestaw odcinków"): {
        "section": "Europa Zachodnia i koprodukcje lat 90.", "artist": "Muminki (1990)",
        "film": "Wiosna w Dolinie Muminków (odc. 1)", "year": 1990},
    ("Mały pingwin Pik-Pok", "Mały pingwin Pik-Pok — odcinek"): {"film": "Mały Eskimos (odc. 22)"},
    ("Dziwne przygody Koziołka Matołka", "Koziołek Matołek — odcinek"): {"film": "Rajd"},
    ("Przygody kota Filemona", "Dziwny świat kota Filemona — odcinek"): {"film": "Nazywam się Filemon (odc. 1)"},
    ("Przygody kota Filemona", "Przygody kota Filemona — odcinek"): {"film": "Gwiazdka"},
    ("Przygód kilka wróbla Ćwirka", "Wróbel Ćwirek — odcinek"): {"film": "Własne gniazdko (odc. 1)"},
    ("Maurycy i Hawranek", "Maurycy i Hawranek — odcinek"): {"film": "Szalony ryś (odc. 4)"},
    ("Fortele Jonatana Koota", "Fortele Jonatana Koota — odcinek"): {"film": "Glac Plac (odc. 1)"},
    ("Krecik", "Krecik — zestaw odcinków"): {"film": "Krecik malarzem"},
    ("Rozbójnik Rumcajs", "Rumcajs — odcinek"): {"film": "Jak Rumcajs podarował Mance słoneczny pierścień (CZ)"},
    ("Rozbójnik Rumcajs", "Rumcajs po polsku — odcinek"): {"film": "Jak Rumcajs wypędził suma ze stawu"},
    ("Sąsiedzi (Pat i Mat)", "Pat i Mat — Tapetowanie"): {"film": "Tapety"},
    ("Sąsiedzi (Pat i Mat)", "Pat i Mat — zestaw odcinków"): {"film": "Bujane krzesło (odc. 5)"},
    ("Żwirek i Muchomorek", "Żwirek i Muchomorek — odcinek po polsku"): {"film": "O złej kunie i dobrej myszce"},
    ("Żwirek i Muchomorek", "Pohádky z mechu a kapradí — odcinek"): {"film": "Bajki z mchu i paproci — zestaw odcinków (CZ)"},
    ("Makowa panienka", "Makowa panienka — odcinek"): {"film": "Makowa panienka i Kleks"},
    ("Bob i Bobek", "Bob a Bobek — króliki z kapelusza"): {"film": "W restauracji (odc. 17)"},
    ("Wilk i Zając (Nu, pogodi!)", "Wilk i Zając — odcinek 1 (plaża)"): {"film": "Odcinek 1 — na plaży"},
    ("Wilk i Zając (Nu, pogodi!)", "Wilk i Zając — wesołe miasteczko"): {"film": "Odcinek 16"},
    ("Wilk i Zając (Nu, pogodi!)", "Wilk i Zając — zestaw odcinków"): {"film": "Zestaw odcinków po polsku"},
    ("Piaskowy Dziadek", "Unser Sandmännchen — odcinek"): {"film": "Gdzie mieszka Piaskowy Dziadek? (DE)"},
    ("Piaskowy Dziadek", "Piaskowy Dziadek — czołówka"): {"film": "Czołówka i zakończenie (NRD)"},
    ("Pszczółka Maja", "Pszczółka Maja (1975) — odcinek po polsku"): {"film": "Spotkanie z Burczymuchą (odc. 5)"},
    ("Pszczółka Maja", "Die Biene Maja — Maja wird geboren"): {"film": "Narodziny Mai (odc. 1, DE)"},
    ("Gustaw", "Gustaw (Gusztáv) — odcinek"): {"film": "Gustaw zaprowadza porządek"},
    ("Pająk chwat wszystkich brat", "Pająk chwat wszystkich brat (Vízipók-csodapók) — odcinek"): {"film": "Odcinek odnowiony cyfrowo (HU)"},
    ("Pom Pom", "Pom Pom meséi — odcinek"): {"film": "Artur Gombóc i czekolada (fragment)", "type": "fragment"},
    ("Kot Miau (Frakk)", "Frakk, a macskák réme — odcinek"): {"artist": "Frakk, postrach kotów", "film": "Frakk i leniwe koty (HU)"},
    ("Smerfy", "Smerfy — pełny odcinek"): {"film": "The Smurfette (odcinek, EN)"},
    ("Smerfy", "Smerfy — odcinek po polsku"): {"film": "Arcydzieło Małego Smerfa"},
    ("Gumisie", "Adventures of the Gummi Bears — odcinek"): {"film": "Gummi Bears — odcinek 34 (EN)"},
    ("Kacze opowieści", "DuckTales — pełny odcinek"): {"film": "Don't Give Up the Ship (odc. 1, EN)"},
    ("Miś Yogi", "Miś Yogi — odcinek"): {"film": "Yogi Bear — odcinek (EN)"},
    ("Muminki (1990)", "Muminki — odcinek po polsku"): {"film": "Ryjek wszystkim pomaga (odc. 93)"},
    ("Muminki (1990)", "Moomin — odcinek"): {"film": "Moominvalley in Spring (odc. 1, EN)"},
    ("Bouli", "Bouli — odcinek po polsku"): {"film": "Czołówka po polsku", "type": "fragment"},
    ("Pingu", "Pingu — odcinek"): {"film": "Pingu — odcinek 1"},
    ("Pingu", "Pingu — zestaw odcinków"): {"film": "Najlepsze odcinki sezonu 1"},
    ("Tabaluga", "Tabaluga — odcinek po polsku"): {"film": "Gdzie jest zima? (odc. 65)"},
    ("Wicky Wiking", "Wickie — odcinek"): {"film": "Straszny Sven (odc. 5, DE)"},
    ("SimsalaGrimm", "SimsalaGrimm — odcinek po polsku"): {"film": "Brat i siostra"},
}

# ręcznie wybrane filmy: (id, section, artist, film, year, type)
MANUAL = [
    ("Ya2z8K_y-Mc", "Bielsko-Biała: Bolek i Lolek, Reksio", "Bolek i Lolek", "Bolek i Lolek na Dzikim Zachodzie (film kinowy)", 1986, "full"),
    ("hTy_JCVcJwk", "Bielsko-Biała: Bolek i Lolek, Reksio", "Przygody Błękitnego Rycerzyka", "Bitwa z osami (fragment)", 1980, "fragment"),
    ("1Du1W6kM734", "Bielsko-Biała: Bolek i Lolek, Reksio", "Miś Kudłatek", "Nad morzem", 1973, "full"),
    ("26apTOYNtUA", "Se-ma-for: Miś Uszatek i dobranocki z Łodzi", "Miś Uszatek", "Wycieczka — scena z odc. 6", 1977, "fragment"),
    ("mlS1A-hebMs", "Se-ma-for: Miś Uszatek i dobranocki z Łodzi", "Miś Uszatek", "Czołówka (wersje językowe)", 1975, "fragment"),
    ("RDfo-O0NNcA", "Se-ma-for: Miś Uszatek i dobranocki z Łodzi", "Przygody Misia Colargola", "Zimowe kłopoty", 1969, "full"),
    ("VdYcDsxLnlU", "Se-ma-for: Miś Uszatek i dobranocki z Łodzi", "Zaczarowany ołówek", "Podwodny skarb (odc. 15)", 1970, "full"),
    ("FQqiDS6WP7c", "Studio Miniatur Filmowych: dobranocki z Warszawy", "Wędrówki Pyzy", "Siedem koników", 1977, "full"),
    ("z0CLwp_EKZg", "Studio Miniatur Filmowych: dobranocki z Warszawy", "Proszę słonia", "Dominik na dworcu (fragment)", 1978, "fragment"),
    ("Lxw3bLzSEa4", "Studio Miniatur Filmowych: dobranocki z Warszawy", "Pomysłowy Dobromir", "Czołówka", 1973, "fragment"),
    ("Zjpt8Qkjoio", "Studio Miniatur Filmowych: dobranocki z Warszawy", "Pomysłowy Dobromir", "Pomysłowy wnuczek — Grzybobranie", 1983, "full"),
    ("U8qG-HJHIIM", "ZSRR: Wilk i Zając, Kiwaczek, kot Leopold", "Trójka z Prostokwaszyna", "Trójka z Prostokwaszyna", 1978, "full"),
    ("BF6TjdsfV_M", "ZSRR: Wilk i Zając, Kiwaczek, kot Leopold", "Trójka z Prostokwaszyna", "Prostokwaszyno — wszystkie części", 1980, "full"),
    ("BQmGXzNMw0E", "ZSRR: Wilk i Zając, Kiwaczek, kot Leopold", "Kubuś Puchatek (Winnie Puch)", "Winni Puch — wszystkie części", 1969, "full"),
    ("CErf41K1tTI", "ZSRR: Wilk i Zając, Kiwaczek, kot Leopold", "Przygody kota Leopolda", "Zemsta kota Leopolda (odc. 1)", 1975, "full"),
    ("4iDyvGJt1TQ", "Czechosłowacja: Krecik, Rumcajs, Sąsiedzi", "O wróżce Amałce", "Jak siedziała w zielonej klatce (odc. 4)", 1973, "full"),
    ("5j05q2LV4OY", "Czechosłowacja: Krecik, Rumcajs, Sąsiedzi", "O wróżce Amałce", "Wróżka Amałka — komplet", 1973, "full"),
    ("XWsX7TgDeoU", "Ameryka w Wieczorynce: Smerfy, Gumisie, Disney", "Smerfy", "Czołówka po polsku", 1987, "fragment"),
]


def fetch_meta(vid):
    out = subprocess.run(
        ["yt-dlp", "--no-warnings", "--ignore-no-formats-error",
         "--extractor-args", "youtube:player_client=web_safari", "--print",
         "%(duration)s|%(view_count)s|%(channel)s|%(title)s",
         f"https://www.youtube.com/watch?v={vid}"],
        capture_output=True, text=True, timeout=60)
    line = (out.stdout or "").strip().splitlines()
    if not line:
        return vid, None
    dur, views, channel, title = (line[0].split("|", 3) + ["", "", "", ""])[:4]
    return vid, {"duration_seconds": int(dur) if dur.isdigit() else 0,
                 "views": int(views) if views.isdigit() else 0,
                 "channel": channel, "title": title}


def main():
    rows = []
    for l in open(os.path.join(ROOT, "results", "raw.jsonl"), encoding="utf-8"):
        r = json.loads(l)
        p = r.get("pick")
        if not p:
            continue
        key = (r["artist"], r["film"])
        if key in DROP:
            continue
        rec = {"section": r["section"], "artist": r["artist"], "film": r["film"],
               "year": r["year"], "type": r["type"], "id": p["id"],
               "duration": p["duration"], "duration_seconds": p["duration_seconds"],
               "views": p["views"], "channel": p["channel"]}
        rec.update(FIX.get(key, {}))
        rows.append(rec)

    with ThreadPoolExecutor(8) as ex:
        metas = dict(ex.map(fetch_meta, [m[0] for m in MANUAL]))
    for vid, section, artist, film, year, typ in MANUAL:
        m = metas.get(vid)
        if not m:
            print(f"POMIJAM (brak metadanych): {artist} — {film} ({vid})")
            continue
        d = m["duration_seconds"]
        rows.append({"section": section, "artist": artist, "film": film, "year": year,
                     "type": typ, "id": vid,
                     "duration": f"{d//3600}:{d%3600//60:02d}:{d%60:02d}" if d >= 3600 else f"{d//60}:{d%60:02d}",
                     "duration_seconds": d, "views": m["views"], "channel": m["channel"]})

    outp = os.path.join(ROOT, "results", "final-01.jsonl")
    with open(outp, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"final-01.jsonl: {len(rows)} pozycji")


if __name__ == "__main__":
    main()
