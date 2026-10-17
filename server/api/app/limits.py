"""Limites simples en mémoire (un seul processus API) : un site public ne doit pas
pouvoir saturer le modèle, qui tourne sur le processeur du VPS."""
import time
from collections import defaultdict, deque

from fastapi import HTTPException


class RateLimit:
    def __init__(self, n: int, seconds: int, message: str):
        self.n, self.seconds, self.message = n, seconds, message
        self._hits: dict[str, deque] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = time.monotonic()
        q = self._hits[key]
        while q and now - q[0] > self.seconds:
            q.popleft()
        if len(q) >= self.n:
            raise HTTPException(429, self.message)
        q.append(now)
        if len(self._hits) > 50_000:  # ménage
            for k in [k for k, v in self._hits.items() if not v or now - v[-1] > self.seconds][:10_000]:
                del self._hits[k]


# 60 messages par heure et par élève ; 10 nouveaux comptes sans compte par heure et par adresse IP
chat_limit = RateLimit(60, 3600, "Tu as beaucoup écrit cette heure-ci : fais une petite pause, ton prof t'attend ensuite.")
signup_limit = RateLimit(10, 3600, "Trop de comptes créés depuis cette connexion. Réessaie plus tard.")
