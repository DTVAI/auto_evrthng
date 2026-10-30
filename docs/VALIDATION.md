# Abnahme der Optimierungen vom 30.10.2026

Geprüft: lokaler Einplatz-Pilot mit Python 3.12.14, SQLite und Chromium.
Alle verwendeten Fachfälle waren synthetisch. Es wurden keine produktiven
Nachrichten, Tenantrechte oder Personaldaten abgerufen und keine Außenaktionen
ausgeführt.

| Prüfung | Tatsächliches Ergebnis |
|---|---|
| Frische virtuelle Umgebung, Installation aus `requirements.lock` mit `--require-hashes` | Bestanden; unabhängige Umgebung ohne vorinstallierte Projektpakete |
| Gesamtsuite mit `-W error` in dieser frischen Umgebung | **277 Tests bestanden, zusätzlich 81 Subtests bestanden**, keine Warnungen, keine xfail-/skip-Marker |
| Frühere 13 Fehlernachweise | Normale bestandene Regressionen in `test_review_regressions.py` |
| Jeder aktive Toolvertrag und jeder konkrete Beispielwert | 81 Eingabeverträge plus 81 unabhängig festgelegte fachliche Sollwerte geprüft |
| Drei lokale Fallketten | Stundenänderung, Eintrittsverschiebung und ANÜ-Rechnungskorrektur vollständig über echte API, Freigabe, manuelle Zielbelege und Schrittbindung geprüft |
| Negative Fallketten | Falsche Person/falsches Datum blockieren; Rechnung mit Positionsabweichung bleibt offen; Revision erhält unabhängige abgeschlossene Schritte und historische Generationen |
| Browser-Grundabnahme | Suche, Hilfe, Tests, Artefakte, Fallrevision, Freigabe, passende Beobachtung, Import und Jobs auf Desktop/Mobil bestanden |
| Browser-Optimierungen | Verschachtelte P03/A06/R10-Formulare, dynamische Vorlagenfelder, CSV-Zuordnung, Leerwertgates, Tastatur-Tabs/Fokus, DST-Offset und Verlassen-Warnung über mehrere Arbeitsbereiche bestanden |
| Statische Prüfungen | Python-Kompilierung, JavaScript-Syntax und gepinnte Ruff-Formatierung bestanden |
| Tatsächliche bisherige Instanz migrieren | Schema 0 nach 2 mit unveränderten Bestandszahlen; Fremdschlüsselprüfung ohne Befund |
| Tatsächliche migrierte DB sichern, prüfen und an neuen Pfad wiederherstellen | Bestanden, Datensatzanzahlen unverändert |
| CI | GitHub-Actions-Konfiguration für Tests/Format/Syntax und separate Browserabnahme hinterlegt; kein erfolgreicher Remote-Lauf allein aus der lokalen Prüfung abgeleitet |

Vor der tatsächlichen Migration wurde eine Sicherung außerhalb des Repositorys
angelegt. Unverändert erhalten blieben 1 Vorgang, 2 Revisionen, 1 Freigabe,
1 Nachweis, 4 Artefakte, 1 Auftrag und 1 Wiederholungsschlüssel. Historische
Metadaten, die vorher nicht gespeichert wurden, werden nicht nachträglich
als bekannt ausgegeben.

Die unabhängige QA fand während der Umsetzung weitere Schnittstellenfälle:
EML-Anhangobjekte und fehlende Message-ID, für READY erforderliche
Orchestrierungsfelder, Teilstring-Verwechslung bei Dokument/Person/Stunden,
leere Nachweisziele und gefälschte SQLite-Schemata mit fehlenden Constraints.
Diese Fälle wurden vor der Abnahme korrigiert und mit Regressionen geprüft.

Server und lokaler Worker wurden auf dem optimierten Stand neu gestartet.
Heartbeat-/Fehlerlogs enthalten technische Zustände; PostgreSQL-Betrieb,
Windows-ACLs, echte Mehrbenutzerrechte und automatische Außenadapter wurden
nicht als geprüft ausgegeben.

## Wiederholen

```sh
.venv/bin/python -m pytest -q -W error
node --check app/static/app.js
.venv/bin/python -m compileall -q app tests
# Gepinntes Quality-Paket optional in eigener Umgebung installieren:
# python -m pip install --require-hashes -r requirements-quality.lock
ruff format --check app tests
```

Für die Browserabnahme Playwright aus `requirements-browser.lock` installieren,
Chromium bereitstellen und eine getrennte lokale Testinstanz starten. Danach
`tests/browser_smoke.py` und `tests/browser_optimizations.py` ausführen.
Beide erzeugen ausschließlich synthetische lokale Datensätze.

## Verbleibende externe Gates

OP07 besitzt eine lokale Manifestprüfung, aber noch keinen echten Fachpilot mit
organisatorisch bestätigten Verantwortlichen, Vorlagen, Datenfreigaben,
Nachweis-/Aufbewahrungsregeln oder gemessener realer Baseline. OP08 ist bedingt
und benötigt bestätigten Bedarf, Betriebsmittel und konkrete Systemrechte.
Ein manuell erfasster Zielbeleg bleibt eine menschliche Attestierung; die App
prüft die externe Quelle nicht automatisch. Details: [Paketstatus](OPTIMIZATION_STATUS.md).
Microsoft Graph und die Übermittlung an die Personalabrechnung bleiben ausgeschlossen.
