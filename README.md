# LEGENDARNE DOBRANOCKI · 1980–2000

Portal streamingowy legendarnych dobranocek polskiej telewizji: **322 zweryfikowane odcinki 53 seriali w 9 rozdziałach** — od Bolka i Lolka, Reksia i Misia Uszatka, przez Krecika, Rumcajsa i Wilka z Zającem, po Smerfy, Gumisie i Muminki.

**LIVE:** https://futureshow1.github.io/futureshow/projects/dobranocki/

Trzeci portal z rodziny filmowej FutureShow — obok [Historii Animacji](https://futureshow1.github.io/futureshow/projects/historia-animacji/) i [Kina Awangardy](https://futureshow1.github.io/futureshow/projects/awangarda-kino-portal/).

## Funkcje

- **Karta = serial, nie odcinek.** Każda dobranocka to zestaw odcinków z możliwie oficjalnych kanałów (Studio Filmów Rysunkowych, Sojuzmultfilm, czeski Bonton, „Smerfy • Po Polsku", rbb Sandmännchen…).
- **▶ Oglądaj ciągiem** — playlista YouTube odtwarza cały zestaw sekwencyjnie, jak dawne wieczorne pasmo TVP; można też wybierać odcinki pojedynczo. Odcinki bez zgody na osadzanie (↗) otwierają się na YouTube.
- **Nocne niebo na dobranoc** — mrugające i dryfujące gwiazdy, spadające gwiazdy, kołyszący się księżyc z pulsującą poświatą; w trybie dziennym księżyc zamienia się w słońce z koroną promieni, a po niebie suną obłoki. Tytuł rozpływa się i wyłania w usypiającym rytmie (bez migotania — strona do wyciszania dzieci). Szanuje `prefers-reduced-motion`.
- **Dwujęzyczność PL/EN**, tryb ciemny/jasny, wyszukiwarka, filtry (całe odcinki / czołówki i fragmenty), spis rozdziałów ze scroll-spy.
- Single-file HTML + `data.js` — zero zależności poza Google Fonts i osadzeniami YouTube (`youtube-nocookie.com`).

## Rozdziały

1. Bielsko-Biała: Bolek i Lolek, Reksio (SFR)
2. Se-ma-for: Miś Uszatek i dobranocki z Łodzi
3. Studio Miniatur Filmowych: dobranocki z Warszawy
4. Czechosłowacja: Krecik, Rumcajs, Sąsiedzi
5. ZSRR: Wilk i Zając, Kiwaczek, kot Leopold
6. NRD i RFN: Piaskowy Dziadek i Pszczółka Maja
7. Węgry: Gustaw i Wodnik Szuwarek
8. Ameryka w Wieczorynce: Smerfy, Gumisie, Disney
9. Europa Zachodnia i koprodukcje lat 90.

## Pipeline danych (`tools/`)

Kuratorowana lista → wyszukiwanie i scoring → ręczne korekty → weryfikacja dostępności → `data.js`:

```
lista.tsv / series.tsv          # kuratorowane listy (serial, zapytania, limity czasu)
search_yt.py / search_series.py # wyszukiwanie yt-dlp + scoring (kanały oficjalne, anty-śmieci)
merge_final.py / merge_series.py / add_polish.py   # scalanie, reguły per serial, ręczne dodatki
check_embed.py                  # dostępność + osadzalność każdego wideo
build_data.py                   # final-*.jsonl → data.js
```

Uwagi praktyczne:
- yt-dlp ≥ 2026.03 przy filmach z wyłączonym osadzaniem wymaga `--ignore-no-formats-error --extractor-args "youtube:player_client=web_safari"` — inaczej fałszywie zgłasza „not available".
- Scoring oparty na ASCII nie radzi sobie z cyrylicą i węgierskim — te seriale dobierane ręcznie.
- Klasyczny Miś Uszatek istnieje legalnie na YT tylko jako sceny TVP VOD; krążące „Nowe przygody Misia Uszatka" to podróbki generowane AI (odrzucone).

## Uruchomienie lokalne

```
python3 -m http.server 8163
# → http://localhost:8163
```

---

Dobranocka: pasmo Telewizji Polskiej nadawane codziennie ok. 19.00 (od lat 90. jako Wieczorynka). Portal obejmuje seriale emitowane w paśmie w latach 1980–2000, także wyprodukowane wcześniej. Dostępność filmów zależy od publikujących kanałów.
