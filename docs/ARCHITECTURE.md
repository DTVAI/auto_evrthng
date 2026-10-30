# Architektur des optimierten lokalen Piloten

FastAPI stellt die Master-UI und APIs für Tools, Vorgänge, Revisionen, Freigaben,
Belege, Prüfaufträge, Übernahmen und Fallketten bereit. Es bleiben ein lokaler
Dienst, eine SQLite-Datenbank und ein separat startbarer DB-Worker. Lokale
Host-/Origin-Prüfung und `X-Toolbox-Request: 1` schützen Browseraufrufe; sie sind
kein Ersatz für Mehrbenutzer-Authentisierung.

## Gemeinsame Verträge

`contracts.py` definiert alle 81 strukturierten Eingabeschemata mit Typen,
Pflichtfeldern, zulässigen Schlüsseln und begrenzten JSON-Werten. `registry.py`
verbindet sie mit den kanonischen Domain-Beispielen und Katalogtexten. Die UI
nutzt dasselbe Schema für Formulare und Hilfe; die API validiert unabhängig davon.
`decisions.py` bildet kanonische Entscheidungsumfänge und Hashes. Eine lokale
Attestierung ist Prüfdatenmaterial und begründet keine tatsächliche Rolle.

Die sechs Module unter `app/domains` führen ausschließlich lokale Berechnungen,
Vergleiche und Entwurfserzeugung aus. `projections.py` beschreibt relevante
Sollwerte: etwa Person, neuer Stundenwert und Datum, Dokumenthash oder berechnete
Aufgabentermine. Beobachtungen müssen diese Werte mit passenden JSON-Typen
enthalten. Leere Ziele, falsche Person, veraltete Revision oder ungeklärter
lokaler Prüfstatus erlauben keinen Abschluss. Ein passender manueller Nachweis
wird als `manual_attestation` ausgewiesen, nicht als automatisch rückgelesen.

## Persistenz und Fallketten

SQLAlchemy speichert Fälle, Revisionen einschließlich neuer Titel-/Personen-
Metadaten, Freigaben, Nachweise, Ereignisse, Artefakte, Jobs und Wiederholungsschlüssel.
`workflow_models.py` ergänzt Fallketten, Schrittgenerationen, Ereignisse und
atomare Fallübernahmen. `workflows.py` führt drei lokale Graphen: `hours_change`,
`start_shift` und `staffing_invoice`. Ein Schritt darf nur an einen passenden,
aktuell abgeschlossenen Fall gebunden werden. Fachliche Querbezüge werden
geprüft; geänderte Voraussetzungen entwerten transitive Folgeschritte und
bewahren frühere Generationen. Bestätigte unabhängige Schritte bleiben erhalten.

Metriken zählen persistierte Ereignisse, Korrekturen, offene Eingaben und
Abschlüsse. Laufzeit folgt realen Zeitstempeln. Bearbeitungs- und Wartezeit werden
nicht erfunden. Übernahme-/Vertretungslabels koordinieren den lokalen Nutzer;
sie sind keine authentisierten Rechte gegen andere Konten.

## Betrieb

`migrations.py` migriert Schema 0/1 nach Version 2 ohne Zurücksetzen vorhandener
Daten. Nicht rekonstruierbare historische Titel/Personenmetadaten bleiben NULL.
Verbindungen erzwingen SQLite-Fremdschlüssel. PK/FK, Typaffinität, notwendige
Spalten und Unique-Regeln werden vor Betrieb und Restore geprüft.

Private SQLite-Dateien/Sidecars sind unter POSIX erforderlich; unsichere
bestehende Pfade werden abgelehnt. Der Worker verwendet atomare Claims und
Lease-Tokens, begrenztes Backoff für Locks sowie Quarantäne nach wiederholt
fehlgeschlagenen Jobs. Heartbeat-/Fehlerlogs enthalten technische Referenzen.
Alle API-Zeitstempel haben einen UTC-Offset. Requestgrößen werden während des
Lesens begrenzt, JSON-Tiefe und Listengrößen vor der Auswertung geprüft.

Manueller EML-/JSON-/CSV-Import wird nur lokal geparst. Außenadapter, Graph,
Abrechnungsübermittlung, automatischer Versand und unabhängige externe
Readbacks sind nicht freigeschaltet. Details: [Betriebsgrenzen](DEPLOYMENT.md).
