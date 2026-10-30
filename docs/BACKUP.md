# Lokale SQLite-Sicherung und Wiederherstellung

Alle lokalen Vorgänge, Artefakte und Aufträge liegen in der SQLite-Datei. Die
SQLite-Backup-API sichert einen konsistenten Stand einschließlich bestätigter
WAL-Daten, ohne die aktive Datenbank zu ersetzen.

```sh
.venv/bin/python -m app.backup create --database toolbox.db --output /geschuetzter/pfad/neue-sicherung
.venv/bin/python -m app.backup verify --backup /geschuetzter/pfad/neue-sicherung
.venv/bin/python -m app.backup restore --backup /geschuetzter/pfad/neue-sicherung --output /geschuetzter/pfad/neue-datenbank.db
```

Ausgabeverzeichnis und Restore-Datei müssen neu sein. Es wird nichts Bestehendes
überschrieben. Das Manifest trennt `manifest_format_version` und
`application_schema_version`, speichert SHA-256 und UTC-Erstellzeit. Prüfung
und Restore verlangen Integrität, Fremdschlüsselkonsistenz, Anwendungsidentität,
unterstützte Schemaversion sowie tatsächliche Tabellen, Typaffinitäten, PK/FK
und Unique-Regeln. Eine leere oder fremde Datenbank ist keine gültige Sicherung.
Unterstützte vollständige Legacy-Datenbanken können geprüft und beim späteren
Anwendungsstart auf Schema 2 migriert werden.

Restore prüft die tatsächlich kopierten Bytes und veröffentlicht atomar an
einem neuen Pfad. Danach zunächst in einer isolierten Instanz prüfen und
`TOOLBOX_DATABASE_URL` bewusst umstellen; nie eine laufende DB überschreiben.
Fehler beenden die CLI mit einem nicht-null Exitcode.

Unter POSIX erzeugt die Anwendung die DB privat (0600) und lehnt vorhandene
zu offene DB-/Sidecar-Dateien sowie durch andere Benutzer beschreibbare
Elternverzeichnisse ab. Vorhandene Nutzerdaten werden nicht heimlich verschoben
oder chmod-umgestellt. Unter Windows sind Benutzer-ACLs für die Ablage durch den
Betrieb einzurichten. Eine lokale Sicherung ersetzt weder Verschlüsselung,
Aufbewahrungsregeln, geschützte Offsite-Kopien noch einen betrieblichen Restoreplan.
Ein Hash ohne unabhängige Signatur authentisiert den Ersteller nicht.

Vor der aktuellen Migration wurde die bisherige Instanz außerhalb des
Repositorys unter `/workspace/backups/before-optimizations-20261030` gesichert.
Dieser Pfad gehört nicht zum Git-Commit. In einer anderen Umgebung existiert
er nicht automatisch; dort vor Migration eine eigene Sicherung erstellen.
