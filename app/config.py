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
    pruefer_url: str
    basismodell: Path
    wissen: Path


def laden() -> Einstellungen:
    daten = Path(os.environ.get("DATENVERZEICHNIS", BASIS / "daten"))
    daten.mkdir(parents=True, exist_ok=True)
    return Einstellungen(
        daten=daten,
        ollama_url=os.environ.get("OLLAMA_URL", "http://localhost:11434"),
        sprachmodell=os.environ.get("SPRACHMODELL", "qwen2.5:7b-instruct"),
        einbettungsmodell=os.environ.get("EINBETTUNGSMODELL", "bge-m3"),
        pruefer_url=os.environ.get("PRUEFER_URL", ""),
        basismodell=BASIS / "modell" / "ftf.sysml",
        wissen=BASIS / "wissen",
    )
