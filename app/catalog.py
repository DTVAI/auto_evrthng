"""Static, locally scoped catalogue of the HR toolbox's 81 process definitions."""
from functools import lru_cache
import json
from pathlib import Path

_DATA = Path(__file__).parent / "data" / "catalog.json"

@lru_cache(maxsize=1)
def catalog():
    """Return process metadata bundled with this application; no external source is read."""
    with _DATA.open(encoding="utf-8") as file:
        return json.load(file)
