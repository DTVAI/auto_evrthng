# Implementierungsübersicht

Der Katalog enthält 81 aktive Funktionen. `B1`–`B5` bezeichnet die Ausbauphase des Zielbilds, nicht einen Produktreifegrad. Die lokale Auswertung je Funktion ist eine regelbasierte Vorschau aus dem passenden Domain-Modul. Das Beispielergebnis in der Tabelle stammt aus dem zugehörigen synthetischen `SAMPLES`-Eingabewert; es ist weder eine Abnahme noch ein Ergebnis für reale HR-Daten.

| ID | Ausbau | Paket | Lokale Prüffunktion anhand des Beispielaufrufs | Live-Anbindung |
|---|---|---|---|---|
| M01 | B1 | `app.domains.communication → app.services` | Nachricht lokal eingeordnet. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| M02 | B3 | `app.domains.communication → app.services` | Archivbeleg lokal vorbereitet. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| M03 | B1 | `app.domains.communication → app.services` | Eingänge mit Herkunft und Änderungen verglichen. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| M04 | B3 | `app.domains.communication → app.services` | Empfängerkontext ausgewertet. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| M05 | B3 | `app.domains.communication → app.services` | Fragen einzeln abgeglichen. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| M06 | B3 | `app.domains.communication → app.services` | Zusage mit Datum und Erfüllungsbedingung erfasst. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| M07 | B3 | `app.domains.communication → app.services` | Quellengebundener Entwurf erstellt. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| M08 | B3 | `app.domains.communication → app.services` | Entwurf ist aktuell. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| M09 | B1 | `app.domains.communication → app.services` | Lokaler Übernahmevorschlag erstellt. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| M10 | B1 | `app.domains.communication → app.services` | Exakte Suche im angegebenen Berechtigungsbereich abgeschlossen. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| M11 | B1 | `app.domains.communication → app.services` | Feldänderungen und betroffene Schritte dargestellt. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| M12 | B3 | `app.domains.communication → app.services` | Berechtigte Fälle nach bestätigter Person gruppiert. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| M13 | B3 | `app.domains.communication → app.services` | Arbeitsübersicht mit erklärten Prioritäten erstellt. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| M14 | B5 | `app.domains.communication → app.services` | Übergabeübersicht erstellt. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| M15 | B1 | `app.domains.communication → app.services` | Wissensversion lokal erfasst. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| R01 | B3 | `app.domains.recruiting → app.services` | Bedarf und freie Kapazität verglichen. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| R02 | B3 | `app.domains.recruiting → app.services` | Kampagnenentwurf erstellt. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| R03 | B3 | `app.domains.recruiting → app.services` | Bewerbung lokal erfasst. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| R04 | B3 | `app.domains.recruiting → app.services` | Felder mit Fundstellen extrahiert. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| R05 | B3 | `app.domains.recruiting → app.services` | Identität belegt. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| R06 | B3 | `app.domains.recruiting → app.services` | Manuellen HR-Abgleich vorbereitet. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| R07 | B3 | `app.domains.recruiting → app.services` | Fehlende Angaben zusammengestellt. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| R08 | B3 | `app.domains.recruiting → app.services` | Vorstellungen mit Quellen getrennt dargestellt. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| R09 | B3 | `app.domains.recruiting → app.services` | Minimiertes Profil für manuelle Übergabe erstellt. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| R10 | B3 | `app.domains.recruiting → app.services` | Termin lokal geprüft. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| R11 | B3 | `app.domains.recruiting → app.services` | Menschliche Entscheidung dokumentiert. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| R12 | B3 | `app.domains.recruiting → app.services` | Gesprächsüberblick aus belegten Fakten erstellt. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| R13 | B3 | `app.domains.recruiting → app.services` | Startbereitschaft belegt. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| R14 | B3 | `app.domains.recruiting → app.services` | Datumsänderung mit Abhängigkeiten vorbereitet. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| R15 | B3 | `app.domains.recruiting → app.services` | Profilstände neutral verglichen. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| P01 | B2 | `app.domains.personnel → app.services` | Passende Freigabe für Änderung erforderlich. (Beispielstatus `NEEDS_DECISION`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| P02 | B2 | `app.domains.personnel → app.services` | Passende Freigabe für Änderung erforderlich. (Beispielstatus `NEEDS_DECISION`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| P03 | B4 | `app.domains.personnel → app.services` | Gehaltsrunde einzeln geprüft. (Beispielstatus `NEEDS_DECISION`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| P04 | B2 | `app.domains.personnel → app.services` | Korrektur als neue Version vorbereitet. (Beispielstatus `NEEDS_DECISION`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| P05 | B2 | `app.domains.personnel → app.services` | Freigegebene Vorlage als Entwurf befüllt. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| P06 | B2 | `app.domains.personnel → app.services` | Signatur oder Dokumentzuordnung muss manuell geklärt werden. (Beispielstatus `NEEDS_DECISION`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| P07 | B4 | `app.domains.personnel → app.services` | Beteiligungsnachweis geprüft. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| P08 | B4 | `app.domains.personnel → app.services` | Zeiträume geprüft. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| P09 | B4 | `app.domains.personnel → app.services` | Zeiträume geprüft. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| P10 | B4 | `app.domains.personnel → app.services` | Rückkehrdaten geprüft. (Beispielstatus `NEEDS_DECISION`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| P11 | B4 | `app.domains.personnel → app.services` | Stammdatenänderung geprüft. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| P12 | B4 | `app.domains.personnel → app.services` | Freigegebene Vorlage als Entwurf befüllt. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| P14 | B4 | `app.domains.personnel → app.services` | Qualifikationsnachweis geprüft. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| P15 | B4 | `app.domains.personnel → app.services` | Austrittsentscheidung und Aufgaben anhand lokaler Angaben geprüft. (Beispielstatus `NEEDS_DECISION`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| P16 | B4 | `app.domains.personnel → app.services` | Abwesenheit und Übergabe vorbereitet. (Beispielstatus `NEEDS_DECISION`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| P17 | B4 | `app.domains.personnel → app.services` | Vertragsversionen verglichen. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| P18 | B2 | `app.domains.personnel → app.services` | Freigabeumfang geprüft. (Beispielstatus `NEEDS_DECISION`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| A01 | B4 | `app.domains.staffing → app.services` | Bedarfsanfrage vorbereitet. (Beispielstatus `NEEDS_DECISION`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| A02 | B4 | `app.domains.staffing → app.services` | Angebote sachlich verglichen; Auswahl bleibt beim Menschen. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| A03 | B4 | `app.domains.staffing → app.services` | Bestellung als Entwurf vorbereitet. (Beispielstatus `NEEDS_DECISION`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| A04 | B4 | `app.domains.staffing → app.services` | Einsatzunterlagen geprüft. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| A05 | B4 | `app.domains.staffing → app.services` | Stunden positionsweise verglichen. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| A06 | B4 | `app.domains.staffing → app.services` | Rechnung positionsweise geprüft. (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| A07 | B4 | `app.domains.staffing → app.services` | Reklamationsstand geprüft. (Beispielstatus `NEEDS_DECISION`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| A08 | B4 | `app.domains.staffing → app.services` | Einsatzänderung und offene Aufgaben geprüft. (Beispielstatus `NEEDS_DECISION`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| O01 | B5 | `app.domains.orchestration → app.services` | Aufgabenvorschau berechnet (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| O02 | B5 | `app.domains.orchestration → app.services` | Rückwärtsplan als Vorschlag berechnet (Beispielstatus `NEEDS_DECISION`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| O03 | B5 | `app.domains.orchestration → app.services` | Beschaffungsplan erstellt (Beispielstatus `NEEDS_DATA`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| O04 | B5 | `app.domains.orchestration → app.services` | Formularentwurf erstellt (Beispielstatus `NEEDS_DATA`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| O05 | B5 | `app.domains.orchestration → app.services` | Transitive Folgen berechnet (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| O06 | B5 | `app.domains.orchestration → app.services` | Entscheidungspakete zur Prüfung erstellt (Beispielstatus `NEEDS_DECISION`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| O07 | B5 | `app.domains.orchestration → app.services` | Szenarien vergleichbar; Entscheidung bleibt bei der Fachrolle (Beispielstatus `NEEDS_DECISION`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| O08 | B5 | `app.domains.orchestration → app.services` | Vertretungsprüfung abgeschlossen (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| O09 | B5 | `app.domains.orchestration → app.services` | Blockadenübersicht erstellt (Beispielstatus `NEEDS_DATA`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| O10 | B5 | `app.domains.orchestration → app.services` | Offene Fragen gebündelt (Beispielstatus `NEEDS_DATA`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| O11 | B5 | `app.domains.orchestration → app.services` | Regelvorschläge aus bestätigten Korrekturen (Beispielstatus `NEEDS_DECISION`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| O12 | B5 | `app.domains.orchestration → app.services` | Regel nur simuliert (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| O13 | B5 | `app.domains.orchestration → app.services` | Verpflichtungen geprüft (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| O14 | B5 | `app.domains.orchestration → app.services` | Kennzahlen aus gelieferten Fällen berechnet (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| T01 | B1 | `app.domains.platform → app.services` | Zeitbezogene Faktensicht berechnet (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| T02 | B1 | `app.domains.platform → app.services` | Regel und Befugnis getrennt geprüft (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| T03 | B1 | `app.domains.platform → app.services` | Timer und Lease bewertet (Beispielstatus `NEEDS_DECISION`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| T04 | B1 | `app.domains.platform → app.services` | Gelieferte Fähigkeitsnachweise ausgewertet (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| T05 | B1 | `app.domains.platform → app.services` | Intentvorschau erstellt (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| T06 | B1 | `app.domains.platform → app.services` | Soll und unabhängige Beobachtung verglichen (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| T07 | B2 | `app.domains.platform → app.services` | Dokumententwurf reproduzierbar gerendert (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| T08 | B3 | `app.domains.platform → app.services` | Extraktionskandidaten zur Prüfung (Beispielstatus `NEEDS_DECISION`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| T09 | B1 | `app.domains.platform → app.services` | Zugriff und Aufbewahrung als Vorschau geprüft (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| T10 | B1 | `app.domains.platform → app.services` | Manifest gegen gelieferte Inhalte geprüft (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| T11 | B1 | `app.domains.platform → app.services` | Gelieferte Testergebnisse und Rolloutfreigabe geprüft (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |
| T12 | B1 | `app.domains.platform → app.services` | Umfang aus gelieferten Daten berechnet (Beispielstatus `READY`) | Nicht eingerichtet; Import/Export und externe Rücklesung erfolgen manuell. |

## Eingabehilfe und Herkunft

Für jede Funktion enthält `app/data/catalog.json` ein `help`-Objekt mit konkretem synthetischem `sample_input`, den verschachtelten Feldern samt Beispielen und Beschreibungen sowie der lokalen Beispielausgabe. Das Schema ist als Hilfestellung gedacht; die Domain-Funktion entscheidet über benötigte Felder. Jeder Katalogeintrag führt `source_process_id` getrennt von `source_sha256`; der Hash bezieht sich auf die unveränderte Quelldatei. P13 ist ausgeschlossen.
