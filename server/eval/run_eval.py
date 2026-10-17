"""Évalue le prof sur les 30 questions de questions.jsonl.

  python run_eval.py https://5-39-119-109.sslip.io            (serveur avec DEV_LOGIN=true)
  python run_eval.py http://localhost:8000 --out rapport.md

Pour chaque question : réponse, temps, contrôles automatiques
(mots attendus présents, refus si hors sujet, kabyle non vérifié signalé
par le serveur), et une colonne « Note » (0, 1 ou 2) à remplir à la main :
  2 = correct et pédagogique · 1 = utilisable avec réserves · 0 = faux, inventé ou hors cadre.
Chaque question part d'un nouveau compte de test, pour qu'elles soient indépendantes.
"""
import argparse
import json
import time
import unicodedata
import uuid
from pathlib import Path

import httpx

REFUSAL_HINTS = ("uniquement", "seulement", "que du kabyle", "ne peux pas", "je ne fais pas",
                 "langue, sa culture", "revenir à la leçon", "on reprend")


def norm(s: str) -> str:
    return unicodedata.normalize("NFC", s).lower()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("base_url")
    ap.add_argument("--out", default="/tmp/rapport_eval.md")
    ap.add_argument("--questions", default=str(Path(__file__).with_name("questions.jsonl")))
    a = ap.parse_args()
    qs = [json.loads(l) for l in open(a.questions, encoding="utf-8") if l.strip()]
    rows = []
    with httpx.Client(base_url=a.base_url.rstrip("/"), timeout=180) as c:
        for q in qs:
            tok = c.post("/auth/dev", json={"name": "Eval", "device_id": f"eval-{uuid.uuid4().hex[:10]}",
                                            "interface_language": "fr"}).json()["access_token"]
            t0 = time.time()
            body = {"message": q["message"], "tz_offset_minutes": 60}
            if q.get("intent"):
                body["intent"] = q["intent"]
            r = c.post("/tutor/chat", json=body, headers={"Authorization": f"Bearer {tok}"})
            dt = time.time() - t0
            res = r.json() if r.status_code == 200 else {"reply": f"ERREUR {r.status_code}: {r.text[:200]}"}
            reply = res.get("reply", "")
            expect = q.get("expect_any", [])
            found = [e for e in expect if norm(e) in norm(reply)]
            checks = []
            if expect:
                checks.append(f"attendu {len(found)}/{len(expect)}")
            if q.get("must_refuse"):
                refused = res.get("off_topic") or any(h in norm(reply) for h in REFUSAL_HINTS)
                checks.append("refus OK" if refused else "PAS DE REFUS")
            if res.get("unverified"):
                checks.append("kabyle non vérifié : " + ", ".join(res["unverified"]))
            if res.get("blocks"):
                checks.append("cartes : " + ", ".join(b.get("type", "?") for b in res["blocks"]))
            rows.append((q, reply, dt, checks))
            print(f"{q['id']} {dt:5.1f}s  {' | '.join(checks)}")
    lines = ["# Évaluation du prof Amusnaw", "",
             f"Serveur : {a.base_url} · {time.strftime('%Y-%m-%d %H:%M')} · {len(rows)} questions", "",
             "Note à remplir : 2 = correct et pédagogique · 1 = utilisable avec réserves · 0 = faux, inventé ou hors cadre.", ""]
    times = [dt for _, _, dt, _ in rows]
    lines += [f"Temps moyen de réponse : {sum(times) / max(len(times), 1):.1f} s (max {max(times or [0]):.1f} s)", ""]
    for q, reply, dt, checks in rows:
        lines += [f"## {q['id']} · {q['cat']} — {q['message']}", "",
                  f"**À vérifier :** {q['check']}", "",
                  f"**Réponse ({dt:.1f} s) :**", "", "> " + reply.replace("\n", "\n> "), "",
                  f"**Contrôles automatiques :** {' · '.join(checks) or '—'}", "",
                  "**Note (0/1/2) :** ___   **Commentaire :** ___", ""]
    Path(a.out).write_text("\n".join(lines), encoding="utf-8")
    print(f"\nRapport : {a.out}")


if __name__ == "__main__":
    main()
