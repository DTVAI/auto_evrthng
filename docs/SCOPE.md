# Umfang und Grenzen

## Enthalten

- 81 katalogisierte Prozessfunktionen mit Kategorie, Ausbaustufe, Eingaben, Befugnisgrenze, Prüfschritten, Abschluss- und Wiederanlaufbeschreibung.
- Lokale Fallanlage, Revisionierung, Freigaben, Nachweise, Ereignisprotokoll und Regelprüfungen.
- Manueller lokaler EML-, JSON- und CSV-Dateiimport mit Vorschau; für passende Tools kann der Payload übernommen werden. Es gibt keine automatische Postfachüberwachung oder Extraktion aus beliebigen Anhängen.
- Lokale Antwort- und Dokumententwürfe, Berechnungen, Abgleiche und Berichte. Entwürfe belegen weder Versand noch Unterzeichnung.
- Manuelle Erfassung externer HR-Rücklesungen zur jeweiligen Fallrevision.
- Dauerhafte lokale Auftragswarteschlange mit Fälligkeitszeit, Lease und lokalem Prüflauf; der Worker führt keine Außenwirkung aus.
- Lokale ANÜ-Rechnungsprüfung: Rechnungslinien können gegen erfasste Bestellung, bestätigte Stunden und Konditionen gerechnet und Abweichungen markiert werden. Das ist keine Rechnungsbuchung oder Zahlungsfreigabe.

## Vom Auftrag ausgeschlossen

- P13 „Übergabe an Abrechnung und Rückabgleich“ ist aus dem aktiven Katalog ausgeschlossen.
- Payroll-/Gehaltsabrechnungsübergabe und automatische Abrechnungssystem-Schreib- oder Rücklesefunktionen.
- Microsoft Graph.

## Derzeit nicht implementiert

Die folgenden Funktionen sind keine durch den Nutzer ausgeschlossenen Ziele,
sondern noch nicht eingerichtete Erweiterungen. Der
[Optimierungsplan](OPTIMIERUNGSPLAN.md) nennt deren Voraussetzungen und Reihenfolge.

- Outlook-/COM-Anbindung, automatische Mailbox-Überwachung, automatischer Mailversand oder automatische Gesendet-Ordnerprüfung.
- Live-Verbindungen oder produktive Konten für HRworks/sonstige HR-Systeme, ERP, Kalender, Bewerbungsplattformen, Identitätsanbieter oder Drittsysteme.
- Automatische Buchung/Zahlung, verbindliche Vertragsauslegung, Rechts-/Steuerentscheidung, Auswahlentscheidung oder Vergütungsfreigabe.
- Produktiver KI-Dienst, automatische Extraktion aus beliebigen Anhängen, autonomes Auslösen externer Vorgänge zu Fristen, Mandanten-/Rollenkonfiguration, produktives Hosting, Backup- und Wiederherstellungsbetrieb.

Automatische fachliche Personal-, Vergütungs- und Rechtsentscheidungen sind
auch beim späteren Ausbau nicht durch eine administrative Routinefreigabe gedeckt.

## Abgrenzung bei ANÜ-Rechnungen

A06 bleibt enthalten, weil die positionsweise Prüfung einer Lieferantenrechnung eine lokale fachliche Kontrollfunktion ist. Die Anwendung kann manuell erfasste Rechnungswerte rechnerisch vergleichen und Prüfhinweise erzeugen. Die Buchung, Zahlungsentscheidung und externe Ergebnisprüfung laufen weiterhin manuell in den dafür zuständigen Systemen. Die Bezeichnung „Abrechnung“ im Sinn von Rechnung/Accounting ändert daran nichts und stellt keine Lohn- oder Gehaltsabrechnungsintegration dar.

## Integrationen und Nachweise

Es gibt keinen konfigurierten Live-Adapter. Die Katalogeinträge beschreiben lokale Berechnungs- oder Dokumentationsschritte und führen notwendige Außenaktionen als manuelle Aufgaben. Ein erfolgreicher lokaler Prüflauf, eine Freigabe oder ein gespeicherter Nachweis darf nicht als Beleg einer Systemänderung, Zustellung, Buchung oder Zahlung ausgegeben werden.
