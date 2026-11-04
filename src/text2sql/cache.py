"""Simple question -> SQL cache (in-memory, with optional JSON file)."""
import json
from pathlib import Path


def _norm(question):
    return " ".join(str(question).lower().split())


class QueryCache:
    def __init__(self, path=None):
        self.path = Path(path) if path else None
        self._data = {}
        self.hits = 0
        self.misses = 0
        if self.path and self.path.exists():
            try:
                self._data = json.loads(self.path.read_text())
            except Exception:
                self._data = {}

    def get(self, question):
        key = _norm(question)
        if key in self._data:
            self.hits += 1
            return self._data[key]
        self.misses += 1
        return None

    def put(self, question, sql):
        self._data[_norm(question)] = sql
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._data, indent=2))

    def stats(self):
        total = self.hits + self.misses
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hits / total, 4) if total else 0.0,
        }
