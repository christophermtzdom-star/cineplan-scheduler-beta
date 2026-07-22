"""Filtering and sorting helpers independent from Streamlit."""


def sort_rows(rows, field="Nombre", descending=False):
    return sorted(rows, key=lambda row: str(row.get(field, "")).casefold(), reverse=descending)


def filter_rows(rows, category="", status=""):
    return [row for row in rows
            if (not category or row.get("Categoría") == category)
            and (not status or row.get("Estado") == status)]
