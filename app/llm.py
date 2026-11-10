"""Zugriff auf das Sprachmodell über die HTTP-Schnittstelle von Ollama (lokal, offenes Modell).

Austauschbar: Jeder Dienst mit derselben Schnittstelle (etwa ein Modell bei einem Anbieter in der EU hinter einem
kompatiblen Proxy) kann über OLLAMA_URL eingesetzt werden. Es gibt keinen Aufruf außerhalb dieser Datei.
"""
import json
import time

import httpx


class Sprachmodell:
    def __init__(self, url: str, modell: str, einbettung: str, zeitlimit: float = 180):
        self.url, self.modell, self.einbettungsmodell = url.rstrip("/"), modell, einbettung
        self.client = httpx.Client(timeout=zeitlimit)

    def json_antwort(self, system: str, nutzer: str, schema: dict) -> tuple[dict, float]:
        """Antwort im vorgegebenen JSON-Schema (strukturierte Ausgabe), dazu die Dauer in Sekunden."""
        t = time.perf_counter()
        r = self.client.post(f"{self.url}/api/chat", json={
            "model": self.modell, "stream": False, "format": schema,
            "options": {"temperature": 0, "num_ctx": 8192},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": nutzer}]})
        r.raise_for_status()
        return json.loads(r.json()["message"]["content"]), time.perf_counter() - t

    def text_antwort(self, system: str, nutzer: str) -> tuple[str, float]:
        t = time.perf_counter()
        r = self.client.post(f"{self.url}/api/chat", json={
            "model": self.modell, "stream": False, "options": {"temperature": 0, "num_ctx": 8192},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": nutzer}]})
        r.raise_for_status()
        return r.json()["message"]["content"], time.perf_counter() - t

    def einbetten(self, texte: list[str]) -> list[list[float]]:
        r = self.client.post(f"{self.url}/api/embed", json={"model": self.einbettungsmodell, "input": texte})
        r.raise_for_status()
        return r.json()["embeddings"]
