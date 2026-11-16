"""Who imports what, with lines and names (docs/next-product/RAVEN-MAP.md).

    python scripts/import_graph.py . data/graph.json
"""
import ast
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(sys.argv[1])
OUT = pathlib.Path(sys.argv[2])
TOPS = ("engine", "common", "protocol", "operator_client", "worker_client", "installers", "scripts", "tests")

files = subprocess.run(["git", "ls-files", *TOPS], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split("\n")
py = [f for f in files if f.endswith(".py")]
mods = {}
for f in py:
    p = f[:-3].replace("/", ".")
    p = p.removesuffix(".__init__")
    mods[p] = f


def resolve(name):
    """Longest known module that `name` is, or is inside."""
    parts = name.split(".")
    while parts:
        cand = ".".join(parts)
        if cand in mods:
            return cand
        parts.pop()
    return None


graph = {}
for mod, f in mods.items():
    src = (ROOT / f).read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        graph[mod] = {"file": f, "error": str(exc)}
        continue
    pkg = mod if f.endswith("__init__.py") else mod.rpartition(".")[0]
    edges = []
    top_level = {id(n) for n in tree.body}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                t = resolve(a.name)
                if t:
                    edges.append({"to": t, "line": node.lineno, "names": [], "lazy": id(node) not in top_level})
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                up = pkg.split(".")
                up = up[: len(up) - (node.level - 1)]
                base = ".".join([*up, base]) if base else ".".join(up)
            for a in node.names:
                t = resolve(f"{base}.{a.name}") or resolve(base)
                if t:
                    edges.append({"to": t, "line": node.lineno, "names": [a.name], "lazy": id(node) not in top_level})
    handlers = re.findall(r'@handler\(\s*"([^"]+)"', src)
    commands = re.findall(r'@command\(\s*"([^"]+)"\s*,\s*"([^"]*)"', src)
    calls = sorted(set(re.findall(r'"((?:[a-z_]+)\.(?:[a-z_]+))"', src)))
    graph[mod] = {
        "file": f,
        "lines": src.count("\n") + 1,
        "edges": edges,
        "handlers": handlers,
        "commands": [" ".join(c).strip() for c in commands],
        "strings": calls,
    }

OUT.write_text(json.dumps(graph, indent=1), encoding="utf-8")
print(len(graph), "modules", sum(len(g.get("edges", [])) for g in graph.values()), "edges")
