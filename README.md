# Werkraum · HR Toolbox

Ein gemeinsamer, lokal laufender Werkzeugkasten für Kommunikation, Recruiting,
Personalverwaltung, ANÜ, Prozesssteuerung und Betrieb. Aus dem Bauplan vom
30.10.2026 sind **81 Funktionen** als ausführbare lokale Prüfungen, Berechnungen,
Vergleiche und Entwurfshilfen umgesetzt. Microsoft Graph und die Übermittlung
an die Personalabrechnung (P13) sind ausgeschlossen. Die ANÜ-Rechnungsprüfung
bleibt enthalten.

**Review-Stand:** Die erneute Prüfung hat offene Integritäts- und Bedienfehler
gefunden. Die Suite enthält derzeit **55 bestandene Tests und 13 ausdrücklich
erwartete Fehlschläge** als reproduzierbare Fehlernachweise. Der Stand ist ein
Entwicklungspilot. [Review](docs/REVIEW.md) und
[priorisierter Optimierungsplan](docs/OPTIMIERUNGSPLAN.md) beschreiben die nächsten
Arbeitspakete; die dort genannten Fehler sind noch nicht behoben.

## Starten

Voraussetzung: Python 3.12. Im Repository:

```bash
./scripts/setup.sh
./scripts/start.sh
```

Die Master-UI ist anschließend lokal auf Port 8000 verfügbar. Der Server bindet
an `127.0.0.1`. Unter Windows:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.lock
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Benutzen

1. In **Werkzeuge** nach Aufgabe, ID, Bereich oder Ausbaupaket suchen.
2. **So funktioniert’s** erklärt Zweck, Eingaben, Ablauf und Grenzen.
3. Ein synthetisches Beispiel laden, Felder bearbeiten oder eine JSON-/EML-/CSV-Datei
   lokal einlesen. Komplexe Listen werden im JSON-Editor gepflegt; CSV wird als
   Vorschau gelesen und anschließend fachlich zugeordnet. EML ist direkt für
   M01, M03 und R03 vorbereitet. Empfangszeit und Identität selbst prüfen.
4. **Test ausführen** liefert konkrete Ergebnisse, Abweichungen und gegebenenfalls
   herunterladbare Textentwürfe. Ein Prüfergebnis ist keine externe Ausführung.
5. Bei Bedarf einen **Vorgang** speichern. Änderungen erzeugen neue Revisionen;
   bestehende Freigaben gelten dann nicht für die neue Revision. Der lokale
   Aktenabschluss verlangt eine aktuelle Freigabe und einen passend erfassten
   manuellen Rücklesebeleg. Die Anwendung überprüft dessen externe Herkunft nicht.

**Prüfaufträge** bleiben über einen Neustart hinweg gespeichert. Für ihre
Verarbeitung einen zweiten Prozess starten:

```bash
.venv/bin/python -m app.worker
# Oder genau einen fälligen Auftrag bearbeiten:
.venv/bin/python -m app.worker --once
```

Der Worker führt ausschließlich lokale Auswertungen aus. Wiederholungsschlüssel,
Lease-Übernahme und gespeicherte Prüfergebnisse verhindern doppelte lokale Jobs.

## Prüfen

```bash
.venv/bin/python -m pytest -q
node --check app/static/app.js
```

Die Tests umfassen sämtliche 81 Beispielaufrufe über die echte API sowie
Fehlerfälle für Identität, interne und externe Antworten, Freigaberevisionen,
Decimal-Rundung, Terminüberschneidungen, Rechnungspositionen, Abhängigkeitszyklen,
Dateiimport und dauerhafte Aufträge. Für die optionale Browserprüfung:

```bash
# Mit gestartetem Server und installiertem Playwright/Chromium:
python tests/browser_smoke.py
```

## Betriebsumfang

Dies ist ein **lokaler Einplatz-Pilot mit SQLite**, keine freigeschaltete
Mehrbenutzer- oder Produktivplattform. Der Prozessnutzer kann die lokale Akte
bearbeiten; eine organisatorische Rollenverwaltung oder unabhängige Authentisierung
ist damit nicht nachgewiesen. In Werkzeugen eingegebene Rollen, Quellen und Belege
sind Prüfdaten und erteilen keine tatsächlichen Zugriffsrechte.

Die Datenbank `toolbox.db` enthält Vorgänge, Revisionen, Nachweise, Prüfergebnisse
und Artefakte; sie wird nicht in Git aufgenommen. Pfad alternativ über
`TOOLBOX_DATABASE_URL` konfigurieren. Das Datenbankschema wird beim Start angelegt;
produktive Migrationen, PostgreSQL-Betrieb, verschlüsselte Sicherung und ein
nachgewiesener Wiederherstellungsprozess sind noch nicht eingerichtet.

HRworks, Zeitwirtschaft, Outlook/COM, Kalender und Signaturdienste sind **nicht
angebunden**. Es werden keine E-Mails versandt und keine Personalwerte in
Fremdsystemen verändert. Für diese Schritte erzeugt die Anwendung Vorschauen
oder prüft bereitgestellte Daten. Rechtliche Entscheidungen, Personalentscheidungen
und die Prüfung verbindlicher Vorlagen bleiben bei den zuständigen Personen.

Die B1–B5-Kennzeichnung stammt aus dem Bauplan und ist eine Ausbauzuordnung,
keine Behauptung einer abgeschlossenen produktiven Abnahme.

- [Bedienbeispiele und API-Abläufe](docs/HOW_TO.md)
- [Abdeckung aller Funktionen](docs/IMPLEMENTATION.md)
- [Architektur](docs/ARCHITECTURE.md)
- [Umfang und Grenzen](docs/SCOPE.md)
- [Szenarien und tatsächlich geprüfte Eigenschaften](docs/SCENARIO_TESTS.md)
- [Lokale Sicherung und Wiederherstellung](docs/BACKUP.md)
- [Abnahme dieser Umsetzung](docs/VALIDATION.md)
