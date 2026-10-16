"""Keep plain SQL dumps restorable on the server that produced their data."""
import os
import re
import shutil
import tempfile
from pathlib import Path


def prepare_backup_for_restore(filename: str) -> None:
    """pg_dump 17 emits transaction_timeout even when dumping a pre-17 server.

    Strip only that unsupported prologue SET, using the source version recorded
    by pg_dump. Never rewrite table data or dumps from PostgreSQL 17 and newer.
    """
    path = Path(filename)
    with path.open(encoding="utf-8", newline="") as source:
        prefix = []
        for _ in range(100):
            line = source.readline()
            if not line:
                break
            prefix.append(line)
            # Everything after the first schema statement is left byte-for-byte.
            if line.startswith(("CREATE ", "ALTER ", "COPY ")):
                break
        version = re.search(r"^-- Dumped from database version (\d+)", "".join(prefix), re.M)
        if not version or int(version.group(1)) >= 17:
            return
        cleaned = [line for line in prefix if line.strip() != "SET transaction_timeout = 0;"]
        if cleaned == prefix:
            return
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=path.parent, delete=False) as target:
                temporary = target.name
                target.writelines(cleaned)
                shutil.copyfileobj(source, target)
        except Exception:
            if temporary:
                os.unlink(temporary)
            raise
    try:
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
