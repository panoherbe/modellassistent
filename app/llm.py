"""Zugriff auf das Sprachmodell über die HTTP-Schnittstelle von Ollama (lokal, offenes Modell).

Austauschbar: Jeder Dienst mit derselben Schnittstelle (etwa ein Modell bei einem Anbieter in der EU hinter einem
kompatiblen Proxy) kann über OLLAMA_URL eingesetzt werden. Es gibt keinen Aufruf außerhalb dieser Datei.
"""
import json
import time

import httpx


class Sprachmodell:
    def __init__(self, url: str, modell: str, einbettung: str, zeitlimit: float = 600, denken: bool = False,
                 einbettung_cpu: bool = False):
        self.url, self.modell, self.einbettungsmodell = url.rstrip("/"), modell, einbettung
        self.denken = denken  # Denkmodus der Qwen3-Modelle: aus = schneller, an = gründlicher (gemessen in nachweis/)
        # Einbettung auf dem Prozessor: Füllt ein großes Sprachmodell den Grafikspeicher, bricht sie sonst ab (CUDA out of memory)
        self.einbettung_cpu = einbettung_cpu
        self.client = httpx.Client(timeout=zeitlimit)
        self.zaehler = {"aufrufe": 0, "ausgabe_tokens": 0, "ausgabe_s": 0.0}

    def _chat(self, system: str, nutzer: str, **extra) -> str:
        r = self.client.post(f"{self.url}/api/chat", json={
            "model": self.modell, "stream": False, "think": self.denken,
            "options": {"temperature": 0, "num_ctx": 8192}, **extra,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": nutzer}]})
        r.raise_for_status()
        d = r.json()
        self.zaehler["aufrufe"] += 1
        self.zaehler["ausgabe_tokens"] += d.get("eval_count", 0)
        self.zaehler["ausgabe_s"] += d.get("eval_duration", 0) / 1e9
        return d["message"]["content"]

    def json_antwort(self, system: str, nutzer: str, schema: dict) -> tuple[dict, float]:
        """Antwort im vorgegebenen JSON-Schema (strukturierte Ausgabe), dazu die Dauer in Sekunden."""
        t = time.perf_counter()
        return json.loads(self._chat(system, nutzer, format=schema)), time.perf_counter() - t

    def text_antwort(self, system: str, nutzer: str) -> tuple[str, float]:
        t = time.perf_counter()
        return self._chat(system, nutzer), time.perf_counter() - t

    def einbetten(self, texte: list[str]) -> list[list[float]]:
        r = self.client.post(f"{self.url}/api/embed", json={"model": self.einbettungsmodell, "input": texte,
                                                            **({"options": {"num_gpu": 0}} if self.einbettung_cpu else {})})
        r.raise_for_status()
        return r.json()["embeddings"]
