# Nachweise

| Datei | Inhalt |
|---|---|
| [`PROTOKOLL.md`](PROTOKOLL.md) | Messprotokoll: alle acht Läufe mit Änderung und Ergebnis, Wahl der Modelle |
| `lauf8/` | maßgeblicher Lauf (11.11.2026, Qwen3.8 27B, EmbeddingGemma 2): `ergebnisse.json` (Kennzahlen), `einzeln.jsonl` (jede Aufgabe mit Antwort, Belegen, SysML-Text, OMG-Prüfung); `lauf8-last.log` Rechnerlast alle 30 s |
| `lauf7/` | derselbe Lauf neben fremder Rechnerlast; 24 von 24 Ergebnissen gleich wie Lauf 8 |
| `lauf1/` bis `lauf6/` | frühere Läufe mit einem kleineren Vorgängermodell (10.11.2026), auch die schlechteren |
| `abruf7/`, `probe7/` | Vergleich von vier Suchmodellen und Proben zu Tempo und Denkmodus (11.11.2026) |
| `tests-*.txt` | Ausgabe der automatischen Tests mit Datum |

Die Vorführung auf panoherbe.com zeigt Antworten aus `lauf8/einzeln.jsonl` (gebaut mit `vorfuehrung/baue.py`).
