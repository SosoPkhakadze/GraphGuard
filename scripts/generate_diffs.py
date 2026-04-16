#!/usr/bin/env python3
"""
generate_diffs.py

For each project under test_projects/, build the call graph from its new
source files and write diff_with_callgraph.txt alongside diff.txt.

Usage (from project root):
    python scripts/generate_diffs.py
"""

import sys
import os
import glob

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
ANALYZER_DIR = os.path.normpath(os.path.join(SCRIPTS_DIR, "..", "analyzer"))
PROJECTS_DIR = os.path.normpath(os.path.join(SCRIPTS_DIR, "..", "test_projects"))

sys.path.insert(0, ANALYZER_DIR)

from callgraph import CallGraph
from diff_parser import parse as parse_diff
from impact import ImpactAnalyzer
from context_builder import build_diff_with_graph



def process_project(project_dir):
    name = os.path.basename(project_dir)
    src_dir = os.path.join(project_dir, "src")
    diff_file = os.path.join(project_dir, "diff.txt")
    out_file = os.path.join(project_dir, "diff_with_callgraph.txt")

    if not os.path.isfile(diff_file):
        print(f"  [{name}] No diff.txt found — skipping.")
        return

    c_files = sorted(glob.glob(os.path.join(src_dir, "*.c")))
    if not c_files:
        print(f"  [{name}] No .c files in src/ — skipping.")
        return

    print(f"  [{name}] Building call graph from {len(c_files)} file(s)...")

    cg = CallGraph()
    cg.build(c_files)

    with open(diff_file, "r") as f:
        diff_text = f.read()

    # project_dir must be absolute for path resolution to match callgraph paths
    file_to_lines = parse_diff(diff_text, repo_root=os.path.abspath(project_dir))

    analyzer = ImpactAnalyzer(cg)
    changed_fns = analyzer.find_changed_functions(file_to_lines)

    print(f"    Changed  : {sorted(changed_fns)}")

    content = build_diff_with_graph(diff_text, cg, changed_fns)
    with open(out_file, "w") as f:
        f.write(content)
    print(f"    Written  : diff_with_callgraph.txt")


def main():
    projects = sorted([
        os.path.join(PROJECTS_DIR, d)
        for d in os.listdir(PROJECTS_DIR)
        if os.path.isdir(os.path.join(PROJECTS_DIR, d))
    ])

    print(f"Processing {len(projects)} project(s).\n")
    for project_dir in projects:
        process_project(project_dir)
    print("\nDone. Run friend1_analyze.py and friend2_analyze.py next.")


if __name__ == "__main__":
    main()
