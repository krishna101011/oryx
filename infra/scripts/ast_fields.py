"""Read-only AST introspection of the pydantic mirror, used by gen-pydantic.ts
to diff Python class fields against TS interface fields.

Not a generator, not a validator on its own — prints a JSON map of
    { ClassName: { "bases": [...], "fields": [ {name, alias, type, optional} ] } }
for every top-level class in the given file, to stdout. gen-pydantic.ts does
the actual comparison against the TS AST; this script only exposes what
Python's own `ast` module already knows about the file, the same way the
existing `ast.parse(...)` syntax probe in gen-pydantic.ts does.

Usage: python ast_fields.py <path-to-types.py>
"""
import ast
import json
import sys


def _base_names(bases: list[ast.expr]) -> list[str]:
    names = []
    for b in bases:
        if isinstance(b, ast.Name):
            names.append(b.id)
        elif isinstance(b, ast.Subscript) and isinstance(b.value, ast.Name):
            # e.g. Generic[T] -> "Generic"
            names.append(b.value.id)
    return names


def _field_alias(call: ast.Call) -> str | None:
    for kw in call.keywords:
        if kw.arg == "alias" and isinstance(kw.value, ast.Constant):
            return kw.value.value
    return None


def _field_call_has_default(call: ast.Call) -> bool:
    """A bare `Field(alias="x")` carries no default and is still required —
    only `default=`/`default_factory=` (or a positional default, the
    pydantic v1 style this codebase doesn't use) makes the key optional."""
    return any(kw.arg in ("default", "default_factory") for kw in call.keywords)


def extract(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=path)

    out: dict[str, dict] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        fields = []
        for stmt in node.body:
            if not isinstance(stmt, ast.AnnAssign) or not isinstance(stmt.target, ast.Name):
                continue
            alias = None
            if isinstance(stmt.value, ast.Call):
                alias = _field_alias(stmt.value)
                optional = _field_call_has_default(stmt.value)
            else:
                optional = stmt.value is not None
            fields.append({
                "name": stmt.target.id,
                "alias": alias,
                "type": ast.unparse(stmt.annotation),
                "optional": optional,
            })
        out[node.name] = {"bases": _base_names(node.bases), "fields": fields}
    return out


if __name__ == "__main__":
    json.dump(extract(sys.argv[1]), sys.stdout)
