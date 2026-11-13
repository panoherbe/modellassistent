# Messprotokoll Modellassistent

Aufgaben: `eval/aufgaben.yaml` (24, selbst geschrieben, synthetisch: 17 präzise, 7 ungenau oder widersprüchlich).
Je Lauf alle Aufgaben, Temperatur 0, ein Durchgang; Ergebnisse je Aufgabe in `lauf<n>/einzeln.jsonl`.
Läufe 1 bis 6 (10.11.2026): Sprachmodell `qwen2.5:7b-instruct`, Einbettung `bge-m3`. Ab Lauf 7 (11.11.2026): die aktuelle Modellgeneration, siehe „Wahl der Modelle“.

| Lauf | Änderung davor | Rückfrage richtig | Vorschlag richtig | Ebene richtig | Beziehung gefunden | Elemente ohne Fehler | Quelle belegt | Modell gültig (OMG) | Median s |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ein Schritt: Vorschlag direkt (Prompt vorschlag-v1) (Abbruch beim Schreiben der Datei; Werte aus `lauf1.log`) | 0/7 | 17/17 | – | – | – | – | 3/3 | – |
| 2 | Klärung davor, ausreichend ja/nein (klaerung-v1); Prompt vorschlag-v2 mit einem Beispiel | 7/7 | 7/17 | 0/17 | 0/11 | 11/14 | 9/14 | 6/6 | 3,85 |
| 3 | Klärung mit vier Kategorien und „im Zweifel ok“ (klaerung-v2); unzulässige Beziehungen entfernt statt gesperrt | 4/7 | 17/17 | 8/17 | 0/11 | 37/41 | 31/41 | 19/19 | 10,61 |
| 4 | Regeln zur Wahl der RFLP-Ebene, zweites Beispiel (vorschlag-v3), Beschreibung der Teile in der Modellübersicht | 3/7 | 17/17 | 14/17 | 2/11 | 38/41 | 25/41 | 21/21 | 10,97 |
| 5 | jede Anforderung und Funktion braucht eine Beziehung zu einem Teil (vorschlag-v4); Typ „NEU-n“ aufgelöst | 3/7 | 17/17 | 13/17 | 1/11 | 38/41 | 30/41 | 21/21 | 11,31 |
| 6 | Beziehung auf einen neuen Baustein (L) wird auf das Teil gelegt, das ihn ausprägt (zuordnung-v2) | 3/7 | 17/17 | 13/17 | 1/11 | 38/41 | 30/41 | 21/21 | 11,28 |
| 7 | aktuelle Modellgeneration (11.11.2026): Sprachmodell qwen3.8:27b, Einbettung embeddinggemma-2, Ollama 0.40.16, Denkmodus aus; Anweisungen unverändert | 7/7 | 16/17 | 16/17 | 7/11 | 22/22 | 22/22 | 16/16 | 45,26 |
| 8 | keine: Wiederholung von Lauf 7 mit Lastprotokoll (`lauf8-last.log`); 24 von 24 Aufgaben mit gleichem Ergebnis | 7/7 | 16/17 | 16/17 | 7/11 | 22/22 | 22/22 | 16/16 | 50,4 |

„Modell gültig“: Aufgaben, bei denen mindestens ein Element ohne Prüffehler ins Modell eingefügt und das ganze
Modell von der OMG-Pilotimplementierung (jupyter-sysml-kernel) ohne Fehler gelesen wurde.

Lauf 7 lief am 11.11.2026 zwischen 16:13 und 16:30 UTC neben einer anderen Arbeit auf dem Prozessor. Lauf 8
wiederholt ihn ohne Änderung und schreibt die Rechnerlast alle 30 s mit (Lastmittel 9–10 bei 16 Kernen, davon
rund 8 das Sprachmodell selbst): alle 24 Ergebnisse gleich, die Zeiten etwa 10 % länger. Zeitangaben stammen
deshalb aus Lauf 8.

## Wahl der Modelle (11.11.2026)

Abruf je Einbettungsmodell (`eval/abruf.py`, 24 Aufgaben, 20 Lastenheft-Absätze, k = 6, Ollama 0.40.16):

| Einbettungsmodell | erwartete Absätze unter den abgerufenen | an erster Stelle |
|---|---|---|
| `qwen3-embedding:0.6b` | 21/22 | 19 |
| `qwen3-embedding:4b` | 22/22 | 19 |
| `qwen3-embedding:8b` | 22/22 | 20 |
| `embeddinggemma-2` | 22/22 | 21 |

Gewählt: `embeddinggemma-2` (neueste Generation, meiste Treffer an erster Stelle, Apache 2.0).

Tempo und Denkmodus (3 Aufgaben A01, C01, D01; Sekunden je Aufgabe, Klärung und Vorschlag):

| Variante | A01 | C01 | D01 | Ergebnis |
|---|---|---|---|---|
| `qwen3.8:27b` mit Denkmodus | 167,42 | 302,16 | 96,32 | Status 3/3 richtig |
| `qwen3.8:27b` (gewählt) | 98,5 | 60,6 | 25,33 | Status 3/3 richtig |
| `qwen3.8:27b` mit MTP | 56,62 | 59,24 | 25,25 | Status 3/3 richtig |

A01 enthält beim ersten Lauf das Laden des Modells. Die MTP-Variante liefert dieselben Antworten und ist hier kaum schneller (das Modell liegt zu 44 % im Hauptspeicher); der Denkmodus braucht ein Vielfaches der Zeit. Gewählt: `qwen3.8:27b`, Denkmodus aus. Das Sprachmodell ist austauschbar (`SPRACHMODELL`); andere Sprachmodelle sind hier nicht gemessen.

## Stand des letzten Laufs

```
{
 "zeit_utc": "2026-11-11T21:25:48+00:00",
 "sprachmodell": "qwen3.8:27b",
 "sprachmodell_digest": "aaee06c39dcf",
 "einbettungsmodell": "embeddinggemma-2",
 "einbettung_digest": "f4981a15b998",
 "denken": false,
 "einbettung_cpu": false,
 "ollama": "0.40.16",
 "prompt_version": "vorschlag-v4+klaerung-v2+zuordnung-v2",
 "modell_sha256": "684cdfbafc41",
 "abruf_k": 6,
 "temperatur": 0,
 "code": "lauf8",
 "kernel": "jupyter-sysml-kernel 0.63.1"
}
```

## Fehler im letzten Lauf (je Aufgabe)

- **A08** „Das FTF transportiert Gitterboxen und Europaletten.“: Status rueckfrage statt vorschlag; Ebene [] statt ['R']; Beziehung zu P-005 fehlt
- **C01** „Bei Rückwärtsfahrt muss auch hinter dem Fahrzeug überwacht werden; ergänze dafür einen zweiten Scanner.“: Beziehung zu R-003 fehlt
- **C04** „Ergänze einen Not-Halt-Taster auf der rechten Fahrzeugseite.“: Beziehung zu R-006 fehlt
- **C05** „Lege den hinteren Scanner an und ordne ihm zusätzlich die Funktion Hindernisse erkennen zu.“: Beziehung zu F-003 fehlt
