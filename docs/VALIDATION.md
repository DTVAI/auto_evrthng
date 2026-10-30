# Validierung vom 30.10.2026

## Ergänzung aus dem unabhängigen Review

Die nachfolgende ursprüngliche Abnahme belegt die geprüften positiven Fälle,
keine allgemeine Fehlerfreiheit. Bei der erneuten Prüfung bestanden dieselben
55 Tests sowie die separate Desktop-/Mobil-Browserprüfung. Zusätzlich wurden
13 gezielte Regressionen aufgenommen, die offene Fehler als strikte erwartete
Fehlschläge reproduzieren. Aktueller Stand: **55 bestanden, 13 xfailed**.
Sie sind nicht behoben und nicht als bestandene Prüfungen zu zählen.
Siehe [Review](REVIEW.md) und [Optimierungsplan](OPTIMIERUNGSPLAN.md).

## Ursprünglicher Prüfumfang

Ausgeführt in dieser Cloud-Instanz mit Python 3.12.14 und Chromium. Alle Daten
waren synthetisch; es wurden keine produktiven Nachrichten oder Personalwerte
gelesen oder verändert.

| Prüfung | Ergebnis |
|---|---|
| `./scripts/setup.sh` mit `requirements.lock` | Bestanden; Installation erneut ausführbar |
| `./scripts/start.sh`, API-Health und Browserzugriff | Bestanden |
| `.venv/bin/python -m pytest -q` | **55 Tests bestanden** |
| Echter API-Durchlauf aller aktiven Tool-Beispiele | **81 von 81** ausgeführt; erwartete offene Entscheidungen bleiben offen |
| `node --check app/static/app.js`, Python-Kompilierung | Bestanden |
| `python tests/browser_smoke.py` | Desktop und Mobil bestanden; keine JavaScript-Laufzeitfehler |
| Lokaler Worker `--once` nach Speicherung im Browser | Persistierter Auftrag ausgeführt; Ergebnis und Artefakt gespeichert |
| Sicherung/Prüfung/Wiederherstellung der echten lokalen Testdatenbank | Bestanden; 1 Vorgang, 2 Revisionen, 4 Artefakte, 1 Nachweis und 1 Auftrag unverändert wiederhergestellt |

Die Browserprüfung deckt Katalogsuche, Hilfetexte, bearbeitete Eingaben,
Prüfergebnis, Download, ungültiges JSON, Vorgangsablage, verweigerten vorzeitigen
Abschluss, Freigabe, manuellen Nachweis, Abschluss, Wiederöffnung durch neue
Revision, Dateiimport und lokale Aufträge ab. Die Wiederherstellung erfolgte
an einen neuen temporären Pfad; die aktive Datenbank wurde nicht überschrieben.

In der Python-Suite erscheint eine DeprecationWarning der TestClient-/AnyIO-
Abhängigkeit. Die Tests wurden vollständig ausgeführt; es gab keine übersprungenen
oder fehlgeschlagenen Tests.

Nicht geprüft und nicht freigeschaltet: produktive Fremdsystemanbindungen,
Mehrbenutzer-Authentisierung und organisatorische Rollenrechte, PostgreSQL-
Parallelbetrieb, gesetzliche Fallentscheidungen, Signaturdienste, verschlüsselte
Offsite-Sicherung und Produktiv-Rollout. Ein manuell eingetragener Rücklesebeleg
ist eine Attestierung durch den lokalen Nutzer. Die App prüft die externe Quelle
nicht automatisch. Die Zuordnung B1–B5 ist keine produktive Phasenabnahme.

Installations- und Startanweisungen wurden als Cloud-Konfigurationsentwurf
gespeichert. Die Veröffentlichung und Wiederherstellung in einer neuen Cloud-
Aufgabe wurden nicht ausgeführt und sind dadurch nicht nachgewiesen.
