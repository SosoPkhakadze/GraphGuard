#!/usr/bin/env python3
"""
Setup real-world evaluation batch for the GraphGuard thesis.
Creates 20 cJSON scenarios spanning narrow → wide blast radii.
Ground truth computed from actual libclang call graph.

Usage: py -3.12 setup_real_eval.py
"""

import os, sys, json, shutil, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analyzer.callgraph import CallGraph
from analyzer.impact    import ImpactAnalyzer

ROOT      = os.path.dirname(os.path.abspath(__file__))
CJSON_DIR = os.path.join(ROOT, "demo_cjson")
BATCH_DIR = os.path.join(ROOT, "batches", "real_world")
CJSON_C   = os.path.join(CJSON_DIR, "cJSON.c")
CJSON_H   = os.path.join(CJSON_DIR, "cJSON.h")


# ── Helpers ───────────────────────────────────────────────────────────────────

def transitive_callers(cg: CallGraph, fn: str, max_depth: int = 20) -> set:
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
    for (path, start, end, fn) in cg._fn_extents:
        if fn == fn_name:
            return path, start, end
    return None


def find_good_line(lines, fn_start, fn_end):
    """
    Find a 0-based line index inside the function body that contains real code
    (assignment, comparison, function call, return with value).
    Skips opening/closing braces, blank lines, pure comment lines.
    Skips the very first non-brace line (often a local variable declaration we
    want to leave alone) and picks the second or third meaningful line.
    """
    # patterns that indicate real code worth "changing"
    CODE_RE = re.compile(
        r'(=|==|!=|<=|>=|\(|\breturn\b|\bif\b|\bwhile\b|\bfor\b)',
        re.IGNORECASE
    )
    candidates = []
    for i in range(fn_start, min(fn_end, len(lines))):
        stripped = lines[i].strip()
        if not stripped or stripped in ("{", "}", "};"):
            continue
        if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
            continue
        if CODE_RE.search(stripped):
            candidates.append(i)
    # return 2nd candidate if possible (skip the very first matching line)
    if len(candidates) >= 2:
        return candidates[1]
    if candidates:
        return candidates[0]
    # absolute fallback: first line of body
    return fn_start


def make_unified_diff(filepath_rel, original_lines, changed_line_idx, old_text, new_text,
                      context=4):
    start = max(0, changed_line_idx - context)
    end   = min(len(original_lines), changed_line_idx + context + 1)

    hunk_old_start = start + 1
    hunk_count     = end - start

    hunk_lines = []
    for i in range(start, end):
        if i == changed_line_idx:
            hunk_lines.append(f"-{original_lines[i]}")
            nt = new_text if new_text.endswith("\n") else new_text + "\n"
            hunk_lines.append(f"+{nt}")
        else:
            hunk_lines.append(f" {original_lines[i]}")

    return (
        f"--- a/{filepath_rel}\n"
        f"+++ b/{filepath_rel}\n"
        f"@@ -{hunk_old_start},{hunk_count} +{hunk_old_start},{hunk_count} @@\n"
        + "".join(hunk_lines)
    )


def make_scenario(name, description, cg, lines, changed_fn, diff_text):
    sd  = os.path.join(BATCH_DIR, name)
    src = os.path.join(sd, "src")
    os.makedirs(src, exist_ok=True)

    shutil.copy(CJSON_C, os.path.join(src, "cJSON.c"))
    shutil.copy(CJSON_H, os.path.join(src, "cJSON.h"))

    with open(os.path.join(sd, "diff.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(diff_text)

    # Build call graph from copied source (same as graphguard does at eval time)
    cg_local = CallGraph()
    cg_local.build([os.path.join(src, "cJSON.c")])

    all_fns  = sorted(cg_local.defined_functions)
    tc       = transitive_callers(cg_local, changed_fn)
    affected = sorted(f for f in tc if f in cg_local.defined_functions)
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

    tc_count = len(affected)
    flag = "" if changed_ok else "  *** NOT FOUND IN GRAPH ***"
    print(f"  {name:<40} changed=[{changed_fn}]  affected={tc_count}{flag}")
    return gt


def build_diff(cg, lines, fn_name, change_note):
    ext = fn_extent(cg, fn_name)
    if not ext:
        print(f"    WARNING: {fn_name} not found in extents — using fallback diff")
        return (f"--- a/src/cJSON.c\n+++ b/src/cJSON.c\n"
                f"@@ -1,1 +1,1 @@\n-/* placeholder */\n+/* {fn_name} changed */\n")
    _, s, e = ext
    idx = find_good_line(lines, s - 1, e - 1)   # fn_extent is 1-based, lines 0-based
    old = lines[idx].rstrip("\n")
    # Make the change visible but syntactically harmless
    new = old + f"  /* CHANGED: {change_note} */"
    return make_unified_diff("src/cJSON.c", lines, idx, old, new)


# ── Scenario definitions ─────────────────────────────────────────────────────
# (fn_name, short_description, change_note)
# Ordered by approximate blast radius (affected functions)

SCENARIOS = [
    # ── Narrow (0-5 affected) ────────────────────────────────────────────────
    ("01_create_reference",
     "cJSON: modified create_reference() — internal helper that wraps item "
     "references. Direct callers: cJSON_AddItemReferenceToArray/Object.",
     "create_reference", "reference flag handling altered"),

    ("02_cJSON_DetachItemViaPointer",
     "cJSON: modified cJSON_DetachItemViaPointer() — lowest-level detach helper "
     "called by all three Detach variants.",
     "cJSON_DetachItemViaPointer", "pointer unlinking logic changed"),

    ("03_get_array_item",
     "cJSON: modified get_array_item() — internal linear scan for array index. "
     "Called by GetArrayItem, DetachItemFromArray, InsertItemInArray, ReplaceItemInArray.",
     "get_array_item", "index boundary check altered"),

    ("04_cJSON_GetObjectItem",
     "cJSON: modified cJSON_GetObjectItem() — public key lookup (case-insensitive). "
     "Called by HasObjectItem and DetachItemFromObject.",
     "cJSON_GetObjectItem", "lookup condition altered"),

    # ── Medium-narrow (6-9 affected) ─────────────────────────────────────────
    ("05_parse_value",
     "cJSON: modified parse_value() — central recursive parse dispatcher. "
     "Called by parse_array, parse_object, and cJSON_ParseWithLengthOpts.",
     "parse_value", "type dispatch condition changed"),

    ("06_parse_array",
     "cJSON: modified parse_array() — parses JSON arrays recursively. "
     "Called by parse_value.",
     "parse_array", "array termination check altered"),

    ("07_parse_object",
     "cJSON: modified parse_object() — parses JSON objects recursively. "
     "Called by parse_value.",
     "parse_object", "object key parsing altered"),

    ("08_parse_string",
     "cJSON: modified parse_string() — parses quoted JSON strings with escape "
     "handling. Called by parse_value and parse_object.",
     "parse_string", "string escape handling altered"),

    ("09_parse_number",
     "cJSON: modified parse_number() — converts JSON number literal to double. "
     "Called by parse_value.",
     "parse_number", "numeric conversion altered"),

    ("10_buffer_skip_whitespace",
     "cJSON: modified buffer_skip_whitespace() — skips whitespace during parse. "
     "Called by parse_array, parse_object, cJSON_ParseWithLengthOpts.",
     "buffer_skip_whitespace", "whitespace detection condition changed"),

    ("11_print_value",
     "cJSON: modified print_value() — central print dispatcher (switch on type). "
     "Called by print_array, print_object, print, cJSON_PrintBuffered, cJSON_PrintPreallocated.",
     "print_value", "type dispatch modified"),

    ("12_print_array",
     "cJSON: modified print_array() — serialises a JSON array recursively. "
     "Called by print_value.",
     "print_array", "array formatting changed"),

    ("13_print_object",
     "cJSON: modified print_object() — serialises a JSON object. "
     "Called by print_value.",
     "print_object", "object key quoting altered"),

    ("14_update_offset",
     "cJSON: modified update_offset() — advances buffer write position after "
     "each token is written. Called by print, print_array, print_object.",
     "update_offset", "offset arithmetic changed"),

    # ── Medium-wide (10-15 affected) ─────────────────────────────────────────
    ("15_compare_double",
     "cJSON: modified compare_double() — epsilon comparison for JSON numbers. "
     "Called by cJSON_Compare and print_number.",
     "compare_double", "epsilon comparison threshold changed"),

    ("16_get_object_item",
     "cJSON: modified get_object_item() — internal object key scan used by "
     "both cJSON_GetObjectItem and cJSON_GetObjectItemCaseSensitive.",
     "get_object_item", "case sensitivity logic altered"),

    ("17_ensure",
     "cJSON: modified ensure() — grows the print output buffer. "
     "Called by every print_ function that writes tokens.",
     "ensure", "growth multiplier reduced"),

    # ── Wide (16-25 affected) ─────────────────────────────────────────────────
    ("18_add_item_to_array",
     "cJSON: modified add_item_to_array() — core array append helper. "
     "Called by cJSON_AddItemToArray, InsertItemInArray, and through add_item_to_object.",
     "add_item_to_array", "tail-pointer update logic changed"),

    ("19_get_decimal_point",
     "cJSON: modified get_decimal_point() — returns locale decimal separator. "
     "Called by parse_number and print_number, which are in both parse and print chains.",
     "get_decimal_point", "locale character lookup altered"),

    ("20_cJSON_strdup",
     "cJSON: modified cJSON_strdup() — internal string duplicator used by every "
     "function that copies string values into JSON items.",
     "cJSON_strdup", "copy length calculation changed"),
]


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    # Clean previous scenarios
    if os.path.isdir(BATCH_DIR):
        for d in os.listdir(BATCH_DIR):
            full = os.path.join(BATCH_DIR, d)
            if os.path.isdir(full):
                shutil.rmtree(full)
            elif os.path.isfile(full):
                os.remove(full)
    os.makedirs(BATCH_DIR, exist_ok=True)

    print("Building cJSON call graph...")
    cg = CallGraph()
    cg.build([CJSON_C])
    print(f"  {len(cg.defined_functions)} functions found.\n")

    with open(CJSON_C, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    print(f"Creating {len(SCENARIOS)} scenarios:")
    for folder, description, fn_name, change_note in SCENARIOS:
        diff = build_diff(cg, lines, fn_name, change_note)
        make_scenario(folder, description, cg, lines, fn_name, diff)

    print(f"\nDone. Run evaluation with:")
    print("  py -3.12 graphguard.py batch batches/real_world --model gpt-4o --agent")


if __name__ == "__main__":
    main()
