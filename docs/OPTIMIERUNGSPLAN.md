# Optimierungsplan für Werkraum

Stand: 30.10.2026. Grundlage ist das [Review mit Befunden F01–F17](REVIEW.md).
Der folgende Plan beschreibt die vereinbarten Arbeitspakete und Abnahmekriterien.
**OP01–OP06 sind inzwischen lokal implementiert**, OP07 ist durch ein
Readiness-Manifest vorbereitet; der echte Fachpilot und das bedingte OP08
benötigen organisatorische bzw. externe Voraussetzungen. Verbindlichen aktuellen
Umfang und Prüfnachweise führen [Paketstatus](OPTIMIZATION_STATUS.md) und
[Abnahme](VALIDATION.md). Die nachstehenden Anforderungen bleiben als
nachvollziehbare Grundlage erhalten.

## Ziel und Reihenfolge

Zuerst lokale Prüfer fachlich verlässlich machen, danach echte zusammenhängende
Fallketten und eine bessere Bedienung liefern. Anschließend kann ein begrenzter
Mehrbenutzer-/Integrationsbetrieb vorbereitet werden. Microsoft Graph und die
Übermittlung an die Personalabrechnung bleiben dauerhaft außerhalb dieses
Auftrags; P13 wird nicht wieder eingeführt. ANÜ-Rechnungsprüfung A06 bleibt im
Umfang. Ein späterer Outlook-COM-Weg ist eine optionale Windows-Integration,
keine Voraussetzung für den lokalen Importbetrieb.

| Reihenfolge | Arbeitspaket | Priorität / Aufwand relativ | Abhängigkeit | Federführung |
|---|---|---|---|---|
| 1a | OP01 Eingabeverträge und widerspruchsfeste Identität | P1 / mittel | keine | Terra 6.1, Fachlogik |
| 1b | OP02 Freigaben, Entscheidungen und Nachweisbindung | P1 / hoch | OP01 Typ-/Hashvertrag | Terra 6.1, Kernarchitektur |
| 1c | OP03 Datenablage, Sicherung und Wiederanlauf | P1 / mittel | Schemaentscheidung aus OP01/02 | Terra 6.1, Backend/Betrieb |
| 2a | OP04 Master-UI und verständliche Arbeitsabläufe | P1/P2 / mittel | OP01 für Formschema; kann parallel starten | Terra 6.1 für Zustandslogik, Luna für Texte/kleine UI-Aufgaben |
| 2b | OP05 Ereignisse, Fallketten und Prozessmetriken | P1/P2 / hoch | OP01–03 | Terra 6.1, Workflow |
| fortlaufend | OP06 Unabhängige Abnahme und reproduzierbare Builds | P1 / mittel | begleitet jedes Paket | getrennte Terra-Review-/Testrolle; Luna für Matrixpflege |
| 3 | OP07 Kontrollierter Fachpilot | Pilotgate / mittel | OP01–06 bestanden | Orchestrierung + benannte Fachverantwortliche |
| danach | OP08 Mehrbenutzerbetrieb und ausgewählte Adapter | nach Bedarf / hoch | Pilotdaten + bestätigter Zielbetrieb | Terra 6.1 + IT/Fachverantwortliche |

„Mittel/hoch“ beschreibt Komplexität im Vergleich der Pakete, keine unbelegte
Stunden- oder Terminzusage. Es wird mit dem bereits vorhandenen Checkout
gearbeitet. Jeder Subagent bekommt nur seine Dateien, Vertragsdefinitionen und
Abnahmekriterien; Querschnittsänderungen gehen durch die Orchestrierung.

## OP01 · Eingabeverträge und widerspruchsfeste Identität

**Behebt:** F03, F04, F05, F06, F08; schafft Grundlage für F14.

- Pro Tool einen typisierten Eingabevertrag definieren, aus dem API-Validierung,
  Formularfelder und Beispiele entstehen. Keine verstreuten Wahrheitsprüfungen
  als Ersatz für erlaubte Typen, Pflichtfelder oder Nachweisschemata.
- Gemeinsame Typen für Decimal-Geld, Stunden, Währung/Basis, technische UTC-Zeit
  und lokale fachliche Tage verwenden. `bool`, Float, leere Zeichenkette,
  Nicht-Endlichkeit und negative Werte gezielt behandeln. Keine gesetzlichen
  Obergrenzen erfinden: fachlich genehmigte Grenzen konfigurierbar machen.
- R05 vergleicht alle vorhandenen Identifikatoren. Widerspruch bleibt Klärfall;
  Person, Bewerbung und Arbeitsverhältnis bleiben getrennt.
- Fallanlage bekommt einen expliziten stabilen Identitätsvertrag. Gleiche Quelle
  und gleiche Identität ist Replay; andere Person ist HTTP 409. Leere Quellen
  normalisieren; Anlagetitel und spätere Titelrevision klar unterscheiden.
- R06 definiert erlaubte Felder je Anlage-/Änderungsaktion und verlangt geeignete
  Quellen/Entscheidung. Unbekannte sensible Felder nicht als Auftrag weiterreichen.

**Abnahme:** F03/F04/F05/F06/F08-Regressionen bestehen ohne `xfail`. Ergänzend
Tabellenfälle für fehlende, falsch typisierte, negative, doppelte und extrem
große Werte sowie konkurrierende Quell-Replays. Alle 81 Beispiele behalten einen
bewusst festgelegten Status und konkrete Sollwerte.

## OP02 · Freigaben, Entscheidungen und Nachweisbindung

**Behebt:** F01, F02; verbessert die bekannte Beschränkung des Aktenabschlusses.

- Einen kanonischen Entscheidungsumfang definieren: fachliche Person/Objekt,
  Aktionsart, Werte, Datum, Revision, Regel-/Vorlageninhalt, Scope, Gültigkeit
  und erforderliche Rolle. Inhalt vor Hashbildung typisieren/normalisieren.
- T02/T05/P07 und die übrigen Befugnisprüfer auf diesen gemeinsamen Vertrag
  bringen. Gleiche Versionsnummer mit geändertem Inhalt ist keine neue Freigabe.
  Rücknahme/Änderung invalidiert nur abhängige, noch nicht ausgeführte Schritte.
- Fachentscheidung, lokale Aktenfreigabe und tatsächliche Ausführungsberechtigung
  als getrennte Objekte führen. Ein übermitteltes `approved: true` oder ein vom
  Client berechneter Hash bleibt im Pilot nur Prüfdaten, keine Rollenautorität.
- Sollprojektion je Schritt modellieren. Beobachtete Zielwerte werden gegen die
  tatsächlich relevanten Sollfelder verglichen, nicht gegen einen vollständigen
  Eingabe-Payload mit Vorherwerten, Vorlagen und Freigabemetadaten.
- Manuell attestiert, unabhängig per Adapter rückgelesen und nicht verifiziert
  bleiben sichtbare unterschiedliche Nachweisarten. `UNKNOWN` darf keinen
  unbewiesenen Abschluss oder automatischen erneuten Versand auslösen.

**Abnahme:** F01/F02-Regressionen bestehen ohne Marker. Änderung je wesentlichem
Scopefeld sperrt die alte Entscheidung. Falsche Person, falscher Zeitraum,
veraltete Vorlage, falscher Zielwert und unklare Ausführung bleiben offen.
Die UI nennt weiterhin die tatsächliche Nachweismethode.

## OP03 · Datenablage, Sicherung und Wiederanlauf

**Behebt:** F09, F10, F11, F12, F13, F17.

- Anwendungsschema versionieren und Migrationen einführen. Revisionsrelevante
  Metadaten wie Titel/Personenbezug historisieren; Unique-/Fremdschlüsselregeln
  auf Datenbankebene sichern und SQLite-Fremdschlüssel pro Verbindung aktivieren.
- Private lokale Datenablage mit kontrollierten Datei-/Verzeichnisrechten,
  SQLite-Sidecars und dokumentiertem Windows-ACL-Verhalten. Vorhandene Nutzerdaten
  nicht automatisch verschieben oder überschreiben.
- Backupmanifest bekommt getrennte Backupformat- und Anwendungsschemaversion.
  Falsche oder leere Datenbanken ablehnen; Restore prüft Pflichtobjekte,
  Integrität und Hashes an einem neuen Ziel. Ältere unterstützte Schemata
  ausdrücklich migrieren oder verständlich ablehnen.
- Worker erhält kontrollierte Behandlung temporärer DB-Fehler, Backoff,
  Heartbeat, beobachtbaren Fehlerstatus und eine Obergrenze/Quarantäne für
  dauerhaft fehlerhafte Jobs. Leases/Fencing bleiben atomar; keine Außenwirkung
  in den lokalen Worker hineinmogeln.
- Technische Zeitstempel durchgängig als UTC mit Offset serialisieren.
  Requestgrößen beim Lesen begrenzen; strukturierte Listen/Komplexität ebenfalls
  limitieren. Logs enthalten technische Referenzen, keine HR-Payloads.

**Abnahme:** F09/F11/F13-Tests ohne Marker, neue Tests für F10/F12/F17. Reale
Toolbox-DB aus WAL sichern und wiederherstellen, leere/falsche DB ablehnen,
SQLite-Lock injizieren und danach Folgeauftrag erfolgreich ausführen,
zwei Worker/Leaseverlust prüfen, nicht-UTC-Zeit nach Reload eindeutig erhalten.

## OP04 · Master-UI und verständliche Arbeitsabläufe

**Behebt:** F14, F15, F16; macht OP01/02 bedienbar.

- Numerische Leerfelder nie still zu Null konvertieren. Validierungsfehler am
  Feld und Absenden-Gate verwenden; JSON-Ansicht als Expertenmodus erhalten.
- Auch verschachtelte Daten über schemabasierte Formulare bearbeiten:
  Gehaltsrunden-Zeilen, Rechnungspositionen, Termine und Nachweise. CSV bekommt
  explizite Spaltenzuordnung, Vorschau und Fehler je Zeile.
- Toolseite klar in „Was tut es?“, „Wann hilft es?“, „Benötigte Angaben“,
  „Beispiel“ und „Ergebnis/noch offene Schritte“ gliedern. Die echte lokale
  Wirkung aus der Tooldefinition ableiten, nicht nur einen Muster-Ergebnissatz.
- ARIA-Tabpanels, Pfeil-/Home-/End-Steuerung, sinnvolle Fokusziele und beschriftete
  Fehler implementieren. Mobil nicht nur Überlauf, sondern reale Formbedienung
  prüfen. Dirty-State und Verlassen-Warnung; optionale lokale Entwürfe nur mit
  bewusstem Datenschutz-/Löschverhalten.
- Datumseingabe benutzerverständlich in Europe/Berlin, technische Speicherung
  UTC; DST und Sommer-/Winterzeit sichtbar. Die heute korrekt als UTC
  beschriftete Eingabe nicht unbemerkt anders interpretieren.

**Abnahme:** Zahl löschen erzeugt keinen Nullwert; Tastatur allein erreicht und
bedient alle Tabs/Fehler; geändertes Formular bleibt nach Validierungsfehler
erhalten; Reload mit ungespeicherten Daten hat einen klaren Warn-/Wiederherstellungsweg.
End-to-End-Tests für drei verschachtelte Tools und Import-Spaltenfehler.

## OP05 · Ereignisse, Fallketten und Prozessmetriken

**Behebt:** F07, vertieft F08 und die bisher statischen Zustandsvorschauen.

- Ereignisse mit Quell-ID, Objekt-ID, Revision und bekannter Fachzeit persistieren.
  Aufgabenidentität daraus ableiten. Replay und neues Ereignis getrennt prüfen.
- Persistenten Abhängigkeitsgraphen für Dokumente, Termine, Zuständigkeit und
  Verpflichtungen aufbauen. Änderung berechnet die transitive Betroffenheit;
  bereits erfolgte Außenwirkung wird nicht als rückgängig dargestellt.
- M09-Übernahme und Vertretung tatsächlich atomar speichern. M10-Suche auf
  serverseitig kontrollierten Scope beziehen, sobald echte Rollen hinzukommen.
- Drei zusammenhängende lokale Fallketten liefern: (1) genehmigte Stundenänderung
  mit Entwurf und HR-Nachweis, (2) Eintrittsverschiebung mit Aufgaben-/Dokument-
  revisionen, (3) ANÜ-Rechnung mit Positionsabweichung und Korrekturlauf.
  Keine dieser Ketten benötigt P13 oder Microsoft Graph.
- Metriken aus gespeicherten Ereignissen ableiten: aktive Zeit/Wartezeit,
  Abschlussnachweise, Korrekturen und fehlende Angaben mit definierten Nennern.
  Keine erfundenen Einsparungen und keine Mitarbeiterrangliste.

**Abnahme:** F07/F08-Tests ohne Marker. Neues Ereignis erzeugt neue Aufgaben,
Replay keine Dublette. Änderung invalidiert genau abhängige Objekte. Eine
Teilabweichung hält die Fallkette offen, ohne bestätigte andere Schritte erneut
auszuführen. Metriken lassen sich aus den gespeicherten Ereignissen nachrechnen.

## OP06 · Unabhängige Abnahme und reproduzierbare Builds

- Pro Tool mindestens ein unabhängig formuliertes Sollresultat sowie fehlende
  Daten, Widerspruch und relevante Grenzfälle testen. Fachwerte unabhängig vom
  Produktionshelper rechnen; Beispielstatus allein ist keine Abnahme.
- Alle 13 Review-Regressionen einzeln in bestehende Fachtests übernehmen und
  `xfail` erst beim tatsächlich bestandenen Fix entfernen. Verbleibende Marker
  und bekannte Lücken im Releasebericht zählen; sie nie als bestanden ausgeben.
- HTTP/API-, Fachlogik-, Queue-/DB- und Browserprüfungen getrennt organisieren.
  CI mit den gepinnten Abhängigkeiten, Datenbankmigrationen, statischen Checks
  und einer kleinen Browserauswahl ergänzen. Produktivkonten sind keine Testdaten.
- Gemeinsame Tooldefinition als Quelle für Registry, Schema, Hilfe und Beispiele
  nutzen, damit `SAMPLES`, katalogisierte Hilfe und Dokumentation nicht driften.
  Domaincode lesbar formatieren; große Dispatchblöcke schrittweise in explizite
  Funktionen teilen, ohne nutzlose Frameworkwechsel.
- Abhängigkeiten mit autoritativen Hinweisen prüfen und kontrolliert aktualisieren.
  Die vorhandene TestClient-/AnyIO-Warnung beheben und Installation in einer
  frischen Umgebung prüfen; keine unbelegten CVE-Behauptungen.

**Abnahme:** Null bekannte P1-Regressionen unter `xfail`; wiederholbarer Build,
sichtbare Ergebniszählung, aktuelle generierte Hilfe und dokumentierte relevante
Restrisiken. Testfehler blockieren die Freigabe des jeweils betroffenen Pakets.

## OP07 · Kontrollierter Fachpilot

Erst nach den lokalen Integritätsgates echte, minimierte Daten freigeben.
Fachverantwortliche bestätigen Vorlagen, erlaubte Felder, zuständige Rollen,
Nachweisarten und Aufbewahrung je Datenkategorie. Mit den drei OP05-Fallketten
starten; aktive Bearbeitungszeit, notwendige Eingriffe, Fehler und Wartezeit
gegen eine gemessene Baseline auswerten. Keine pauschale B1–B5-Freigabe aus einer
grünen Testsuite ableiten.

**Abnahme:** repräsentative Fälle durch Fachverantwortliche nachvollzogen,
offene Pflichten sichtbar, lokaler Restore wiederholt, Verantwortlicher für
Betrieb und fachliche Änderungen benannt. Keine externe Änderung wird nur aus
einem lokalen `READY` behauptet.

## OP08 · Mehrbenutzerbetrieb und ausgewählte Adapter

Nach bestätigtem Bedarf PostgreSQL/Migrationen, serverseitige Identitäten,
RBAC pro Suche/Download/Export und unverwechselbare Entscheidungsrollen ergänzen.
Zuerst den belegten HRworks-Lese-/manuellen Rückleseweg vorbereiten; jede
Schreibaktion braucht anschließend eigene Tenantrechte, Idempotenz und Readback.
Auf Windows ist klassisches Outlook-COM optional; auf anderen Systemen bleibt
EML-/Dateiimport ein eigenständiger Betriebsweg. Keine Graph-Ausweichlösung und
keine Abrechnungsintegration bauen.

**Abnahme:** Rechteentzug wirkt auch auf abgeleitete Ansichten und Downloads;
Capabilities sind je Aktion belegt. Unbekannter Ausgang bleibt `UNKNOWN`,
reiner Timeout löst keine blinde Wiederholung aus. Zugangsdaten ausschließlich
über sichere Umgebungskonfiguration, erst wenn die konkrete Anbindung gebaut
und ihr Bedarf nachgewiesen ist.

## Zusammenarbeit und Abschlussregel

Terra 6.1 übernimmt domänenübergreifende Verträge, Identität, Freigaben,
Transaktionen, Worker und negative Tests. Luna übernimmt begrenzte Texte,
Hilfematrix und kleine, klar spezifizierte UI-/Dokumentationsaufgaben. Eine
unabhängige Reviewrolle prüft jeden Paketabschluss. Luna 6.1 ist in der
aktuellen Toolauswahl nicht verfügbar; Luna bezeichnet das verfügbare Luna-Modell.

Pro Paket gibt es einen eigenen Commit mit Befund-ID, Verhaltensänderung und
Testnachweis. Beendet wird ein Paket erst mit bestandenen konkreten Kriterien,
aktualisierter Hilfe und korrekt ausgewiesenem Restumfang. Der Startpunkt für
die nächste Umsetzung sind **OP01 und OP02**, parallel zur Betriebshärtung
OP03 und der eng begrenzten Korrektur des numerischen UI-Leerzustands aus OP04.
