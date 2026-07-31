#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sprawdza dostępność i osadzalność wybranych filmów.
Wejście: JSONL z polem "id" (linie z pick=null są pomijane, obsługuje też format final-*.jsonl).
Wyjście: JSONL id -> {playable_in_embed, availability, age_limit, ok}
Użycie: python3 check_embed.py merged.jsonl embed_report.jsonl [--workers 8]
"""
import json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor, as_completed


def check(vid):
    try:
        out = subprocess.run(
            ["yt-dlp", "--no-warnings", "--ignore-no-formats-error",
             "--extractor-args", "youtube:player_client=web_safari", "--print",
             "%(playable_in_embed)s|%(availability)s|%(age_limit)s",
             f"https://www.youtube.com/watch?v={vid}"],
            capture_output=True, text=True, timeout=60,
        )
        line = (out.stdout or "").strip().splitlines()
        if not line:
            return {"id": vid, "ok": False, "error": (out.stderr or "").strip()[-200:]}
        emb, avail, age = (line[0].split("|") + ["", "", ""])[:3]
        return {
            "id": vid,
            "playable_in_embed": emb == "True",
            "availability": avail,
            "age_limit": int(age) if age.isdigit() else 0,
            "ok": avail in ("public", "unlisted") ,
        }
    except Exception as ex:
        return {"id": vid, "ok": False, "error": str(ex)[:200]}


def main():
    inp, outp = sys.argv[1], sys.argv[2]
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 8
    ids = []
    seen = set()
    with open(inp, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            vid = r.get("id") or (r.get("pick") or {}).get("id")
            if vid and vid not in seen:
                seen.add(vid)
                ids.append(vid)
    results = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(check, v): v for v in ids}
        done = 0
        for f in as_completed(futs):
            r = f.result()
            results.append(r)
            done += 1
            flag = "OK" if r.get("ok") else "!!"
            emb = "embed" if r.get("playable_in_embed") else "NOEMBED"
            print(f"[{done}/{len(ids)}] {flag} {emb} {r['id']}", file=sys.stderr)
    with open(outp, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    bad = sum(1 for r in results if not r.get("ok"))
    noemb = sum(1 for r in results if r.get("ok") and not r.get("playable_in_embed"))
    print(f"GOTOWE: {len(results)} sprawdzonych, {bad} niedostępnych, {noemb} bez embedu", file=sys.stderr)


if __name__ == "__main__":
    main()
