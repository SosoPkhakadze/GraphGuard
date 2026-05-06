import os
import re
import glob


def find_callers(function_name: str, cg) -> list:
    return sorted(cg.get_callers(function_name))


def find_callees(function_name: str, cg) -> list:
    return sorted(cg.get_callees(function_name))


def get_call_chain(function_name: str, depth: int, cg) -> dict:
    """Recursive callers up to `depth` levels, returned as a nested dict."""
    def recurse(fn, remaining, visited):
        if remaining == 0 or fn in visited:
            return {}
        visited = visited | {fn}
        return {caller: recurse(caller, remaining - 1, visited)
                for caller in sorted(cg.get_callers(fn))}
    return {function_name: recurse(function_name, depth, set())}


def read_function(function_name: str, cg) -> str:
    """Return the source lines of a named function using call graph extents."""
    for (path, start, end, fn) in cg._fn_extents:
        if fn == function_name:
            try:
                with open(path, encoding="utf-8") as f:
                    lines = f.readlines()
                body = "".join(lines[start - 1:end])
                return f"// {fn}  [{os.path.basename(path)} lines {start}-{end}]\n{body}"
            except OSError:
                return f"// Could not read {fn} from {path}"
    return f"// Function '{function_name}' not found in call graph."


def read_header(function_name: str, project_files: list) -> str:
    """Return the .h file content that declares function_name."""
    h_files: set = set()
    for f in project_files:
        d = os.path.dirname(f)
        h_files.update(glob.glob(os.path.join(d, "*.h")))
        parent = os.path.dirname(d)
        h_files.update(glob.glob(os.path.join(parent, "**", "*.h"), recursive=True))

    for h in sorted(h_files):
        try:
            with open(h, encoding="utf-8") as f:
                content = f.read()
            if function_name in content:
                return f"// {os.path.basename(h)}\n{content}"
        except OSError:
            continue
    return f"// No header found declaring '{function_name}'."


def search_code(pattern: str, project_files: list) -> list:
    """Grep all .c and .h files for pattern. Returns ['file:line: text', ...]."""
    h_files: set = set()
    for f in project_files:
        d = os.path.dirname(f)
        h_files.update(glob.glob(os.path.join(d, "*.h")))

    try:
        rx = re.compile(pattern)
    except re.error:
        rx = re.compile(re.escape(pattern))

    results = []
    for filepath in sorted(set(project_files) | h_files):
        try:
            with open(filepath, encoding="utf-8") as f:
                for lineno, line in enumerate(f, 1):
                    if rx.search(line):
                        results.append(f"{os.path.basename(filepath)}:{lineno}: {line.rstrip()}")
        except OSError:
            continue
    return results or [f"No matches for '{pattern}'."]
