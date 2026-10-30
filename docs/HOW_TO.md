# Bedienung und Eingabehilfe

Die API-Beispiele setzen voraus, dass die Anwendung lokal läuft und die Datenbank initialisiert wurde. Alle schreibenden Aufrufe brauchen `X-Toolbox-Request: 1`. Die Beispielwerte sind vollständig synthetisch.

## Eingaben für alle 81 Funktionen

`GET /api/tools` liefert den Katalog. `GET /api/tools/P03` liefert eine Funktion im Einzelnen. Jeder Eintrag besitzt `help.what_it_checks`, `help.sample_status`, `help.sample_input` und `help.input_fields`. `input_fields` beschreibt jeden Beispielpfad, seinen Beispielwert und Typ. Kopiere `sample_input` in einen Test und ändere nur Werte, die für den eigenen Prüffall nötig sind. Fehlende oder ungültige Felder führen zu `NEEDS_DATA`; eine offene Befugnis- oder Sachentscheidung führt typischerweise zu `NEEDS_DECISION`.

```sh
curl http://127.0.0.1:8000/api/tools/P03
curl -X POST http://127.0.0.1:8000/api/tools/P03/test \
  -H 'Content-Type: application/json' -H 'X-Toolbox-Request: 1' \
  --data @payload.json
```

Die zweite Anfrage erzeugt einen lokalen Prüflauf und speichert dessen Artefakte. `GET /api/runs/{run_id}` zeigt das Ergebnis. Ein `READY`-Ergebnis bedeutet nur, dass die übergebenen Werte die lokale Regelprüfung bestanden haben.

## Beispiel: Gehaltsrunde mit Cent-Rundung und Fallnachweis

Das folgende einzelne Personenbeispiel zeigt den vollständigen lokalen Aktenweg für eine genehmigte 2,5-%-Vorschau ab 1. November 2026. 4.000,00 EUR werden mit `ROUND_HALF_UP` zu 4.100,00 EUR berechnet. Der eingebettete Hash bindet die HR-Freigabe an genau diesen Umfang und diese Regelversion.

```json
{
  "round_id": "2026-annual",
  "revision": 1,
  "people": [{
    "person_id": "P-104",
    "old": "4000.00",
    "current": "4000.00",
    "approval": {
      "by": "HR-Verantwortliche:r",
      "scope_hash": "67ff5d9fea76d6cc57ba03ae8ad278bb18b5283511730b750223f9359ee93d39"
    }
  }],
  "valid_from": "2026-11-01",
  "currency": "EUR",
  "basis": "Monat",
  "rule_version": "1",
  "mode": "percentage",
  "percentage": "2.5"
}
```

Der Hash wurde aus dem vom Prüfer gebildeten Umfang berechnet: `round_id`, Revision, Personenkennung, alter und neuer Betrag, Wirksamkeitsbeginn, Währung, Bezugsbasis, Regelversion, Modus, Prozentwert und Rundungsmodus. Eine geänderte Eingabe benötigt eine neue Freigabe.

1. Lege damit einen Fall an und lies die berechnete Vorschau aus. `source_ref` macht denselben Demo-Fall idempotent; nutze für einen neuen Lauf eine neue Referenz.

```python
import json
from urllib.request import Request, urlopen

base = "http://127.0.0.1:8000"
def post(path, body):
    request = Request(
        base + path,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Toolbox-Request": "1"},
        method="POST",
    )
    with urlopen(request) as response:
        return json.load(response)

payload = {
    "round_id": "2026-annual", "revision": 1,
    "people": [{
        "person_id": "P-104", "old": "4000.00", "current": "4000.00",
        "approval": {
            "by": "HR-Verantwortliche:r",
            "scope_hash": "67ff5d9fea76d6cc57ba03ae8ad278bb18b5283511730b750223f9359ee93d39"
        }
    }],
    "valid_from": "2026-11-01", "currency": "EUR", "basis": "Monat",
    "rule_version": "1", "mode": "percentage", "percentage": "2.5"
}
case = post("/api/tools/P03/cases", {
    "title": "Gehaltsrunde P-104",
    "source_ref": "demo-gehaltsrunde-p104",
    "payload": payload,
})
assert case["result"]["status"] == "READY", case["result"]
case_id = case["id"]
```

2. Nachdem die zuständige Rolle den Inhalt geprüft hat, bestätige genau die aktuelle Revision:

```python
post(f"/api/cases/{case_id}/approve", {
    "revision": 1,
    "comment": "Freigabe für die geprüfte Vorschau",
})
```

3. Eine berechtigte HR-Rolle führt die externe Änderung außerhalb des Werkzeugkastens aus und vergleicht den tatsächlich gespeicherten Zielwert manuell mit 4.100,00 EUR. Erfasse den Beleg erst nach dieser Prüfung. Der aktuelle API-Endpunkt bindet `observed` an den Fall-Payload und speichert die Belegreferenz; er nimmt den extern gelesenen Wert nicht separat entgegen und vergleicht ihn nicht selbst. Das folgende Muster wartet bewusst auf eine echte Belegreferenz:

```python
reference = input("Manuell geprüfte HR-Belegreferenz: ").strip()
if not reference:
    raise ValueError("Ohne HR-Rücklesebeleg nicht fortfahren")
post(f"/api/cases/{case_id}/evidence", {
    "revision": 1,
    "kind": "independent_readback",
    "reference": reference,
    "observed": payload,
})
```

4. Schließe nur nach Freigabe, passendem Nachweis und `READY`:

```python
post(f"/api/cases/{case_id}/complete", {"revision": 1})
```

Das Fallende dokumentiert die manuelle Attestierung. Die Anwendung hat keine Gehalts- oder Payroll-Änderung vorgenommen oder extern verifiziert. Wird der Fall geändert, steigt die Revision; alte Freigaben und Nachweise schließen die neue Revision nicht ab.

## Lokalen Auftrag in die Warteschlange stellen

`POST /api/jobs` akzeptiert `tool_id`, `payload` und optional ein ISO-Zeitfeld `due_at` mit Zeitzone. Ohne `due_at` ist der Auftrag sofort fällig. `GET /api/jobs` zeigt den Status. Starte den Worker mit `python -m app.worker --once` oder ohne `--once` für laufendes lokales Polling. Nach Status `DONE` enthält der Auftrag `run_id`; lies das Ergebnis mit `GET /api/runs/{run_id}`. Ein Auftrag ist eine lokale Auswertung und führt keine Mail-, Kalender- oder HR-Systemaktion aus.
