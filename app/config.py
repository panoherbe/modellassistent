"""Einstellungen aus Umgebungsvariablen. Keine Geheimnisse im Code."""
import os
from dataclasses import dataclass
from pathlib import Path

BASIS = Path(__file__).resolve().parent.parent
PROMPT_VERSION = "vorschlag-v4+klaerung-v2+zuordnung-v2"


@dataclass(frozen=True)
class Einstellungen:
    daten: Path
    ollama_url: str
    sprachmodell: str
    einbettungsmodell: str
    denken: bool
    einbettung_cpu: bool
    pruefer_url: str
    basismodell: Path
    wissen: Path


def laden() -> Einstellungen:
    daten = Path(os.environ.get("DATENVERZEICHNIS", BASIS / "daten"))
    daten.mkdir(parents=True, exist_ok=True)
    return Einstellungen(
        daten=daten,
        ollama_url=os.environ.get("OLLAMA_URL", "http://localhost:11434"),
        sprachmodell=os.environ.get("SPRACHMODELL", "qwen3.8:27b"),
        einbettungsmodell=os.environ.get("EINBETTUNGSMODELL", "embeddinggemma-2"),
        denken=os.environ.get("DENKEN", "0") == "1",
        einbettung_cpu=os.environ.get("EINBETTUNG_CPU", "0") == "1",
        pruefer_url=os.environ.get("PRUEFER_URL", ""),
        basismodell=BASIS / "modell" / "ftf.sysml",
        wissen=BASIS / "wissen",
    )
