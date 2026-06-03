#!/usr/bin/env python3
"""
setup_cjson_test.py - build a batch-style project from cJSON so all 4 approaches
can be benchmarked on a real library.

Produces:
    batches/batch_cjson/cjson_demo/src/cJSON.c          (modified)
    batches/batch_cjson/cjson_demo/src/cJSON.h          (verbatim, for context)
    batches/batch_cjson/cjson_demo/diff.txt             (git-style unified)
    batches/batch_cjson/cjson_demo/ground_truth.json    (transitive callers)

The modification: tighten the bounds-check in `parse_value` so it also rejects
buffers where the read offset is already past the end. This is a realistic,
small change that intersects every cJSON_Parse* entry point.
"""
import os
import sys
import json
import shutil
import difflib

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)

from analyzer.callgraph import CallGraph
from analyzer.impact    import ImpactAnalyzer

ORIG_C   = os.path.join(ROOT, "demo_cjson", "cJSON.c")
ORIG_H   = os.path.join(ROOT, "demo_cjson", "cJSON.h")
PROJECT  = os.path.join(ROOT, "batches", "batch_cjson", "cjson_demo")
SRC_DIR  = os.path.join(PROJECT, "src")

OLD_CHUNK = (
    "    if ((input_buffer == NULL) || (input_buffer->content == NULL))\n"
    "    {\n"
    "        return false; /* no input */\n"
    "    }\n"
)
NEW_CHUNK = (
    "    if ((input_buffer == NULL) || (input_buffer->content == NULL) ||\n"
    "        (input_buffer->offset >= input_buffer->length))\n"
    "    {\n"
    "        return false; /* no input or already past end */\n"
    "    }\n"
)


def main():
    os.makedirs(SRC_DIR, exist_ok=True)
    target_c = os.path.join(SRC_DIR, "cJSON.c")
    target_h = os.path.join(SRC_DIR, "cJSON.h")

    # Read source as bytes, normalise CRLF -> LF for both files so the diff and
    # patch logic stay portable.
    with open(ORIG_C, "rb") as f:
        original = f.read().replace(b"\r\n", b"\n").decode("utf-8")
    with open(ORIG_H, "rb") as f:
        header = f.read().replace(b"\r\n", b"\n").decode("utf-8")

    with open(target_h, "w", encoding="utf-8", newline="\n") as f:
        f.write(header)
    if OLD_CHUNK not in original:
        sys.exit("ERROR: anchor chunk not found in cJSON.c — adjust OLD_CHUNK.")
    if original.count(OLD_CHUNK) != 1:
        sys.exit("ERROR: anchor chunk appears more than once.")
    modified = original.replace(OLD_CHUNK, NEW_CHUNK, 1)
    with open(target_c, "w", encoding="utf-8", newline="\n") as f:
        f.write(modified)

    # Unified diff that the diff parser can read
    diff_lines = list(difflib.unified_diff(
        original.splitlines(keepends=True),
        modified.splitlines(keepends=True),
        fromfile="a/src/cJSON.c",
        tofile="b/src/cJSON.c",
        n=3,
    ))
    # Add the "diff --git" header to match other batch projects' diff.txt format
    diff_header = "diff --git a/src/cJSON.c b/src/cJSON.c\n"
    with open(os.path.join(PROJECT, "diff.txt"), "w", encoding="utf-8") as f:
        f.write(diff_header)
        f.writelines(diff_lines)

    # Ground truth: changed_functions + transitive callers from the call graph
    cg = CallGraph()
    cg.build([target_c])
    ia = ImpactAnalyzer(cg)
    changed_functions  = ["parse_value"]
    affected_functions = sorted(ia._all_callers("parse_value"))
    all_functions      = sorted(cg.defined_functions)

    gt = {
        "changed_functions":  changed_functions,
        "affected_functions": affected_functions,
        "all_functions":      all_functions,
    }
    with open(os.path.join(PROJECT, "ground_truth.json"), "w", encoding="utf-8") as f:
        json.dump(gt, f, indent=2)

    print(f"  changed_functions  : {changed_functions}")
    print(f"  affected_functions : {len(affected_functions)} functions")
    for fn in affected_functions:
        print(f"      - {fn}")
    print(f"  all_functions      : {len(all_functions)} total")
    print(f"\n  Project ready at: {os.path.relpath(PROJECT, ROOT)}")
    print(f"\n  To evaluate all 4 approaches:")
    print(f"    py graphguard.py batch batches/batch_cjson --model gpt --agent")


if __name__ == "__main__":
    main()
