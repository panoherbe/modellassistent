# Modellassistent

**LLM-Assistenz für die modellbasierte Systementwicklung mit SysML v2: Aus einem Satz in Alltagssprache entsteht ein
strukturierter Modellvorschlag mit RFLP-Ebene, Beziehungen und Quellen. Das Programm prüft ihn, ein Mensch nimmt jedes
Element an, korrigiert oder lehnt es ab. Erst dann wird er SysML v2, geprüft mit der OMG-Pilotimplementierung, und ein
neuer Modellstand. Das läuft heute, lokal, mit einem offenen Sprachmodell und synthetischen Daten.**

## Was läuft

| Baustein | Umsetzung |
|---|---|
| Systemmodell | synthetisches SysML-v2-Modell eines autonomen Flurförderfahrzeugs in RFLP-Struktur (`modell/ftf.sysml`): 7 Anforderungen, 7 Funktionen, 8 logische Bausteine, 8 Teile, 14 Beziehungen (*satisfy*, *allocate*) |
| Wissensquelle | synthetisches Lastenheft mit 20 Absätzen, je mit Kennung `LH-x.y` (`wissen/`) |
| Abruf | Einbettungen (bge-m3), sechs Absätze je Eingabe; das kleine Modell geht vollständig als Übersicht in den Kontext |
| Klärung | erst prüft das Sprachmodell, ob die Eingabe reicht (Zielwert fehlt, Widerspruch zu einer Quelle, unklar); dann Rückfrage statt Vorschlag |
| Vorschlag | Sprachmodell antwortet nur im festen JSON-Schema (Ebene, Name, Beschreibung, Typ, Beziehungen, Quellen mit Zitat); Kennungen vergibt das Programm |
| Prüfung | Ebene, Name, Doppelungen, Typ eines Teils, zulässige Beziehungen (R *satisfy* P, F *allocate* P), Quelle aus dem Kontext und Zitat wörtlich belegt; Fehler sperren die unveränderte Übernahme |
| Mensch entscheidet | je Element annehmen, korrigieren oder ablehnen, keine Sammelübernahme; Freigabe erst, wenn alles entschieden ist |
| SysML v2 | Text nur aus Vorlagen, an festen Stellen ins Modell eingefügt; das ganze Modell prüft der Jupyter-Kernel der OMG-Pilotimplementierung (`pruefer/`); ist es ungültig, entsteht kein neuer Modellstand |
| Protokoll | nur erweiterbar, Hash-Kette; je Schritt Sprachmodell, Prompt-Version, Quellen mit Stand, Befunde, Entscheidung vorher/nachher, neuer Modellstand |
| Übergabe | SysML-v2-Text und JSON (`/api/anfrage/{id}/export`), REST mit OpenAPI (`/docs`) |

Messung: `nachweis/PROTOKOLL.md` (sechs Läufe am 10.11.2026 mit denselben 24 Aufgaben, jeder Lauf mit allen Aufgaben,
auch die schlechteren). Letzter Lauf: 21 von 21 Modellen nach dem Einfügen gültig (OMG-Pilotimplementierung),
30 von 41 Elementen mit wörtlich belegter Quelle, 17 von 17 präzisen Eingaben mit Vorschlag, aber nur 3 von 7 vagen
oder widersprüchlichen Eingaben mit Rückfrage und 11 von 21 Anforderungen und Funktionen mit Beziehung zu einem Teil.
Bilder: `medien/bilder/`.

## Start

Voraussetzung: Docker mit Compose, NVIDIA-GPU mit 8 GB oder mehr (gemessen: RTX 3060, 12 GB).

```bash
docker compose up -d
docker compose exec ollama ollama pull qwen2.5:7b-instruct
docker compose exec ollama ollama pull bge-m3
# Oberfläche: http://127.0.0.1:8431
docker compose run --rm test                                    # Tests ohne Sprachmodell
docker compose run --rm app python -m eval.messen --ausgabe nachweis/neu   # Messlauf
```

## Was der Prototyp nicht ist

Ein Prototyp mit synthetischen Daten. Er liest nur die Teilmenge der SysML-v2-Textnotation, in der das Beispielmodell
geschrieben ist (die Gültigkeit des ganzen Modells prüft die OMG-Pilotimplementierung); er legt neue Elemente an, ändert
aber keine vorhandenen; Anmeldung und Rollen fehlen; die Messaufgaben sind selbst geschrieben.

## Lizenz

AGPL-3.0. Sprachmodell Qwen2.5 (Apache 2.0), Einbettung bge-m3 (MIT), OMG SysML v2 Pilot Implementation (EPL-2.0).
Auftraggeber erhalten im Auftrag die vertraglich vereinbarten Rechte.

Panagiotis Herbe · [panoherbe.com](https://panoherbe.com)
