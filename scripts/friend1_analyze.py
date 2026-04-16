#!/usr/bin/env python3
"""
friend1_analyze.py  —  Friend 1: diff only (no call graph)

For each project in test_projects/, reads diff.txt + full src/ file contents,
sends to Claude, and saves the structured response as friend1_response.json.

Requirements:
    export ANTHROPIC_API_KEY=sk-ant-...
    pip install anthropic

Usage (from project root):
    python scripts/friend1_analyze.py
"""

import sys
import os
import glob
import json
import re

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.normpath(os.path.join(SCRIPTS_DIR, "..", "test_projects"))

import anthropic

MODEL = "claude-sonnet-4-6"

PROMPT_TEMPLATE = """\
You are a senior software engineer reviewing a code change.

=== DIFF ===
{diff_block}

=== FULL SOURCE FILES (current/new state) ===
{files_block}

Based on the information above, respond ONLY with a valid JSON object — \
no markdown fences, no explanation outside the JSON.
Use this exact structure:
{{
  "changed_functions": ["names of functions directly modified in the diff"],
  "affected_functions": ["names of OTHER functions whose behavior may change as a result"],
  "reasoning": "one short paragraph explaining the impact"
}}"""


def build_files_block(src_dir):
    parts = []
    for path in sorted(glob.glob(os.path.join(src_dir, "*.c"))):
        rel = os.path.join("src", os.path.basename(path))
        with open(path) as f:
            content = f.read()
        parts.append(f"--- {rel} ---\n{content}")
    return "\n\n".join(parts)


def parse_json_response(text):
    # Strip markdown code fences if the model wraps the response anyway
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text.strip(), flags=re.MULTILINE)
    return json.loads(text.strip())


def analyze_project(project_dir, client, diff_filename, output_filename, approach_label):
    name = os.path.basename(project_dir)
    diff_file = os.path.join(project_dir, diff_filename)
    out_file = os.path.join(project_dir, output_filename)
    src_dir = os.path.join(project_dir, "src")

    if not os.path.isfile(diff_file):
        print(f"  [{name}] {diff_filename} not found — skipping.")
        return

    with open(diff_file) as f:
        diff_text = f.read()

    files_block = build_files_block(src_dir)
    prompt = PROMPT_TEMPLATE.format(diff_block=diff_text, files_block=files_block)

    print(f"  [{name}] Querying Claude ({approach_label})...")
    msg = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text

    try:
        parsed = parse_json_response(raw)
    except Exception as e:
        print(f"    WARNING: JSON parse failed ({e}) — storing raw text.")
        parsed = {"changed_functions": [], "affected_functions": [], "reasoning": raw}

    result = {
        "project": name,
        "approach": approach_label,
        "changed_functions": parsed.get("changed_functions", []),
        "affected_functions": parsed.get("affected_functions", []),
        "reasoning": parsed.get("reasoning", ""),
        "raw_response": raw,
    }

    with open(out_file, "w") as f:
        json.dump(result, f, indent=2)

    print(f"    Changed  : {result['changed_functions']}")
    print(f"    Affected : {result['affected_functions']}")
    print(f"    Saved    : {output_filename}")


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: Set the ANTHROPIC_API_KEY environment variable.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    projects = sorted([
        os.path.join(PROJECTS_DIR, d)
        for d in os.listdir(PROJECTS_DIR)
        if os.path.isdir(os.path.join(PROJECTS_DIR, d))
    ])

    print(f"Friend 1 (diff only) — {len(projects)} project(s)\n")
    for project_dir in projects:
        analyze_project(
            project_dir, client,
            diff_filename="diff.txt",
            output_filename="friend1_response.json",
            approach_label="diff_only",
        )
    print("\nDone.")


if __name__ == "__main__":
    main()
