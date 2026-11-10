# Messprotokoll Modellassistent

Aufgaben: `eval/aufgaben.yaml` (24, selbst geschrieben, synthetisch: 17 präzise, 7 ungenau oder widersprüchlich).
Je Lauf alle Aufgaben, Temperatur 0, ein Durchgang; Ergebnisse je Aufgabe in `lauf<n>/einzeln.jsonl`.

| Lauf | Änderung davor | Rückfrage richtig | Vorschlag richtig | Ebene richtig | Beziehung gefunden | Elemente ohne Fehler | Quelle belegt | Modell gültig (OMG) | Median s |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ein Schritt: Vorschlag direkt (Prompt vorschlag-v1) (Abbruch beim Schreiben der Datei; Werte aus `lauf1.log`) | 0/7 | 17/17 | – | – | – | – | 3/3 | – |
| 2 | Klärung davor, ausreichend ja/nein (klaerung-v1); Prompt vorschlag-v2 mit einem Beispiel | 7/7 | 7/17 | 0/17 | 0/11 | 11/14 | 9/14 | 6/6 | 3,85 |
| 3 | Klärung mit vier Kategorien und „im Zweifel ok“ (klaerung-v2); unzulässige Beziehungen entfernt statt gesperrt | 4/7 | 17/17 | 8/17 | 0/11 | 37/41 | 31/41 | 19/19 | 10,61 |
| 4 | Regeln zur Wahl der RFLP-Ebene, zweites Beispiel (vorschlag-v3), Beschreibung der Teile in der Modellübersicht | 3/7 | 17/17 | 14/17 | 2/11 | 38/41 | 25/41 | 21/21 | 10,97 |
| 5 | jede Anforderung und Funktion braucht eine Beziehung zu einem Teil (vorschlag-v4); Typ „NEU-n“ aufgelöst | 3/7 | 17/17 | 13/17 | 1/11 | 38/41 | 30/41 | 21/21 | 11,31 |
| 6 | Beziehung auf einen neuen Baustein (L) wird auf das Teil gelegt, das ihn ausprägt (zuordnung-v2) | 3/7 | 17/17 | 13/17 | 1/11 | 38/41 | 30/41 | 21/21 | 11,28 |

„Modell gültig“: Aufgaben, bei denen mindestens ein Element ohne Prüffehler ins Modell eingefügt und das ganze
Modell von der OMG-Pilotimplementierung (jupyter-sysml-kernel) ohne Fehler gelesen wurde.

## Stand des letzten Laufs

```
{
 "zeit_utc": "2026-11-10T21:54:14+00:00",
 "sprachmodell": "qwen2.5:7b-instruct",
 "sprachmodell_digest": "845dbda0ea48",
 "einbettungsmodell": "bge-m3",
 "einbettung_digest": "790764642607",
 "prompt_version": "vorschlag-v4+klaerung-v2+zuordnung-v2",
 "modell_sha256": "684cdfbafc41",
 "abruf_k": 6,
 "temperatur": 0,
 "code": "lauf6",
 "kernel": "jupyter-sysml-kernel 0.63.1"
}
```

## Fehler im letzten Lauf (je Aufgabe)

- **A01** „Das Fahrzeug soll Rampen mit voller Last befahren können.“: Ebene ['F', 'P'] statt ['R']; Beziehung zu P-002 fehlt
- **A03** „Das Fahrzeug darf nicht breiter als 900 mm sein.“: Beziehung zu P-001 fehlt
- **A05** „Das FTF muss Position, Ladestand und Störungen jede Sekunde an das Leitsystem melden.“: Ebene ['F', 'P'] statt ['R']; Beziehung zu P-007 fehlt
- **A07** „Die Lastaufnahme soll Ladungsträger um bis zu 120 mm anheben.“: Ebene ['L', 'P'] statt ['R']; Beziehung zu P-005 fehlt
- **A08** „Das FTF transportiert Gitterboxen und Europaletten.“: Ebene ['F', 'L', 'P'] statt ['R']; Beziehung zu P-005 fehlt
- **A09** „Das Fahrzeug muss im Zweischichtbetrieb mit 30 Minuten Ladepause zwischen den Schichten auskommen.“: Beziehung zu P-006 fehlt
- **B03** „Füge eine Funktion zum Melden von Störungen an das Leitsystem hinzu.“: Beziehung zu P-007 fehlt
- **C01** „Bei Rückwärtsfahrt muss auch hinter dem Fahrzeug überwacht werden; ergänze dafür einen zweiten Scanner.“: Beziehung zu R-003 fehlt
- **C04** „Ergänze einen Not-Halt-Taster auf der rechten Fahrzeugseite.“: Beziehung zu R-006 fehlt
- **C05** „Lege den hinteren Scanner an und ordne ihm zusätzlich die Funktion Hindernisse erkennen zu.“: Beziehung zu F-003 fehlt
- **D03** „Ergänze einen Sensor.“: Status vorschlag statt rueckfrage
- **D04** „Die Akkulaufzeit soll verbessert werden.“: Status vorschlag statt rueckfrage
- **D05** „Das Fahrzeug soll 2000 kg tragen können.“: Status vorschlag statt rueckfrage
- **D06** „Die Höchstgeschwindigkeit im Automatikbetrieb soll 3 m/s betragen.“: Status vorschlag statt rueckfrage
