"""SQLite: Anfragen, Vorschläge je Element mit Entscheidung, Modellstände und das nur erweiterbare Protokoll."""
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS anfrage (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    eingabe     TEXT NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('rueckfrage', 'offen', 'freigegeben', 'verworfen')),
    vorschlag   TEXT NOT NULL,            -- JSON: Ergebnis von vorschlag.erzeugen (mit Rohantwort und Kontext)
    modell_stand TEXT NOT NULL,           -- SHA-256 (Anfang) des Modells, auf dem der Vorschlag beruht
    angelegt    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS element (
    anfrage_id  INTEGER NOT NULL REFERENCES anfrage(id),
    id          TEXT NOT NULL,            -- vergebene Kennung, z. B. R-008
    daten       TEXT NOT NULL,            -- JSON: Vorschlag des Assistenten mit Befunden
    entscheidung TEXT CHECK (entscheidung IN ('angenommen', 'bearbeitet', 'abgelehnt')),
    endfassung  TEXT,                     -- JSON nach menschlicher Korrektur
    entschieden_am TEXT,
    PRIMARY KEY (anfrage_id, id)
);
CREATE TABLE IF NOT EXISTS modellstand (
    nr          INTEGER PRIMARY KEY,
    sha256      TEXT NOT NULL,
    text        TEXT NOT NULL,
    anfrage_id  INTEGER,
    syntax      TEXT NOT NULL,            -- JSON: Ergebnis der OMG-Pilotimplementierung oder „nicht geprüft“
    angelegt    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS protokoll (
    nr          INTEGER PRIMARY KEY,
    zeit        TEXT NOT NULL,
    benutzer    TEXT,
    aktion      TEXT NOT NULL,
    daten       TEXT NOT NULL,            -- JSON
    vorgaenger  TEXT NOT NULL,
    hash        TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS protokoll_nur_anhaengen_u BEFORE UPDATE ON protokoll
BEGIN SELECT RAISE(ABORT, 'Protokoll ist nur erweiterbar'); END;
CREATE TRIGGER IF NOT EXISTS protokoll_nur_anhaengen_d BEFORE DELETE ON protokoll
BEGIN SELECT RAISE(ABORT, 'Protokoll ist nur erweiterbar'); END;
"""


def verbinden(pfad: Path | str) -> sqlite3.Connection:
    con = sqlite3.connect(pfad, check_same_thread=False, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA)
    return con
