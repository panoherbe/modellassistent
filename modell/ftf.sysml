// Synthetisches Systemmodell eines autonomen Flurförderfahrzeugs (FTF) in SysML v2, Textnotation.
// Alle Werte sind erfunden; das Modell dient nur dem Prototyp des Modellassistenten.
// RFLP-Konvention dieses Prototyps: R = Anforderungen (requirement), F = Funktionen (action),
// L = logische Bausteine (part def), P = physische Ausprägung (part im Fahrzeug ftf).
// Kennungen stehen als Kurzname in <'...'>. Zeilen mit „// einfuegen:“ markieren, wo freigegebene Vorschläge landen.
package FTF {

    package Anforderungen {
        requirement <'R-001'> nutzlast {
            doc /* Das FTF transportiert Ladungsträger mit einer Masse von bis zu 500 kg. */
        }
        requirement <'R-002'> fahrgeschwindigkeit {
            doc /* Die Fahrgeschwindigkeit beträgt im Automatikbetrieb höchstens 1,5 m/s. */
        }
        requirement <'R-003'> personenschutz {
            doc /* Personen und Hindernisse im Fahrweg werden erkannt; das FTF hält vor ihnen sicher an. */
        }
        requirement <'R-004'> einsatzdauer {
            doc /* Das FTF arbeitet mit einer Akkuladung mindestens 8 Stunden im Schichtbetrieb. */
        }
        requirement <'R-005'> positioniergenauigkeit {
            doc /* An Übergabestationen positioniert sich das FTF auf ±10 mm genau. */
        }
        requirement <'R-006'> notHalt {
            doc /* Ein Not-Halt an beiden Fahrzeugseiten bringt das FTF sofort zum Stillstand. */
        }
        requirement <'R-007'> leitsystemanbindung {
            doc /* Das FTF empfängt Fahraufträge vom Leitsystem und meldet seinen Zustand zurück. */
        }
        // einfuegen: R
    }

    package Funktionen {
        action <'F-001'> navigieren {
            doc /* Position bestimmen und eine Route zum Ziel planen. */
        }
        action <'F-002'> fahren {
            doc /* Das Fahrzeug entlang der geplanten Route bewegen. */
        }
        action <'F-003'> hindernisseErkennen {
            doc /* Den Fahrweg überwachen und Hindernisse sowie Personen erkennen. */
        }
        action <'F-004'> lastHandhaben {
            doc /* Ladungsträger aufnehmen und abgeben. */
        }
        action <'F-005'> energieBereitstellen {
            doc /* Elektrische Energie speichern und an die Verbraucher verteilen. */
        }
        action <'F-006'> kommunizieren {
            doc /* Fahraufträge empfangen und Zustandsmeldungen an das Leitsystem senden. */
        }
        action <'F-007'> notHaltAusloesen {
            doc /* Bei Betätigung des Not-Halts alle Antriebe sicher abschalten. */
        }
        // einfuegen: F
    }

    package Logik {
        part def <'L-001'> Fahrwerk {
            doc /* Antriebsräder mit Motoren und Bremsen. */
        }
        part def <'L-002'> Navigationsrechner {
            doc /* Rechner für Lokalisierung, Routenplanung und Fahrzeugführung. */
        }
        part def <'L-003'> Sicherheitslaserscanner {
            doc /* Sensor, der Schutzfelder im Fahrweg überwacht. */
        }
        part def <'L-004'> Lastaufnahme {
            doc /* Hubeinrichtung für Ladungsträger. */
        }
        part def <'L-005'> Energiespeicher {
            doc /* Akku mit Batteriemanagement. */
        }
        part def <'L-006'> Funkmodul {
            doc /* Drahtlose Verbindung zum Leitsystem. */
        }
        part def <'L-007'> Sicherheitssteuerung {
            doc /* Steuerung für Not-Halt und Schutzfeldauswertung. */
        }
        part def <'L-008'> Fahrzeug {
            doc /* Das Flurförderfahrzeug als Ganzes. */
        }
        // einfuegen: L
    }

    package Physik {
        part <'P-001'> ftf : Logik::Fahrzeug {
            part <'P-002'> fahrwerk : Logik::Fahrwerk;
            part <'P-003'> rechner : Logik::Navigationsrechner;
            part <'P-004'> scannerVorn : Logik::Sicherheitslaserscanner;
            part <'P-005'> hubwerk : Logik::Lastaufnahme;
            part <'P-006'> akku : Logik::Energiespeicher;
            part <'P-007'> funk : Logik::Funkmodul;
            part <'P-008'> sicherheitssteuerung : Logik::Sicherheitssteuerung;
            // einfuegen: P
        }
    }

    package Verknuepfungen {
        satisfy Anforderungen::nutzlast by Physik::ftf.hubwerk;
        satisfy Anforderungen::fahrgeschwindigkeit by Physik::ftf.fahrwerk;
        satisfy Anforderungen::personenschutz by Physik::ftf.scannerVorn;
        satisfy Anforderungen::einsatzdauer by Physik::ftf.akku;
        satisfy Anforderungen::positioniergenauigkeit by Physik::ftf.rechner;
        satisfy Anforderungen::notHalt by Physik::ftf.sicherheitssteuerung;
        satisfy Anforderungen::leitsystemanbindung by Physik::ftf.funk;
        allocate Funktionen::navigieren to Physik::ftf.rechner;
        allocate Funktionen::fahren to Physik::ftf.fahrwerk;
        allocate Funktionen::hindernisseErkennen to Physik::ftf.scannerVorn;
        allocate Funktionen::lastHandhaben to Physik::ftf.hubwerk;
        allocate Funktionen::energieBereitstellen to Physik::ftf.akku;
        allocate Funktionen::kommunizieren to Physik::ftf.funk;
        allocate Funktionen::notHaltAusloesen to Physik::ftf.sicherheitssteuerung;
        // einfuegen: V
    }
}
