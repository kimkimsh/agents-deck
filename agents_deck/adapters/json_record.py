import json
from typing import Any, Dict, Iterable, List, Optional


class JsonRecord:
    """Decodes JSONL lines into object records; anything else is skipped."""

    @staticmethod
    def parse(line: bytes) -> Optional[Dict[str, Any]]:
        if not line.strip():
            return None
        try:
            tRecord = json.loads(line)
        except ValueError:
            return None
        return tRecord if isinstance(tRecord, dict) else None

    @staticmethod
    def parseAll(lines: Iterable[bytes]) -> List[Dict[str, Any]]:
        tRecords = []
        for tLine in lines:
            tRecord = JsonRecord.parse(tLine)
            if tRecord is not None:
                tRecords.append(tRecord)
        return tRecords
