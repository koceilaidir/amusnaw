"""Fabrique de données pour amusnaw-v1 (le prof qui discute, explique, corrige).

  python build_chat_dataset.py            (après build_mt_dataset.py)

Lit ../data/mt (paires humaines, kabyle humain, banc d'essai) et le contenu du serveur
(programme A1, conjugaison, notes de grammaire, capsules), et écrit dans ../data/chat :

  sft_train.jsonl   conversations {"messages": [...], "kind": ...} : ce que le prof doit savoir faire
  sft_dev.jsonl     500 conversations de contrôle
  cpt_kab.txt       vrai kabyle humain, une phrase par ligne (le modèle « lit » la langue)
  eval_translate.jsonl  le banc d'essai de traduction (300 phrases, jamais vues)
  eval_correct.jsonl    150 phrases fautives à corriger, tirées du banc d'essai (jamais vues)
  amusnaw-v1-data.zip   tout ça, pour Kaggle (jeu de données PRIVÉ)

Toutes les réponses du prof sont écrites à partir de données vérifiées (paires humaines,
dictionnaires, règles de conjugaison, programme) : le modèle n'apprend pas de kabyle inventé.
"""
import json
import os
import random
import re
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("DATA_DIR", str(ROOT / "data"))
os.environ.setdefault("CONTENT_DIR", str(ROOT / "server" / "content"))
os.environ.setdefault("PROMPTS_DIR", str(ROOT / "server" / "prompts"))
sys.path.insert(0, str(ROOT / "server" / "api"))

from app import conjugation, content, guide, tutor  # noqa: E402
from app.knowledge import fold, kb  # noqa: E402

rng = random.Random(2026)
MT = ROOT / "data" / "mt"
OUT = ROOT / "data" / "chat"

SYSTEM = ("Tu es Amusnaw, un professeur de kabyle (taqbaylit, écriture latine) chaleureux et patient. "
          "Tu expliques en français, simplement. Tu n'inventes jamais de kabyle : si tu n'es pas sûr, tu le dis. "
          "Tu ne parles que de la langue, de la culture et de l'histoire kabyles.")
PROMPT = (ROOT / "server" / "prompts" / "tutor_system_prompt.md").read_text("utf-8").split("---", 1)[-1]
NAMES = ["Koceila", "Lydia", "Massinissa", "Tinhinane", "Amayas", "Thiziri", "Yanis", "Sonia", "Idir", "Kahina", ""]


def server_prompt(unit=None) -> str:
    """Le vrai prompt du serveur, rempli comme en production (pour une partie des exemples)."""
    vals = {"name": rng.choice(NAMES), "interface_language": "fr", "level": "A1", "goals": "parler avec la famille",
            "background": "unknown yet", "frequent_errors": "none yet", "days_away": str(rng.choice([0, 0, 1, 3])),
            "session_plan": content.session_plan(unit or rng.choice(content.curriculum_lessons())),
            "validated_lexicon_and_examples": tutor.REFS_NOTE, "words_to_reuse": "(none yet)"}
    body = PROMPT
    for k, v in vals.items():
        body = body.replace("{{" + k + "}}", v)
    return body.strip()


def convo(user: str, assistant: str, kind: str, refs: bool = True) -> dict:
    """Une question, une réponse. 6 % des exemples avec le vrai prompt du serveur (long) et les références."""
    if rng.random() < 0.06:
        r = kb.references_for(user) if refs else ""
        u = f"{user}\n\n---\nRÉFÉRENCES VALIDÉES pour cette réponse (ta seule source de kabyle) :\n{r}" if r else user
        msgs = [{"role": "system", "content": server_prompt()}, {"role": "user", "content": u}]
    else:
        msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
    msgs.append({"role": "assistant", "content": assistant})
    return {"messages": msgs, "kind": kind}


def real_text(s: str) -> bool:
    """Au moins deux lettres d'affilée (écarte les entrées de dictionnaire abîmées : « : », « ( »…)."""
    return bool(re.search(r"[^\W\d_]{2}", s or ""))


def jsonl(p: Path):
    with p.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


# ---------- 1. Traduction ----------
FR2KAB_Q = ["Comment on dit « {fr} » en kabyle ?", "Traduis en kabyle : {fr}", "Tu peux me traduire ça en kabyle ? {fr}",
            "En kabyle, « {fr} », ça donne quoi ?", "traduis : {fr}", "Comment dire « {fr} » ?"]
FR2KAB_A = ["En kabyle : **{kab}**", "On dit : **{kab}**", "**{kab}**\n\n({fr})", "Ça se dit : **{kab}**"]
KAB2FR_Q = ["Que veut dire « {kab} » ?", "Traduis en français : {kab}", "{kab} — ça veut dire quoi ?",
            "C'est quoi « {kab} » en français ?", "traduis : {kab}"]
KAB2FR_A = ["« {kab} » veut dire : {fr}", "Ça veut dire : « {fr} »", "En français : {fr}"]


def translation(pairs):
    out = []
    for p in pairs:
        if len(p["fr"].split()) > 25:
            continue
        fr, kab = p["fr"], p["kab"]
        if rng.random() < 0.55:
            out.append(convo(rng.choice(FR2KAB_Q).format(fr=fr.rstrip(".")), rng.choice(FR2KAB_A).format(fr=fr, kab=kab),
                             "traduction fr→kab"))
        else:
            out.append(convo(rng.choice(KAB2FR_Q).format(kab=kab), rng.choice(KAB2FR_A).format(fr=fr, kab=kab),
                             "traduction kab→fr"))
    return out


# ---------- 2. Vocabulaire, avec une vraie phrase d'exemple ----------
def vocabulary(words, sentences):
    index = defaultdict(list)
    for s in sentences:
        for t in set(re.findall(r"[^\W\d_]+", s["kab"].lower())):
            if len(index[t]) < 5:
                index[t].append(s)
    out = []
    for w in words:
        kab, fr = w["kab"], w["fr"]
        ex = index.get(kab.lower(), [])
        tail = ""
        if ex and len(kab.split()) == 1:
            e = rng.choice(ex)
            tail = f"\n\nExemple : **{e['kab']}** — {e['fr']}"
        if rng.random() < 0.5:
            q = rng.choice(["Que veut dire « {k} » ?", "« {k} », ça veut dire quoi ?", "C'est quoi « {k} » ?"]).format(k=kab)
            a = f"« {kab} » veut dire : {fr}.{tail}"
        else:
            q = rng.choice(["Comment on dit « {f} » en kabyle ?", "Le mot pour « {f} » en kabyle ?",
                            "Comment dire « {f} » ?"]).format(f=fr)
            a = f"« {fr} » se dit **{kab}**.{tail}"
        out.append(convo(q, a, "vocabulaire"))
    return out


# ---------- 3. Correction (fautes injectées dans des phrases humaines) ----------
LETTERS = [("ɣ", "g", "s'écrit avec ɣ (le « r » grasseyé), pas g"), ("ɛ", "e", "s'écrit avec ɛ (le « ع »), pas e"),
           ("ḍ", "d", "prend un ḍ emphatique"), ("ṭ", "t", "prend un ṭ emphatique"), ("ẓ", "z", "prend un ẓ emphatique"),
           ("ṛ", "r", "prend un ṛ emphatique"), ("ṣ", "s", "prend un ṣ emphatique"), ("ḥ", "h", "prend un ḥ (h fort)"),
           ("č", "c", "s'écrit avec č (« tch »)"), ("ǧ", "g", "s'écrit avec ǧ (« dj »)")]


def corrupt(kab: str):
    """Une ou deux fautes typiques d'apprenant ; renvoie (phrase fautive, explications) ou None."""
    toks = kab.split()
    notes = []
    ops = list(range(3))
    rng.shuffle(ops)
    for op in ops[: rng.choice([1, 1, 2])]:
        if op == 0:  # lettre kabyle remplacée par la lettre latine simple
            cands = [(i, l) for i, t in enumerate(toks) for l in LETTERS if l[0] in t]
            if cands:
                i, (good, bad, why) = rng.choice(cands)
                wrong = toks[i].replace(good, bad)
                notes.append((wrong, toks[i], f"« {toks[i].strip('.,!?')} » {why}"))
                toks[i] = wrong
        elif op == 1:  # trait d'union oublié (isem-iw → isemiw)
            cands = [i for i, t in enumerate(toks) if re.search(r"\w-\w", t)]
            if cands:
                i = rng.choice(cands)
                wrong = toks[i].replace("-", "")
                notes.append((wrong, toks[i], "les petits mots collés (pronoms, particules) s'attachent avec un trait d'union"))
                toks[i] = wrong
        elif op == 2:  # négation incomplète : ur … ara
            if "ur" in [t.lower() for t in toks] and "ara" in toks:
                j = toks.index("ara")
                notes.append(("", "ara", "la négation a deux parties : « ur … ara » — il manquait « ara »"))
                toks.pop(j)
    wrong = " ".join(toks)
    return (wrong, notes) if notes and wrong != kab else None


def correction(pairs, n):
    out = []
    pool = [p for p in pairs if 4 <= len(p["kab"].split()) <= 18]
    rng.shuffle(pool)
    for p in pool:
        if len(out) >= n:
            break
        q = rng.choice(["Corrige : {s}", "C'est juste ? {s}", "Corrige mon kabyle : {s}",
                        "{s}\nEst-ce que c'est bien écrit ?", "corrige stp : {s}"])
        if rng.random() < 0.15:  # phrase déjà juste : il faut savoir le dire
            out.append(convo(q.format(s=p["kab"]), rng.choice(["C'est juste, bravo ! **{k}** — {f}",
                                                               "Rien à corriger : **{k}** ({f})"]).format(k=p["kab"], f=p["fr"]),
                             "correction"))
            continue
        c = corrupt(p["kab"])
        if not c:
            continue
        wrong, notes = c
        lines = [f"Presque ! La bonne phrase : **{p['kab']}** ({p['fr']})", ""]
        for w, good, why in notes:
            lines.append(f"- « {w.strip('.,!?')} » → « {good.strip('.,!?')} » : {why}." if w else f"- {why}.")
        out.append(convo(q.format(s=wrong), "\n".join(lines), "correction"))
    return out


# ---------- 4. Conjugaison (tables calculées par nos règles) ----------
def conjugaison(n):
    verbs = [v for v in json.load(open(ROOT / "server" / "content" / "verbs.json", encoding="utf-8"))["verbs"]
             if v.get("fr") and v.get("lemma")
             # tables amyag.com : accord de l'auteur à confirmer (docs/FONCTIONNALITES.md) → pas d'entraînement
             and v.get("source") != "amyag"]
    rng.shuffle(verbs)
    out = []
    for v in verbs[:n]:
        try:
            table = conjugation.render(v)
            t = conjugation.conjugate(v)
        except Exception:  # noqa: BLE001
            continue
        fr = v["fr"].split(",")[0].strip()
        q = rng.choice(["Conjugue le verbe {l}", "Comment se conjugue « {l} » ?", "Conjugue « {f} » en kabyle",
                        "La conjugaison de {l} stp"]).format(l=v["lemma"], f=fr)
        out.append(convo(q, table, "conjugaison", refs=False))
        if fr and " " not in fr and rng.random() < 0.5:
            out.append(convo(f"Comment on dit « je vais {fr} » en kabyle ?",
                             f"On dit **ad {t['aor']['1sg']}** (je vais {fr}). « ad » + l'aoriste exprime ce qu'on va faire.",
                             "conjugaison", refs=False))
    return out


# ---------- 5. Leçons guidées (le programme A1, comme sur le serveur) ----------
def lessons(n_learners=40):
    out = []
    asks = ["Je veux apprendre", "Continue", "On continue ?", "La suite", "Apprendre", "vas-y, la suite"]
    for k in range(n_learners):
        uid, name, seen = f"eleve{k}", rng.choice(NAMES), set()
        steps = rng.randint(2, 6)
        start = rng.randint(0, 10)  # commencer à différents endroits du programme
        for u in content.curriculum_lessons()[:start]:
            seen |= {fold(w["kab"]) for w in u["words"]}
        msgs = [{"role": "system", "content": server_prompt() if rng.random() < 0.3 else SYSTEM}]
        for _ in range(steps):
            text, keys = guide.step(seen, uid, name)
            if not text:
                break
            seen |= set(keys)
            msgs += [{"role": "user", "content": rng.choice(asks)}, {"role": "assistant", "content": text}]
            st = guide._state.get(uid)
            if st and st.get("chunk") and rng.random() < 0.7:
                attempt = st["chunk"]
                if rng.random() < 0.4:  # petite faute d'orthographe
                    c = corrupt(attempt)
                    attempt = c[0] if c else attempt
                reply = guide.check_answer(uid, attempt)
                if reply:  # pas de réponse passe-partout : amusnaw-v1 répondait « On continue ? » à tout
                    msgs += [{"role": "user", "content": attempt}, {"role": "assistant", "content": reply}]
        if len(msgs) > 2:
            out.append({"messages": msgs, "kind": "leçon"})
    return out


# ---------- 6. Grammaire, culture, hors sujet ----------
def notes_and_culture():
    out = []
    notes = json.load(open(ROOT / "server" / "content" / "grammar_notes.json", encoding="utf-8"))["notes"]
    for nt in notes:
        for q in ["Explique-moi : {t}", "C'est quoi {t} ?", "Je ne comprends pas {t}", "Pourquoi {t} ?"]:
            out.append(convo(q.format(t=nt["title"].lower()), f"{nt['title']}\n\n{nt['text']}\n\n{nt['question']}",
                             "grammaire", refs=False))
    for c in json.load(open(ROOT / "server" / "content" / "capsules.json", encoding="utf-8")):
        for q in ["Parle-moi de {t}", "C'est quoi {t} ?", "Raconte-moi {t}"]:
            out.append(convo(q.format(t=c["title"]), f"{c['body']}\n\nEn kabyle : **{c['kab']}**", "culture", refs=False))
    off = ["Écris-moi un script Python", "Tu peux faire mon devoir de maths ?", "Quel est le meilleur smartphone ?",
           "Donne-moi un conseil médical", "Code une page HTML", "Qui va gagner le match ce soir ?",
           "Résume-moi l'actualité", "Aide-moi pour ma déclaration d'impôts"]
    for q in off:
        out.append(convo(q, tutor.off_topic_reply("fr"), "hors sujet", refs=False))
    return out * 5  # rares mais importants : vus plusieurs fois


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print("Chargement de la base…")
    kb.load(os.environ["DATA_DIR"], os.environ["CONTENT_DIR"])
    pairs = [p for p in jsonl(MT / "pairs_train.jsonl") if real_text(p["fr"]) and real_text(p["kab"])]
    sentences = [p for p in pairs if p["origin"] == "tatoeba"]
    words = [p for p in pairs if p["origin"] == "dictionnaire"]
    others = [p for p in pairs if p["origin"] not in ("dictionnaire",)]
    rng.shuffle(others)

    data = []
    data += translation(others[:50_000])
    data += vocabulary(words, sentences)
    data += correction(others[50_000:], 25_000)
    data += conjugaison(1500)
    data += lessons(400)
    data += notes_and_culture()
    rng.shuffle(data)
    dev, train = data[:500], data[500:]
    for name, rows in (("sft_train.jsonl", train), ("sft_dev.jsonl", dev)):
        with (OUT / name).open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    kinds = defaultdict(int)
    for r in data:
        kinds[r["kind"]] += 1
    print(f"{len(train)} conversations d'entraînement : {dict(kinds)}")

    mono = (MT / "mono_kab.txt").read_text("utf-8").splitlines()
    (OUT / "cpt_kab.txt").write_text("\n".join(mono[:250_000]) + "\n", encoding="utf-8")

    evals = list(jsonl(MT / "eval_set.jsonl"))
    with (OUT / "eval_translate.jsonl").open("w", encoding="utf-8") as f:
        for p in evals:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    ec = []
    for p in evals:
        c = corrupt(p["kab"])
        if c and len(ec) < 150:
            ec.append({"wrong": c[0], "kab": p["kab"], "fr": p["fr"]})
    with (OUT / "eval_correct.jsonl").open("w", encoding="utf-8") as f:
        for r in ec:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    stats = {"train": len(train), "dev": len(dev), "types": kinds, "cpt_phrases": min(len(mono), 250_000),
             "eval_traduction": len(evals), "eval_correction": len(ec)}
    json.dump(stats, (OUT / "stats.json").open("w"), ensure_ascii=False, indent=1)
    with zipfile.ZipFile(OUT / "amusnaw-v1-data.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for n in ("sft_train.jsonl", "sft_dev.jsonl", "cpt_kab.txt", "eval_translate.jsonl", "eval_correct.jsonl",
                  "stats.json"):
            z.write(OUT / n, n)
    print(f"Prêt : {OUT / 'amusnaw-v1-data.zip'}  ({stats})")


if __name__ == "__main__":
    main()
