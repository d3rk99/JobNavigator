import pytest

from backend.backup_compat import prepare_backup_for_restore


@pytest.mark.parametrize("version,strip", [("16.15", True), ("15.9", True), ("17.11", False)])
def test_dump_prologue_matches_source_server(tmp_path, version, strip):
    header = f"-- Dumped from database version {version}\nSET statement_timeout = 0;\nSET transaction_timeout = 0;\nCREATE TABLE example (value text);\n"
    # A matching string in user data must never be edited.
    data = "COPY example FROM stdin;\nSET transaction_timeout = 0;\n\\.\n"
    path = tmp_path / "backup.sql"
    path.write_text(header + data, encoding="utf-8")
    prepare_backup_for_restore(str(path))
    expected_header = header.replace("SET transaction_timeout = 0;\n", "") if strip else header
    assert path.read_text(encoding="utf-8") == expected_header + data
    prepare_backup_for_restore(str(path))
    assert path.read_text(encoding="utf-8") == expected_header + data


def test_unknown_source_version_is_not_rewritten(tmp_path):
    path = tmp_path / "backup.sql"
    text = "SET transaction_timeout = 0;\n"
    path.write_text(text)
    prepare_backup_for_restore(str(path))
    assert path.read_text() == text
