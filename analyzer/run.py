"""
GraphGuard – end-to-end pipeline

Experiment:
  A) Claude evaluates the change using the diff only
  B) Claude evaluates the change using the diff + call graph context

Prints both responses so they can be compared.
"""

import os
import sys

from callgraph import CallGraph
from diff_parser import parse as parse_diff
from impact import ImpactAnalyzer
from context_builder import build_diff_only, build_diff_with_graph
from evaluator import Evaluator

# ── paths ────────────────────────────────────────────────────────────────────
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# Source files representing the NEW (post-change) version of the project
NEW_FILES = [
    os.path.join(ROOT, "test", "multi_v2", "math.c"),
    os.path.join(ROOT, "test", "multi_v2", "utils.c"),
    os.path.join(ROOT, "test", "multi_v2", "main.c"),
]

DIFF_FILE = os.path.join(ROOT, "test", "sample.diff")


# ── helpers ───────────────────────────────────────────────────────────────────
def separator(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


# ── pipeline ─────────────────────────────────────────────────────────────────
def main():
    # 1. Build call graph from the new version of the code
    separator("Step 1 – Building call graph")
    cg = CallGraph()
    cg.build(NEW_FILES)

    print("Functions found:")
    for fn in sorted(cg.defined_functions):
        callees = sorted(cg.get_callees(fn))
        callers = sorted(cg.get_callers(fn))
        print(f"  {fn}")
        if callees:
            print(f"    calls:      {callees}")
        if callers:
            print(f"    called by:  {callers}")

    # 2. Parse the diff
    separator("Step 2 – Parsing diff")
    with open(DIFF_FILE, "r") as f:
        diff_text = f.read()

    file_to_lines = parse_diff(diff_text, repo_root=ROOT)
    print("Changed line ranges per file:")
    for path, lines in file_to_lines.items():
        print(f"  {os.path.relpath(path, ROOT)}  lines: {sorted(lines)}")

    # 3. Find changed functions and analyze impact
    separator("Step 3 – Impact analysis")
    analyzer = ImpactAnalyzer(cg)
    changed_fns = analyzer.find_changed_functions(file_to_lines)
    report = analyzer.analyze(changed_fns)

    print(f"Changed functions: {sorted(report.changed_functions)}")
    for fn in sorted(report.changed_functions):
        print(f"\n  {fn}")
        print(f"    direct callers:      {sorted(report.direct_callers[fn])}")
        print(f"    direct callees:      {sorted(report.direct_callees[fn])}")
        trans = report.transitive_callers[fn] - report.direct_callers[fn]
        if trans:
            print(f"    transitive callers: {sorted(trans)}")

    # 4. Build prompts
    separator("Step 4 – Building prompts")
    prompt_a = build_diff_only(diff_text)
    prompt_b = build_diff_with_graph(diff_text, report)

    print(f"Prompt A length: {len(prompt_a)} chars")
    print(f"Prompt B length: {len(prompt_b)} chars  (+call graph context)")

    # 5. Evaluate with Claude
    separator("Step 5 – Querying Claude")
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: Set the ANTHROPIC_API_KEY environment variable to run AI evaluation.")
        print("\nPrompt A (diff only):\n")
        print(prompt_a)
        print("\nPrompt B (diff + graph):\n")
        print(prompt_b)
        sys.exit(1)

    evaluator = Evaluator(api_key=api_key)
    results = evaluator.evaluate(prompt_a, prompt_b)

    # 6. Print comparison
    separator("Result A – Diff only")
    print(results["diff_only"])

    separator("Result B – Diff + Call Graph")
    print(results["diff_with_graph"])

    separator("Done")


if __name__ == "__main__":
    main()
