from typing import Any


def row_to_dict(row: Any) -> dict:
    """
    Safely convert a database Row object to a Python dict.
    Works with dicts and row-like objects. Returns empty dict for None.
    """
    if row is None:
        return {}
    if isinstance(row, dict):
        return row
    try:
        return dict(row)
    except Exception:
        try:
            return {key: row[key] for key in getattr(row, "keys", lambda: [])()}
        except Exception:
            return {}


def rows_to_list(rows: Any) -> list:
    """
    Convert a list of database Row objects to a list of dicts.
    """
    if not rows:
        return []
    return [row_to_dict(row) for row in rows]
