"""
Step 6: build the two schema contexts the language model will receive.

- v1 (schema only): table and column names with types, read from the database.
  This is what a team with no documentation can offer.
- v2 (semantic layer): v1 plus the descriptions, grain, rules and limitations
  in semantic/dictionary.yml.

The evaluation compares both, to measure what documentation is worth.
"""
from pathlib import Path

import duckdb
import yaml

DB = "data/waitlist.duckdb"
DICTIONARY = Path("semantic/dictionary.yml")
OUT = Path("context")
GOLD_TABLES = ["dim_list", "dim_clinic", "fact_waitlist", "fact_wait_band"]


def read_schema(con):
    schema = {}
    for table in GOLD_TABLES:
        rows = con.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = ? ORDER BY ordinal_position", [table]).fetchall()
        schema[table] = rows
    return schema


def check_coverage(schema, dictionary):
    """Every column in the database must be documented, and nothing extra."""
    problems = []
    for table, columns in schema.items():
        documented = dictionary["tables"].get(table, {}).get("columns", {})
        in_db = {name for name, _ in columns}
        problems += [f"{table}.{c} is not documented" for c in in_db - set(documented)]
        problems += [f"{table}.{c} is documented but not in the database" for c in set(documented) - in_db]
    if problems:
        raise ValueError("Dictionary out of date:\n  " + "\n  ".join(problems))


def render_v1(schema):
    lines = ["# Database schema (DuckDB)", ""]
    for table, columns in schema.items():
        lines.append(f"## {table}")
        lines += [f"- {name} ({dtype})" for name, dtype in columns]
        lines.append("")
    return "\n".join(lines)


def render_v2(schema, dictionary):
    lines = ["# Database schema (DuckDB) with documentation", ""]
    for table, columns in schema.items():
        info = dictionary["tables"][table]
        lines += [f"## {table}", info["description"], f"Grain: {info['grain']}", ""]
        lines += [f"- {name} ({dtype}): {info['columns'][name]}" for name, dtype in columns]
        lines.append("")
    if dictionary.get("background"):
        lines += ["## Clinical background", *[f"- {item}" for item in dictionary["background"]], ""]
    lines += ["## Rules", *[f"{i}. {rule}" for i, rule in enumerate(dictionary["rules"], 1)], ""]
    lines += ["## Not available in this data", *[f"- {item}" for item in dictionary["not_available"]]]
    lines.append("If a question needs information that is not available, say so instead of answering.")
    return "\n".join(lines)


def main():
    con = duckdb.connect(DB, read_only=True)
    schema = read_schema(con)
    con.close()

    dictionary = yaml.safe_load(DICTIONARY.read_text(encoding="utf-8"))
    check_coverage(schema, dictionary)

    OUT.mkdir(exist_ok=True)
    for name, text in [("schema_v1.md", render_v1(schema)), ("schema_v2.md", render_v2(schema, dictionary))]:
        (OUT / name).write_text(text, encoding="utf-8")
        print(f"{name}: {len(text.split()):,} words")


if __name__ == "__main__":
    main()