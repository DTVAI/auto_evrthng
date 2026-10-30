# Status der Optimierungen

Stand: 30.10.2026. OP01–OP06 sind für den lokalen Einplatz-Pilot implementiert.
Die Abnahme steht in [VALIDATION.md](VALIDATION.md). Kein Paketstatus behauptet
organisatorische Freigaben oder produktive Außenwirkung.

| Paket | Umsetzung / Nachweis | Verbleibende Grenze |
|---|---|---|
| OP01 | Typisierte, begrenzte Verträge für alle 81 Tools; widerspruchsfeste Identität und Quell-Replays; Feldlisten; Geld-/Stundenprüfung. | Fachliche Grenzwerte/Vorlagen müssen für reale Daten bestätigt werden. |
| OP02 | Kanonische lokale Entscheidungsumfänge, Inhaltshashes, Gültigkeit; revisionsgebundene Freigaben und konkrete Sollwertprojektionen. | Manuelle Attestierungen authentisieren keine organisatorische Rolle und prüfen keine externe Quelle. |
| OP03 | SQLite-Schema 2, datenerhaltende Legacy-Migration, private POSIX-Dateien, FK-/PK-/Unique-Prüfung, versionierte Sicherung, UTC-Ausgabe, Streaming-Limits, Worker-Backoff/Quarantäne. | Windows-ACLs, PostgreSQL und produktiver Offsite-Betrieb sind nicht nachgewiesen. |
| OP04 | Verschachtelte Schemaformulare, Listen und Maps, CSV-Zuordnung mit Zeilenfehlern, Leerwertgates, Tastatur-Tabs/Fokus und Verlassen-Warnung. | Kein stilles dauerhaftes Speichern sensibler Browserentwürfe; JSON-Expertenmodus bleibt für komplexe Eingaben. |
| OP05 | Drei persistierte lokale Fallketten mit Schritten/Abhängigkeiten, passenden Fallbelegen, selektiver Invalidierung und Historie; atomare lokale Übernahmen; gemessene Ereigniszähler/Laufzeit. | Aktive Bearbeitungszeit/Wartezeit sind ohne passende Ereignisse bewusst unbekannt. Lokale Identitätslabels sind kein RBAC. |
| OP06 | Normale Regressionen statt xfail, eigene Sollwerte für alle 81 Tools, drei vollständige Fallketten, unabhängige QA, Hash-Locks und CI-Konfiguration. | Ein lokaler Testlauf ist kein ausgeführter GitHub-Actions-Lauf oder Produktiv-Rollout. |
| OP07 | Readiness-Manifest mit init/check, fehlenden Gates und festen Ausschlüssen. | Echter Fachpilot wartet auf benannte Verantwortliche, freigegebene Vorlagen/Daten, Nachweis-/Aufbewahrungsregeln und gemessene Baseline. |
| OP08 | Voraussetzungen und Integrationsgrenzen dokumentiert. | Bedingtes Folgepaket: bestätigter Mehrbenutzerbedarf, Identitätsanbieter, serverseitige Rechte und Tenantzugriff fehlen. Nicht produktiv implementiert. |

Die Befunde F01–F17 sind im lokalen Umfang korrigiert; historische Befunde bleiben
im [Review](REVIEW.md) lesbar. F10 wird über technische Heartbeat-/Fehlerlogs und
Jobstatus beobachtet, nicht über einen vorgetäuschten produktiven Monitor.

Microsoft Graph und die Übermittlung an die Personalabrechnung/P13 bleiben
ausgeschlossen. ANÜ-Rechnungsprüfung ist keine Buchung oder Zahlungsfreigabe.
