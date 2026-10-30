# Review der bisherigen Umsetzung

Stand: 30.10.2026. Geprüft wurden Anwendungskern, sechs Fachmodule, Master-UI,
Dokumentation, Tests, Dateiimport, Worker und lokale Sicherung. Drei unabhängige
Reviews (Terra 6.1 für Backend/Fachlogik, Luna für UI/Dokumentation) wurden mit
einer erneuten Integrationstest- und Browserprüfung zusammengeführt.

## Ergebnis

Die Anwendung ist ein funktionsfähiger lokaler Einplatz-Pilot. Für alle **81
verbleibenden IDs** gibt es ausführbare lokale Prüfer, Berechnungen oder
Entwurfshilfen. Das ist keine abgeschlossene Umsetzung sämtlicher fachlicher
Workflows aus B1–B5. Die frühere Aussage „81 lokale Tools“ trifft zu; sie darf
nicht als produktive Abnahme der 81 Prozesse verstanden werden.

Die bestehende Suite besteht mit **55 Tests**. Zusätzlich wurden **13 gezielte
Regressionstests** aufgenommen, die bekannte Fehler reproduzieren. Diese sind
ausdrücklich `xfail(strict=True, raises=AssertionError)` markiert. Ergebnis:
**55 bestanden, 13 erwartete Fehlschläge, keine unerwarteten Fehlschläge**. Ein
grüner Prozess-Exitcode bedeutet daher ausdrücklich nicht Fehlerfreiheit oder
Produktionsreife. Nach einer Korrektur muss der zugehörige Marker entfernt
werden; ein unerwartetes Bestehen schlägt durch `strict=True` fehl.

Der Desktop-/Mobil-Browserdurchlauf wurde erneut gegen eine getrennte lokale
Instanz mit synthetischer SQLite-Datenbank ausgeführt und bestanden. Er deckt
die positiven Bedienabläufe ab, nicht die vollständige Barrierefreiheit oder
alle hier gefundenen negativen Fälle. JavaScript-Syntaxprüfung und Python-
Kompilierung bestanden ebenfalls.

Diese Änderung liefert Review, reproduzierbare Befunde und Optimierungsplan.
Die unten aufgeführten Anwendungsfehler sind **noch offen**; sie wurden nicht
durch Dokumentation oder erwartete Testfehlschläge behoben. Microsoft Graph
und die Übermittlung an die Personalabrechnung/P13 bleiben ausgeschlossen.

## Befunde und konkrete Auswirkung

P1 bezeichnet eine vor verlässlichem Facheinsatz zu korrigierende
Funktions-/Datenintegritätslücke. P2 bezeichnet eine nachgelagerte Verbesserung
oder Härtung. Es wurde keine produktive Außenwirkung ausgeführt und kein
erfolgreicher Angriff auf eine Produktivinstanz behauptet.

| ID | Priorität | Stelle | Befund / tatsächliches Verhalten | Erwartetes Verhalten und Nachweis |
|---|---|---|---|---|
| F01 | P1 | `app/domains/platform.py:57` und `:77` | T02 akzeptiert eine geänderte Regel bei unveränderter Freigabe, solange Version/Aktion/Scope passen. T05 akzeptiert einen geänderten Payload; dessen Hash wird zwar berechnet, aber nicht mit einer Freigabe verglichen. | Regel- und Intentfreigaben an kanonischen Inhalt, Revision, Aktion, Scope und Gültigkeit binden. Änderung bei gleicher Version muss sperren. Zwei Regressionstests reproduzieren `authority/authorized=True`. |
| F02 | P1 | `app/domains/personnel.py:117` | P07 bindet den Beteiligungsnachweis nur an Vertretung und Entwurfshash. Eine andere Personen-ID und andere Maßnahme bleiben mit demselben Beleg `READY`. | Person, Maßnahme, Entwurf, Regelversion und konkreten Beteiligungsumfang gemeinsam binden. Regressionstest vorhanden. |
| F03 | P1 | `app/domains/recruiting.py:56` | R05 reicht irgendeine passende Kennung. Eine passende E-Mail überstimmt eine widersprechende Personalnummer und führt bei den übergebenen Bestätigungswerten zu einer bestätigten Person. | Widerspruch als Klärfall behandeln, niemals automatisch durch eine andere passende Kennung überstimmen. Regressionstest vorhanden. |
| F04 | P1 | `app/main.py:106`, `:145` und `:162` | Wiederholung derselben Quelle prüft nur den ersten Payload-Hash. Derselbe Tool-/Quellschlüssel mit anderer `subject_id` liefert die bestehende Akte der ersten Person zurück. | Personenbezug in den stabilen Anlagevertrag aufnehmen; widersprechende Identität HTTP 409, auch im konkurrierenden Insert-/Replay-Pfad. API-Regressionstest vorhanden. Titeländerungen separat als Metadatenrevision behandeln. |
| F05 | P1 | `app/domains/recruiting.py:60` | R06 reicht beliebige `approved_fields`, etwa `salary`, ungeprüft als manuellen HR-Auftrag durch. Ein frei übergebener Feldname ersetzt keine zulässige Recruiting-Felddefinition oder Entscheidung. | Aktionsbezogene Feldliste, Typen und Quellen-/Entscheidungsnachweis verlangen; Auftragsvorschau und bestätigten Zielabgleich getrennt ausgeben. Regressionstest mit einem nicht deklarierten Gehaltsfeld vorhanden. |
| F06 | P1 | `app/domains/staffing.py:39` und `app/domains/personnel.py:127` | A03 akzeptiert negative Stunden und negativen Satz, P10 negative Rückkehrstunden, wenn der Benutzer den passenden lokalen Freigabehash mitliefert. | Werte unabhängig von jeder Freigabe validieren: positive Stunden, nichtnegative Sätze und fachlich konfigurierte Obergrenzen. Zwei Regressionstests vorhanden. |
| F07 | P1 | `app/domains/orchestration.py:68` | O01 lässt Ereignisidentität, Quelle und Termin aus dem Aufgabenschlüssel weg; fehlende Ereignisrevision wird zu `1`. Zwei unterschiedliche Ereignistermine erzeugen denselben Schlüssel. | Stabile Ereignis-ID plus explizite Revision verwenden. Echte Wiederholung deduplizieren; neues Ereignis und neue Revision dürfen nicht verschwinden. Regressionstest vorhanden. |
| F08 | P2 | `app/domains/orchestration.py:156` | O14 akzeptiert negative Laufzeiten und berechnet daraus z. B. einen negativen Mittelwert bei `READY`. | Nur endliche, nichtnegative, fachlich vergleichbare Messwerte aggregieren; offene/abgeschlossene Fälle und Nenner ausweisen. Regressionstest vorhanden. |
| F09 | P1 | `app/backup.py:30` und `:57` | Sicherung und Verifikation prüfen SQLite-Struktur, Hash und Fremdschlüssel, aber keine Toolbox-Tabellen oder Anwendungsschemaversion. Eine leere Quelldatei wird als gültige Sicherung akzeptiert. | Falsche/leere Datenbank ablehnen; Anwendungsidentität, unterstützte Schemaversion und erforderliche Tabellen/Spalten vor Backup und Restore prüfen. Regressionstest vorhanden. Dies betrifft falsche Quellen, nicht die bereits nachgewiesene konsistente Sicherung einer richtigen DB. |
| F10 | P1 | `app/worker.py:48` und `:52` | Der Worker hat keine Behandlung vorübergehender Datenbankfehler. Ein Fehler bei Initialisierung oder Polling beendet den Prozess; Folgeaufträge warten ohne Wiederanlauf. | Wiederholbare Fehler isolieren, Transaktion zurückrollen, begrenztes Backoff/Fehlerstatus und Heartbeat vorsehen; permanente Fehler sichtbar beenden. Codebefund; Fault-Injection-Abnahme noch zu bauen. |
| F11 | P1, umgebungsabhängig | `app/db.py:5` | Bei `umask 022` wird eine neue HR-Datenbank als `0644` erzeugt. In einem allgemein zugänglichen Projektverzeichnis könnten andere lokale Konten mitlesen. Die aktuelle Cloud-Instanz verwendet restriktivere Rechte. | Private Datenablage/Dateirechte einschließlich SQLite-Sidecars auf POSIX sicherstellen; unter Windows Benutzer-ACLs festlegen. Subprozess-Regression unter permissiver Umask vorhanden. |
| F12 | P2 | `app/models.py:25`, `app/main.py:185` | Ein neuer Titel überschreibt den Falltitel; historische Revisionen speichern nur den Payload. Der frühere Titel ist aus dem Audit nicht rekonstruierbar. | Revisionsrelevante Metadaten mitversionieren und Vorher-/Nachher-Ansicht anbieten. Codebefund; Audit-Regression ergänzen. |
| F13 | P2 | `app/main.py:266` | Jobzeiten werden auf UTC normalisiert, von SQLite aber ohne Zeitzone zurückgegeben. Die API liefert nach Reload keinen UTC-Offset mehr. | Alle technischen Zeiten als ISO-8601 mit `Z`/Offset serialisieren. Nicht-UTC-Eingabe muss nach Reload denselben Zeitpunkt mit eindeutigem Offset liefern. Regressionstest vorhanden. |
| F14 | P1 | `app/static/app.js:502` | Ein geleertes numerisches Eingabefeld wird mit `Number('')` zu `0` und still in den JSON-Payload geschrieben. Das ist eine unbeabsichtigte fachliche Wertänderung. | Leerzustand erhalten, Validierungsfehler anzeigen und Absenden blockieren bzw. explizite Eingabe verlangen. Codebefund; Browser-Negativtest ergänzen. |
| F15 | P2 | `app/static/app.js:351` und `:470` | Tabs haben keine zugeordneten Tabpanels, keine Pfeil-/Home-/End-Tastensteuerung. Vollständiges Rerendern verliert den Fokus. | Tab-/Panel-Verknüpfung, roving tabindex und gezielte Fokuswiederherstellung; Tastaturtest. Codebefund. |
| F16 | P2 | `app/static/app.js:2` und `:475` | Ungespeicherte Entwürfe existieren nur im Arbeitsspeicher; Reload oder Schließen verliert sie ohne Warnung. Navigation innerhalb derselben Seite funktioniert. | Dirty-State und Verlassen-Warnung, optional bewusst aktivierbare lokale Entwurfsablage mit Löschfunktion. Kein stilles Speichern sensibler HR-Daten im Browser. Codebefund. |
| F17 | P2 | `app/main.py:44` | Die 1-MB-Grenze wird erst nach `await request.body()` geprüft; der komplette Body wurde dann bereits gepuffert. | Streaming-Grenze vor vollständiger Speicherbelegung, zusätzlich Struktur-/Listengrößen begrenzen. Codebefund; keine Last-/Angriffsprüfung durchgeführt. |

## Was die vorhandene Abdeckung tatsächlich belegt

| Paket | Lokale Abdeckung | Wesentliche noch offene Weiterentwicklung |
|---|---|---|
| M01–M15 | Klassifikation, Dubletten-/Konflikterkennung, Fragezustände, Zusagen, Entwürfe, Vergleiche und Übersichten | Persistente gemeinsame Übernahme, tatsächliche serverseitige Suchrechte und bestätigte Quellenverwaltung; Eingaben simulieren heute Teile dieser Zustände. |
| R01–R15 | Kapazität, Bewerbungsimport, Feldprüfung, Identitätsvorschläge, Terminprüfung, fehlende Angaben und Startchecklisten | Widerspruchsfeste Identität, zugelassene HR-Felder, stabile Bewerbungsobjekte und nachvollziehbare manuelle HR-Anlage. |
| P01–P18 ohne P13 | Decimal-Änderungen/Gehaltsrunde, versionierte Entwürfe, Perioden-/Nachweisprüfung und Vertragsvergleich | Einheitliche Entscheidungsbindung, typisierte Sollwerte und dokumentierter Rücklesevergleich; externe Personalmaßnahme bleibt manuell. |
| A01–A08 | Bedarf/Angebote, Auftragsentwurf, Zeiträume, Stunden und positionsweise Rechnungsprüfung | Wertebereichsgates, dauerhaft verbundene Bestell-/Stunden-/Rechnungsobjekte, Korrekturen je Position. |
| O01–O14 | DAG-Rückwärtsplanung, Auswirkungs-/Szenariovorschau, Vertretungs-/Blockeransicht, Regeltests und Metriken | Ereignisidentität, gespeicherter Abhängigkeitsgraph, gemessene Baseline und klare Metrikdefinitionen. |
| T01–T12 + API | Lokale Fakten-/Regel-/Nachweisprüfer, Fälle/Revisionen, Jobqueue, Import und SQLite-Sicherung | Unverwechselbare Schemaversionen, umfassende Befugnisbindung, Wiederanlauf, echte Betriebsgates und später Mehrbenutzerrechte. |

Die API-Beispielprüfung in `tests/test_acceptance.py:30` prüft unter anderem,
dass alle IDs ausführbar sind und kein Beispiel `EXCEPTION` ergibt. Sie prüft
nicht für jedes Tool ein unabhängiges fachliches Sollresultat. Das erklärt,
weshalb die ursprünglichen 55 bestandenen Tests die neuen Fehler nicht
ausgeschlossen haben. Künftige Abnahme muss konkrete Werte und Negativfälle
prüfen, nicht nur Aufrufbarkeit oder einen akzeptierten Status.

## Reproduzieren

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest tests/test_known_review_gaps.py -v -rx
node --check app/static/app.js
```

Für Browserprüfungen eine eigene Testdatenbank/Instanz verwenden:

```bash
TOOLBOX_DATABASE_URL=sqlite:////tmp/hr-review/review.db TOOLBOX_PORT=8011 ./scripts/start.sh
TOOLBOX_TEST_URL=http://127.0.0.1:8011 python tests/browser_smoke.py
```

Das Verzeichnis `/tmp/hr-review` zuvor anlegen. Browserprüfung benötigt
Playwright und Chromium und erzeugt synthetische Fälle/Aufträge. Die
Socket-Beschränkung der Cloud-Sandbox erforderte die normale Tool-Eskalation;
der Paket-/TLS-Schutz wurde nicht abgeschaltet.

Der [Optimierungsplan](OPTIMIERUNGSPLAN.md) ordnet die Befunde in abnehmbare
Arbeitspakete ein. Ein Push dieses Reviews veröffentlicht den Entwicklungsstand,
keine Produktivfreigabe und keine Behebung der offenen Befunde.
