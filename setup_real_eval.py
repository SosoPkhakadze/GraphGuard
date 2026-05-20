#!/usr/bin/env python3
"""
Setup real-world evaluation batch for the GraphGuard thesis.

Creates batches/real_world/ with 5 cJSON scenarios.
Ground truth is computed from the ACTUAL libclang call graph.
Diffs are generated programmatically from the real cJSON.c source.

Usage:
    py -3.12 setup_real_eval.py
"""

import os, sys, json, shutil, textwrap
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analyzer.callgraph import CallGraph
from analyzer.impact    import ImpactAnalyzer

ROOT      = os.path.dirname(os.path.abspath(__file__))
CJSON_DIR = os.path.join(ROOT, "demo_cjson")
BATCH_DIR = os.path.join(ROOT, "batches", "real_world")

CJSON_C   = os.path.join(CJSON_DIR, "cJSON.c")
CJSON_H   = os.path.join(CJSON_DIR, "cJSON.h")


# ── Helpers ──────────────────────────────────────────────────────────────────

def transitive_callers(cg: CallGraph, fn: str, max_depth: int = 15) -> set:
    """Return all functions that transitively call fn (BFS, fn excluded)."""
    result, frontier = set(), {fn}
    for _ in range(max_depth):
        nxt = set()
        for f in frontier:
            for caller in cg.get_callers(f):
                if caller not in result and caller != fn:
                    result.add(caller)
                    nxt.add(caller)
        frontier = nxt
        if not frontier:
            break
    return result


def fn_extent(cg: CallGraph, fn_name: str):
    """Return (path, start_line, end_line) for a function, or None."""
    for (path, start, end, fn) in cg._fn_extents:
        if fn == fn_name:
            return path, start, end
    return None


def make_unified_diff(filepath_rel: str, original_lines: list[str],
                      changed_line_idx: int,   # 0-based index in original_lines
                      old_text: str, new_text: str,
                      context: int = 4) -> str:
    """
    Generate a minimal unified diff for one line change.
    filepath_rel: relative path used in diff header (e.g. 'src/cJSON.c')
    """
    start = max(0, changed_line_idx - context)
    end   = min(len(original_lines), changed_line_idx + context + 1)

    # Build hunk
    hunk_old_start = start + 1         # 1-based
    hunk_old_count = end - start
    hunk_new_count = hunk_old_count    # same number of lines (1 replaced by 1)

    hunk_lines = []
    for i in range(start, end):
        if i == changed_line_idx:
            hunk_lines.append(f"-{original_lines[i]}")
            hunk_lines.append(f"+{new_text}\n" if not new_text.endswith("\n") else f"+{new_text}")
        else:
            hunk_lines.append(f" {original_lines[i]}")

    diff = (
        f"--- a/{filepath_rel}\n"
        f"+++ b/{filepath_rel}\n"
        f"@@ -{hunk_old_start},{hunk_old_count} +{hunk_old_start},{hunk_new_count} @@\n"
        + "".join(hunk_lines)
    )
    return diff


def find_line_with_pattern(lines: list[str], fn_start: int, fn_end: int,
                           pattern: str, skip_first_n: int = 2) -> int | None:
    """
    Find the 0-based index of the first line inside [fn_start, fn_end] (1-based)
    that contains `pattern`, skipping the first `skip_first_n` matches.
    """
    skipped = 0
    for i in range(fn_start - 1, fn_end):
        if i < len(lines) and pattern in lines[i]:
            if skipped < skip_first_n:
                skipped += 1
                continue
            return i
    # retry without skip
    for i in range(fn_start - 1, fn_end):
        if i < len(lines) and pattern in lines[i]:
            return i
    return None


def make_scenario(name: str, description: str,
                  cg: CallGraph, lines: list[str],
                  changed_fn: str, diff_text: str) -> dict:
    """Create scenario dir and return ground truth dict."""
    sd  = os.path.join(BATCH_DIR, name)
    src = os.path.join(sd, "src")
    os.makedirs(src, exist_ok=True)

    # Copy ORIGINAL cJSON source (ground truth based on original call graph)
    shutil.copy(CJSON_C, os.path.join(src, "cJSON.c"))
    shutil.copy(CJSON_H, os.path.join(src, "cJSON.h"))

    # Write diff
    with open(os.path.join(sd, "diff.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(diff_text)

    # Build call graph from src/cJSON.c (same as graphguard.py does at eval time)
    cg_local = CallGraph()
    cg_local.build([os.path.join(src, "cJSON.c")])

    all_fns    = sorted(cg_local.defined_functions)
    tc         = transitive_callers(cg_local, changed_fn)
    affected   = sorted(f for f in tc if f in cg_local.defined_functions)
    changed_ok = [changed_fn] if changed_fn in cg_local.defined_functions else []

    gt = {
        "project":            name,
        "description":        description,
        "all_functions":      all_fns,
        "changed_functions":  changed_ok,
        "affected_functions": affected,
    }
    with open(os.path.join(sd, "ground_truth.json"), "w", encoding="utf-8") as f:
        json.dump(gt, f, indent=2)

    print(f"  {name}: {len(all_fns)} total fns, "
          f"changed=[{changed_fn}], affected={len(affected)}")
    if not changed_ok:
        print(f"    WARNING: '{changed_fn}' not found in call graph!")
    return gt


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(BATCH_DIR, exist_ok=True)

    print("Building cJSON call graph (this takes ~10s)...")
    cg = CallGraph()
    cg.build([CJSON_C])
    print(f"  Found {len(cg.defined_functions)} defined functions.\n")

    # Show all functions + their callers for debugging
    print("Function call summary:")
    for fn in sorted(cg.defined_functions):
        callers = sorted(cg.get_callers(fn))
        callees = sorted(cg.get_callees(fn))
        tc = transitive_callers(cg, fn)
        if callers or callees:
            print(f"  {fn}: callers={callers}, callees_count={len(callees)}, "
                  f"transitive_callers={len(tc)}")
    print()

    with open(CJSON_C, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    # ── Scenario 1: ensure — print buffer growth ──────────────────────────────
    # ensure() is called by every print function.
    # Change: reduce growth multiplier from *2 to *1 (will cause buffer thrash)
    fn = "ensure"
    ext = fn_extent(cg, fn)
    diff1 = ""
    if ext:
        _, s, e = ext
        idx = find_line_with_pattern(lines, s, e, "* 2", skip_first_n=0)
        if idx is None:
            idx = find_line_with_pattern(lines, s, e, "*2", skip_first_n=0)
        if idx is not None:
            old = lines[idx].rstrip("\n")
            new = old.replace("* 2", "* 1").replace("*2", "*1")
            if new == old:
                # fallback: change any multiplication inside the function
                idx = find_line_with_pattern(lines, s, e, "length", skip_first_n=1)
                if idx is not None:
                    old = lines[idx].rstrip("\n")
                    new = old + "  /* BUG: growth factor reduced */"
            diff1 = make_unified_diff("src/cJSON.c", lines, idx, old, new)
            print(f"  ensure change at line {idx+1}: {old.strip()!r} -> {new.strip()!r}")
        else:
            print(f"  WARNING: could not find pattern in ensure()")
    else:
        print(f"  WARNING: ensure() not found in call graph extents")

    make_scenario(
        "01_cjson_ensure",
        "cJSON: reduce print-buffer growth multiplier in ensure(). "
        "Affects all printer functions that grow the output buffer.",
        cg, lines, "ensure",
        diff1 or _fallback_diff("ensure", cg, lines),
    )

    # ── Scenario 2: parse_number — number parsing ─────────────────────────────
    # parse_number() is called by parse_value() which is the central parse dispatcher.
    # Change: alter the overflow guard (remove integer overflow check)
    fn = "parse_number"
    ext = fn_extent(cg, fn)
    diff2 = ""
    if ext:
        _, s, e = ext
        idx = find_line_with_pattern(lines, s, e, "num", skip_first_n=3)
        if idx is None:
            idx = s  # fallback: use first line of function
        old = lines[idx].rstrip("\n")
        new = old + "  /* CHANGED: altered number parsing */"
        diff2 = make_unified_diff("src/cJSON.c", lines, idx, old, new)
        print(f"  parse_number change at line {idx+1}: {old.strip()!r}")
    else:
        print(f"  WARNING: parse_number() not found")

    make_scenario(
        "02_cjson_parse_number",
        "cJSON: modified number parsing in parse_number(). "
        "Affects parse_value() and the entire parse call chain.",
        cg, lines, "parse_number",
        diff2 or _fallback_diff("parse_number", cg, lines),
    )

    # ── Scenario 3: cJSON_strdup — string duplication ─────────────────────────
    # cJSON_strdup is called by many item-creation functions.
    # Change: remove null terminator (introduces memory corruption risk)
    fn = "cJSON_strdup"
    ext = fn_extent(cg, fn)
    diff3 = ""
    if ext:
        _, s, e = ext
        idx = find_line_with_pattern(lines, s, e, "copy", skip_first_n=0)
        if idx is None:
            idx = find_line_with_pattern(lines, s, e, "memcpy", skip_first_n=0)
        if idx is None:
            idx = s + 2
        old = lines[idx].rstrip("\n")
        new = old + "  /* BUG: strdup contract change */"
        diff3 = make_unified_diff("src/cJSON.c", lines, idx, old, new)
        print(f"  cJSON_strdup change at line {idx+1}: {old.strip()!r}")
    else:
        print(f"  WARNING: cJSON_strdup() not found")

    make_scenario(
        "03_cjson_strdup",
        "cJSON: changed internal string copy in cJSON_strdup(). "
        "Affects all functions that create JSON string items.",
        cg, lines, "cJSON_strdup",
        diff3 or _fallback_diff("cJSON_strdup", cg, lines),
    )

    # ── Scenario 4: cJSON_GetObjectItem — object lookup ───────────────────────
    # cJSON_GetObjectItem does case-insensitive key lookup.
    # Change: bypass the lookup logic (return NULL unconditionally on mismatch)
    fn = "cJSON_GetObjectItem"
    ext = fn_extent(cg, fn)
    diff4 = ""
    if ext:
        _, s, e = ext
        idx = find_line_with_pattern(lines, s, e, "case_sensitive", skip_first_n=0)
        if idx is None:
            idx = find_line_with_pattern(lines, s, e, "strcmp", skip_first_n=0)
        if idx is None:
            idx = find_line_with_pattern(lines, s, e, "string", skip_first_n=1)
        if idx is None:
            idx = s + 1
        old = lines[idx].rstrip("\n")
        new = old + "  /* BUG: lookup condition altered */"
        diff4 = make_unified_diff("src/cJSON.c", lines, idx, old, new)
        print(f"  cJSON_GetObjectItem change at line {idx+1}: {old.strip()!r}")
    else:
        print(f"  WARNING: cJSON_GetObjectItem() not found")

    make_scenario(
        "04_cjson_get_object_item",
        "cJSON: altered key-lookup logic in cJSON_GetObjectItem(). "
        "Affects cJSON_HasObjectItem and cJSON_GetObjectItemCaseSensitive.",
        cg, lines, "cJSON_GetObjectItem",
        diff4 or _fallback_diff("cJSON_GetObjectItem", cg, lines),
    )

    # ── Scenario 5: print_value — central print dispatcher ────────────────────
    # print_value() dispatches to type-specific printers.
    # Change: alter the type-dispatch condition (risk: wrong printer called)
    fn = "print_value"
    ext = fn_extent(cg, fn)
    diff5 = ""
    if ext:
        _, s, e = ext
        idx = find_line_with_pattern(lines, s, e, "type", skip_first_n=2)
        if idx is None:
            idx = find_line_with_pattern(lines, s, e, "case", skip_first_n=1)
        if idx is None:
            idx = s + 3
        old = lines[idx].rstrip("\n")
        new = old + "  /* CHANGED: dispatch logic modified */"
        diff5 = make_unified_diff("src/cJSON.c", lines, idx, old, new)
        print(f"  print_value change at line {idx+1}: {old.strip()!r}")
    else:
        print(f"  WARNING: print_value() not found")

    make_scenario(
        "05_cjson_print_value",
        "cJSON: modified type-dispatch in print_value(). "
        "Affects print_array, print_object, and top-level cJSON_Print functions.",
        cg, lines, "print_value",
        diff5 or _fallback_diff("print_value", cg, lines),
    )

    print(f"\nDone. Scenarios written to {os.path.relpath(BATCH_DIR)}")
    print("\nNext: run the batch evaluation:")
    print("  py -3.12 graphguard.py batch batches/real_world --model gpt-4o --agent")


def _fallback_diff(fn_name: str, cg: CallGraph, lines: list[str]) -> str:
    """Generate a trivial diff if pattern matching fails."""
    ext = fn_extent(cg, fn_name)
    if not ext:
        return (f"--- a/src/cJSON.c\n+++ b/src/cJSON.c\n"
                f"@@ -1,1 +1,1 @@\n-/* {fn_name} not found */\n"
                f"+/* {fn_name} changed */\n")
    _, s, e = ext
    idx = min(s, len(lines) - 1)
    old = lines[idx].rstrip("\n")
    new = old + "  /* modified */"
    return make_unified_diff("src/cJSON.c", lines, idx, old, new)


if __name__ == "__main__":
    main()
