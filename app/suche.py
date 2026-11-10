"""Abruf passender Lastenheft-Absätze zu einer Eingabe: Einbettungen (bge-m3) und Kosinus-Ähnlichkeit.

Das Modell selbst ist klein und geht als Übersicht vollständig in den Kontext; abgerufen werden die Absätze der
Wissensquellen. Die Einbettungen werden einmal je Quellenstand berechnet und zwischengespeichert.
"""
import hashlib
import json
import math
from pathlib import Path

from .wissen import Quelle


def _einheit(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


class Index:
    def __init__(self, quellen: list[Quelle], llm, cache: Path):
        self.quellen, self.llm = quellen, llm
        schluessel = hashlib.sha256((llm.einbettungsmodell + "".join(q.id + q.text for q in quellen)).encode()).hexdigest()
        if cache.exists() and json.loads(cache.read_text()).get("schluessel") == schluessel:
            self.vektoren = json.loads(cache.read_text())["vektoren"]
        else:
            self.vektoren = [_einheit(v) for v in llm.einbetten([f"{q.id}: {q.text}" for q in quellen])]
            cache.write_text(json.dumps({"schluessel": schluessel, "vektoren": self.vektoren}))

    def suchen(self, text: str, k: int = 6) -> list[tuple[Quelle, float]]:
        q = _einheit(self.llm.einbetten([text])[0])
        werte = [sum(a * b for a, b in zip(q, v)) for v in self.vektoren]
        reihe = sorted(range(len(werte)), key=lambda i: -werte[i])[:k]
        return [(self.quellen[i], round(werte[i], 4)) for i in reihe]
