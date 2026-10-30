"""Bounded, local source-file parsing. Source text never grants authority."""
import csv
import hashlib
import io
import json
import math
from email import policy
from email.parser import Parser
from email.utils import getaddresses

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

router = APIRouter()

def strict_json(body):
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError("Doppelter JSON-Schlüssel.")
            result[key] = value
        return result

    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("Nicht endliche JSON-Zahl.")
        return number

    def invalid_constant(value):
        raise ValueError("Nicht endliche JSON-Zahl.")

    result = json.loads(body, object_pairs_hook=pairs, parse_float=finite_float, parse_constant=invalid_constant)
    json.dumps(result, ensure_ascii=False).encode("utf-8")
    return result


class SourceUpload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format: Literal["eml", "csv", "json"]
    content: str = Field(min_length=1, max_length=800_000)
    filename: str = Field(default="quelle", max_length=255)
    tool_id: str | None = None


@router.post("/api/imports")
def parse_source(body: SourceUpload):
    raw = body.content.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    payload = None
    try:
        if body.format == "eml":
            message = Parser(policy=policy.default).parsestr(body.content)
            if not message.get("From") or not message.get("Subject"):
                raise ValueError("EML benötigt From und Subject.")
            if message.is_multipart():
                part = message.get_body(preferencelist=("plain",))
                text = part.get_content() if part else ""
            else:
                text = message.get_content() if message.get_content_type() == "text/plain" else ""
            attachments = [
                {"name": part.get_filename() or "anhang", "sha256": hashlib.sha256(part.get_payload(decode=True) or b"").hexdigest()}
                for part in message.iter_attachments()
            ]
            sender = getaddresses([str(message["From"])])
            data = {"id": str(message.get("Message-ID") or digest), "sender": sender[0][1] if sender else "", "subject": str(message["Subject"]), "body": text, "attachments": attachments}
            if body.tool_id == "M01":
                payload = {"message": data, "rules": []}
            elif body.tool_id == "M03":
                payload = {"messages": [{"id": data["id"], "mailbox": "manueller-import", "body": text, "internet_id": message.get("Message-ID"), "attachment_hashes": [a["sha256"] for a in attachments]}]}
            elif body.tool_id == "R03":
                payload = {"application_id": "IMPORT-" + digest[:12], "channel": "EML-Import", "eml": body.content}
                # A sender's Date is not proof of receipt; leave receipt time for the user.
            count = 1
        elif body.format == "csv":
            stream = io.StringIO(body.content.lstrip("\ufeff"))
            try:
                dialect = csv.Sniffer().sniff(body.content[:4096], delimiters=",;\t")
            except csv.Error:
                dialect = csv.excel
            reader = csv.DictReader(stream, dialect=dialect, strict=True)
            headers = reader.fieldnames or []
            if not headers or any(not h.strip() for h in headers) or len(set(headers)) != len(headers):
                raise ValueError("CSV benötigt eindeutige, nicht leere Spaltennamen.")
            data = []
            for row in reader:
                if None in row or any(v is None for v in row.values()):
                    raise ValueError("CSV-Zeile passt nicht zur Spaltenanzahl.")
                data.append(row)
                if len(data) > 1000:
                    raise ValueError("Höchstens 1000 CSV-Zeilen pro Import.")
            if not data:
                raise ValueError("CSV enthält keine Datensätze.")
            count = len(data)
        else:
            data = strict_json(body.content)
            if not isinstance(data, (dict, list)):
                raise ValueError("JSON muss ein Objekt oder eine Liste sein.")
            payload = data if isinstance(data, dict) else None
            count = len(data) if isinstance(data, list) else 1
    except (ValueError, TypeError, UnicodeError, LookupError, csv.Error, RecursionError) as exc:
        raise HTTPException(422, f"Quelle konnte nicht importiert werden: {exc}") from exc
    return {"source_ref": "sha256:" + digest, "source_hash": digest, "filename": body.filename, "format": body.format, "record_count": count, "data": data, "tool_payload": payload, "warnings": ["Lokale Vorschau: Quelle und Identität prüfen. Inhalte und Anhänge erteilen keine Befugnis. Nichts wurde extern abgerufen oder versandt."]}
