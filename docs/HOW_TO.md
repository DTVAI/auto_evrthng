# Bedienung und konkrete lokale Abläufe

## Tool auswählen und ausprobieren

Die Master-UI bietet 81 Tools mit Suche, Bereichen, B1–B5-Zuordnung, Eingabehilfe
und Testbeispielen. B1–B5 bleibt eine Ausbauzuordnung, keine Produktivabnahme.
Schemabasierte Formulare erlauben auch Listen und verschachtelte Felder;
JSON ist als Expertenmodus verfügbar. Ein geleertes Zahlenfeld wird nicht Null,
sondern bleibt fehlend und blockiert die Prüfung. Ungespeicherte Änderungen
lösen beim Verlassen/Reload eine Browserwarnung aus; sie werden nicht unbemerkt
in dauerhaftem Browserspeicher abgelegt.

Dateien werden lokal eingelesen. EML kann M01/M03/R03 befüllen. Empfangszeit und
Identität müssen gegebenenfalls ergänzt werden. Für CSV die Zielliste und
Spalten explizit zuordnen, Vorschau und Zeilenfehler prüfen, dann übernehmen.
Anhänge/Quellen liefern Fakten, keine ausführbaren Befugnisse.

```sh
curl http://127.0.0.1:8000/api/tools/P03
curl -X POST http://127.0.0.1:8000/api/tools/P03/test \
  -H 'Content-Type: application/json' -H 'X-Toolbox-Request: 1' \
  --data @payload.json
```

`GET /api/tools/{id}` liefert `input_schema`, kanonisches `sample` und Hilfe.
Schreibende API-Aufrufe benötigen den genannten Header. Ungültige Struktur/
Typen ergeben HTTP 422, ein fachlicher Klärfall einen erklärten Toolstatus.
Ein `READY` ist eine bestandene lokale Prüfung, keine externe Aktion.

## Gehaltsrunde als lokale Vorschau

P03 berechnet etwa 2.987,35 EUR plus 2,5 Prozent mit HALF_UP zu **3.062,03 EUR**.
Pflichtfelder sind `round_id`, `revision`, `valid_from`, `currency`, `basis`,
`rule_version`, `mode` und `people`. Bei Prozentmodus kommt `percentage` hinzu;
pro Person `person_id`, `old` und der tatsächlich geprüfte `current`-Ausgangswert.
Das aktuelle synthetische `sample` enthält diese Angaben vollständig.

Ohne passende personenspezifische lokale Attestierung bleibt die Vorschau
`NEEDS_DECISION`. Das Ergebnis nennt `scope` und `scope_hash`. Erst nach einer
bewussten fachlichen Prüfung kann die lokale Attestierung als
`people[n].approval = {"by": "benannte Prüfstelle", "scope_hash": "geprüfter Hash"}`
eingetragen werden. Sie ist keine serverseitig authentisierte Freigabe.
Änderung von Person, Basis, Wert, Datum oder Regelumfang entwertet den Hash.
Ein abweichender `current`-Wert sperrt nur die betroffene Position.

## Vorgang, Freigabe und beobachtetes Ziel

Eine Fallanlage speichert Eingaben, Prüfergebnis, Artefakte und Revision 1.
`source_ref` erlaubt Replay: gleiche Quelle mit anderer Person oder anderen
Anlagedaten ist ein Konflikt. Eine Revision erhält frühere Artefakte und
Metadaten; alte Freigaben und Nachweise schließen sie nicht ab.

Der Fall liefert `expected_observation`, beispielsweise für eine Stundenänderung:

```json
{"person_id":"P1","new":"30","unit":"Stunden/Woche","valid_from":"2027-06-30"}
```

Beim manuell durchgeführten Zielvergleich werden die tatsächlich beobachteten
relevanten Werte mit diesem Ziel verglichen. Nicht den gesamten Antrag samt
Vorherwerten und Freigabemetadaten als Beleg kopieren. Ein einfacher unabhängiger
Entwurfsfall M07 erwartet z. B. `{"draft":"Guten Tag Alex"}`; ein Vertragsentwurf
seinen Dokumenthash, ein Aufgabenplan die tatsächlich berechneten Termine.

API-Weg: `POST /api/tools/{id}/cases`, anschließend
`POST /api/cases/{id}/approve` mit aktueller `revision`. Der Beleg kommt über
`POST /api/cases/{id}/evidence` mit `revision`, `kind: independent_readback`,
einer nichtleeren `reference` und dem tatsächlich geprüften `observed`-Objekt.
`POST /api/cases/{id}/complete` verlangt lokalen Status READY sowie passende
Freigabe und Beobachtung. Die Herkunft eines manuell erfassten Belegs wird
nicht automatisch authentisiert; Abschlussbasis bleibt `manual_attestation`.
Falsche Werte, leeres Ziel und eine falsche Person erlauben keinen Abschluss.

## Drei gespeicherte Fallketten

Unter Fallketten oder `POST /api/workflows` eine Art auswählen:

| Art | Schritte |
|---|---|
| `hours_change` | `change` P02, `draft` P05, `hr_record` P04 |
| `start_shift` | `event` O01, `tasks` O02, `document` P05, `commitments` O13 |
| `staffing_invoice` | `hours` A05, `invoice` A06, `correction` A07 |

Das `payload` ist ein Objekt aus Schrittname und jeweiliger Tooleingabe. Zunächst
kann es leer sein; fehlende Angaben bleiben sichtbar. Für die Stundenkette
müssen Entwurfsfelder `person_id`, `new`, `valid_from` der genehmigten Änderung
entsprechen und als Platzhalter im Dokument tatsächlich verwendet werden.
Die Eintrittskette prüft Person und Ereignistermin, die Rechnungskette die
abgeglichenen Stundenpositionen und dieselbe Rechnungsnummer.

Ein abgeschlossener passender Vorgang wird über
`POST /api/workflows/{id}/steps/{step_id}/attach` mit `revision` und `case_id`
zugeordnet. Offene Voraussetzungen blockieren Folgeschritte. Eine Reklamation
kann schon zu einer abweichenden Rechnung bearbeitet werden; die Gesamtkette
bleibt offen, bis die korrigierte Rechnung belegt ist. Änderungen über
`PATCH /api/workflows/{id}` erhalten Historie und unabhängige fertige Schritte.
Beispiele mit unabhängigen Sollwerten: `tests/test_workflow_chains.py`.

## Übernahmen, Aufträge und Zeiten

Eine lokale Übernahme über `/api/cases/{id}/claim` speichert `identity` und
optional `deputy_for`; eine konkurrierende Übernahme erhält HTTP 409.
`/release` verlangt dasselbe Label. `GET /api/cases?identity=...` filtert die
lokal übernommenen Fälle. Diese Labels sind keine organisatorischen Rechte.

`POST /api/jobs` nimmt `tool_id`, `payload`, optional `due_at` mit Zeitzone und
`idempotency_key` an. Gleicher Schlüssel/Inhalt ist Replay, anderer Inhalt ein
Konflikt. `GET /api/jobs` und `/api/runs/{run_id}` zeigen Status und Ergebnis.
Der lokale Worker startet mit `.venv/bin/python -m app.worker` oder `--once`.
Nach wiederholten Jobfehlern ist `QUARANTINED` sichtbar; temporäre SQLite-Locks
werden mit begrenztem Backoff behandelt. Technische Heartbeats stehen im Log.

Die UI verlangt bei lokaler Berliner Zeiteingabe einen expliziten UTC-Offset,
z. B. `2026-10-25T02:30:00+02:00`. Der Offset wird gegen Europe/Berlin geprüft,
damit die doppelte Uhrzeit beim Zeitwechsel nicht geraten wird. Die API gibt
technische Zeitpunkte mit UTC-Offset aus.
