#!/usr/bin/env python3
"""
GraphGuard CLI — AI-powered C code impact analyzer

Usage examples:
  python graphguard.py analyze                        # auto-detect git changes here
  python graphguard.py analyze --model claude         # use Claude instead of GPT
  python graphguard.py analyze --staged               # only staged changes
  python graphguard.py analyze --unpushed             # committed but not yet pushed
  python graphguard.py batch ./batches/batch_01 --model gpt
  python graphguard.py batch ./batches/batch_02 --model claude
  python graphguard.py summary
  python graphguard.py compare
  python graphguard.py config --gpt-key sk-proj-... --claude-key sk-ant-...
"""

import os
import sys
import json
import glob
import subprocess
import argparse

# ── Package path so IDE resolves imports ─────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from analyzer.callgraph       import CallGraph
from analyzer.diff_parser     import parse as parse_diff
from analyzer.impact          import ImpactAnalyzer, algorithmic_predict
from analyzer.context_builder import build_diff_with_graph, build_diff_only
from analyzer.agent           import run_agent

# ── Constants ─────────────────────────────────────────────────────────────────
CONFIG_FILE = os.path.join(ROOT, "graphguard_config.json")

BATCHES = [
    ("batch_01", os.path.join(ROOT, "batches", "batch_01")),
    ("batch_02", os.path.join(ROOT, "batches", "batch_02")),
    ("batch_03", os.path.join(ROOT, "batches", "batch_03")),
    ("batch_04", os.path.join(ROOT, "batches", "batch_04")),
    ("batch_05", os.path.join(ROOT, "batches", "batch_05")),
]

MODEL_ALIASES = {
    "gpt":                       "gpt-4o",
    "gpt4":                      "gpt-4o",
    "gpt-4o":                    "gpt-4o",
    "gpt-mini":                  "gpt-4o-mini",
    "gpt-4o-mini":               "gpt-4o-mini",
    "claude":                    "claude-sonnet-4-6",
    "claude-sonnet":             "claude-sonnet-4-6",
    "claude-sonnet-4-6":         "claude-sonnet-4-6",
    "claude-opus":               "claude-opus-4-7",
    "claude-opus-4-7":           "claude-opus-4-7",
    "claude-haiku":              "claude-haiku-4-5-20251001",
    "claude-haiku-4-5":          "claude-haiku-4-5-20251001",
    "claude-haiku-4-5-20251001": "claude-haiku-4-5-20251001",
}

OPENAI_MODELS    = {"gpt-4o", "gpt-4o-mini"}
ANTHROPIC_MODELS = {"claude-sonnet-4-6", "claude-opus-4-7", "claude-haiku-4-5-20251001"}

PROMPT = """\
You are a senior C software engineer doing a code review. Analyze this change thoroughly.
Respond ONLY with valid JSON — no markdown fences, no explanation:
{{
  "changed_functions": ["functions whose body was directly modified"],
  "structural_changes": ["any struct, typedef, macro, or global variable definitions that changed"],
  "affected_functions": ["functions that call or use anything that changed — include ALL transitive callers you can identify"],
  "bugs_introduced": ["each specific bug or undefined behavior introduced, one string per bug, be concrete: name the variable, line logic, or type"],
  "severity": "low | medium | high | critical",
  "concerns": "2-3 sentences: what exactly changed, what will break at runtime or compile time, and why"
}}

{content}"""


# ── Config ────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_config(cfg: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    print(f"Config saved to {os.path.relpath(CONFIG_FILE)}")


def resolve_model(alias: str) -> str:
    m = MODEL_ALIASES.get(alias.lower())
    if m is None:
        choices = ", ".join(sorted(set(MODEL_ALIASES.values())))
        sys.exit(f"ERROR: Unknown model '{alias}'.\nSupported: {choices}")
    return m


def get_api_client(model: str, cfg: dict, args):
    if model in OPENAI_MODELS:
        key = (getattr(args, "api_key", None)
               or os.environ.get("OPENAI_API_KEY")
               or cfg.get("openai_key"))
        if not key:
            sys.exit("ERROR: OpenAI API key required.\n"
                     "  Set via: python graphguard.py config --gpt-key sk-proj-...\n"
                     "  Or env:  OPENAI_API_KEY=...")
        from openai import OpenAI
        return OpenAI(api_key=key), "openai"

    if model in ANTHROPIC_MODELS:
        key = (getattr(args, "api_key", None)
               or os.environ.get("ANTHROPIC_API_KEY")
               or cfg.get("anthropic_key"))
        if not key:
            sys.exit("ERROR: Anthropic API key required.\n"
                     "  Set via: python graphguard.py config --claude-key sk-ant-...\n"
                     "  Or env:  ANTHROPIC_API_KEY=...")
        import anthropic
        return anthropic.Anthropic(api_key=key), "anthropic"

    sys.exit(f"ERROR: Unrecognized model '{model}'")


# Thesis evaluation uses this simpler prompt so results stay comparable across runs.
PROMPT_BATCH = """\
You are reviewing a C code change to identify impact.
Respond ONLY with valid JSON — no markdown fences, no explanation:
{{"changed_functions": ["directly modified functions"], "affected_functions": ["functions that call or depend on changed functions"], "concerns": "one sentence"}}

{content}"""


# ── AI query ──────────────────────────────────────────────────────────────────

def query_model(content: str, client, provider: str, model: str,
                prompt_template: str = PROMPT) -> dict:
    full_prompt = prompt_template.format(content=content)
    try:
        if provider == "openai":
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": full_prompt}],
                temperature=0,
            )
            text = resp.choices[0].message.content.strip()
        else:
            import anthropic as _anthropic
            try:
                msg = client.messages.create(
                    model=model,
                    max_tokens=1024,
                    messages=[{"role": "user", "content": full_prompt}],
                )
            except _anthropic.AuthenticationError:
                raise RuntimeError(
                    "Invalid Anthropic API key. "
                    "Update it with: python graphguard.py config --anthropic-key <your-key>"
                ) from None
            except _anthropic.BadRequestError as e:
                if "credit balance" in str(e) or "billing" in str(e).lower():
                    raise RuntimeError(
                        "Anthropic API credits exhausted. "
                        "Add credits at console.anthropic.com/settings/billing"
                    ) from None
                raise
            text = msg.content[0].text.strip()
    except RuntimeError:
        raise

    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
    return json.loads(text)


# ── Metrics ───────────────────────────────────────────────────────────────────

def compute_metrics(predicted: set, ground_pos: set, all_fns: set) -> dict:
    tp = predicted & ground_pos
    fp = predicted - ground_pos
    fn = ground_pos - predicted
    tn = (all_fns - ground_pos) - predicted
    n_tp, n_fp, n_fn, n_tn = len(tp), len(fp), len(fn), len(tn)
    prec = n_tp / (n_tp + n_fp) if (n_tp + n_fp) > 0 else 0.0
    rec  = n_tp / (n_tp + n_fn) if (n_tp + n_fn) > 0 else 0.0
    f1   = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    acc  = (n_tp + n_tn) / len(all_fns) if all_fns else 0.0
    return {
        "TP": n_tp, "TN": n_tn, "FP": n_fp, "FN": n_fn,
        "Precision": round(prec, 3), "Recall": round(rec, 3),
        "F1": round(f1, 3), "Accuracy": round(acc, 3),
        "TP_fns": sorted(tp), "FP_fns": sorted(fp), "FN_fns": sorted(fn),
    }


def metrics_line(m: dict) -> str:
    return (f"  TP={m['TP']}  TN={m['TN']}  FP={m['FP']}  FN={m['FN']}  "
            f"Prec={m['Precision']:.3f}  Rec={m['Recall']:.3f}  "
            f"F1={m['F1']:.3f}  Acc={m['Accuracy']:.3f}")


# ── Git helpers ───────────────────────────────────────────────────────────────

def git_run(*args, cwd=None) -> str:
    result = subprocess.run(
        ["git"] + list(args),
        capture_output=True, text=True,
        cwd=cwd or os.getcwd(),
    )
    return result.stdout


def get_git_root(cwd=None) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True,
        cwd=cwd or os.getcwd(),
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def get_diff_text(mode: str, cwd=None) -> str:
    """
    mode:
      'all'      — all uncommitted changes (staged + unstaged)  [default]
      'staged'   — only staged changes
      'unstaged' — only unstaged changes
      'unpushed' — committed but not yet pushed to upstream
    """
    if mode == "staged":
        return git_run("diff", "--cached", cwd=cwd)
    if mode == "unstaged":
        return git_run("diff", cwd=cwd)
    if mode == "unpushed":
        # Check if upstream exists
        upstream = git_run("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}", cwd=cwd).strip()
        if not upstream or upstream.startswith("fatal"):
            print("No upstream branch configured — checking last commit instead.")
            return git_run("diff", "HEAD~1..HEAD", cwd=cwd)
        return git_run("diff", f"{upstream}..HEAD", cwd=cwd)
    # default: all uncommitted
    return git_run("diff", "HEAD", cwd=cwd)


def extract_changed_c_files(diff_text: str, git_root: str) -> list[str]:
    """Return absolute paths of .c/.h files mentioned in the diff."""
    files = []
    for line in diff_text.splitlines():
        if line.startswith("+++ b/") and (line.endswith(".c") or line.endswith(".h")):
            rel = line[len("+++ b/"):]
            files.append(os.path.normpath(os.path.join(git_root, rel)))
    return files


def get_cache_path(changed_files: list[str]) -> str:
    """Return the .graphguard_cache.json path for the project that owns changed_files."""
    root = os.path.dirname(os.path.abspath(changed_files[0]))
    if os.path.basename(root).lower() in ("src", "source", "lib", "libs"):
        root = os.path.dirname(root)
    return os.path.join(root, ".graphguard_cache.json")


EXCLUDE_DIRS = {"test", "tests", "test_", "spec", "specs", "unittest",
                "build", "cmake_build", "out", "dist", "third_party",
                "thirdparty", "vendor", "external", "deps", "unity",
                "googletest", "gtest", "cmocka", "check", "fixture",
                "fuzzing", "fuzz", "fuzzers", "examples", "samples"}

def find_project_c_files(changed_files: list[str]) -> list[str]:
    """
    Given a list of changed .c files, locate the "project root" for each
    (go up one level if the file lives in src/, source/, or lib/) then
    collect all .c files in that subtree, excluding test/build directories.
    """
    search_roots: set[str] = set()
    for f in changed_files:
        d = os.path.dirname(os.path.abspath(f))
        if os.path.basename(d).lower() in ("src", "source", "lib", "libs"):
            d = os.path.dirname(d)
        search_roots.add(d)

    all_c: list[str] = []
    for root in search_roots:
        for path in glob.glob(os.path.join(root, "**", "*.c"), recursive=True):
            parts = os.path.normpath(path).split(os.sep)
            if any(p.lower().rstrip("s") in EXCLUDE_DIRS or p.lower() in EXCLUDE_DIRS
                   for p in parts[len(os.path.normpath(root).split(os.sep)):]):
                continue
            all_c.append(path)
    return list(set(all_c))


# ── Interactive prompt helper ─────────────────────────────────────────────────

def ask_choice(question: str, options: list[tuple[str, str]]) -> str:
    """Print a numbered menu and return the chosen key."""
    print(f"\n{question}")
    for i, (_, label) in enumerate(options, 1):
        print(f"  [{i}] {label}")
    while True:
        raw = input("  > ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1][0]
        for key, _ in options:
            if raw.lower() == key.lower():
                return key
        print(f"  Please enter a number between 1 and {len(options)}.")


# ── Subcommand: analyze (git-aware, interactive) ──────────────────────────────

def cmd_analyze(args, cfg):
    cwd = os.getcwd()

    # ── Step 1: get the diff ──────────────────────────────────────────────────
    if hasattr(args, "diff_file") and args.diff_file:
        with open(args.diff_file, encoding="utf-8") as f:
            diff_text = f.read()
        git_root = cwd
    else:
        git_root = get_git_root(cwd)
        if not git_root:
            sys.exit("ERROR: Not inside a git repository.\n"
                     "  Run from inside a git project, or use --diff <file>.")

        mode = "all"
        if getattr(args, "staged", False):   mode = "staged"
        if getattr(args, "unpushed", False): mode = "unpushed"

        diff_text = get_diff_text(mode, cwd=cwd)
        if not diff_text.strip():
            mode_label = {"all": "uncommitted", "staged": "staged",
                          "unpushed": "unpushed"}[mode]
            print(f"No {mode_label} changes detected.")
            print("Tip: edit a .c/.h file, or use --staged / --unpushed.")
            return

    changed_files = extract_changed_c_files(diff_text, git_root)
    if not changed_files:
        print("No .c or .h files found in the diff.")
        print("  - Stage your files first: git add <files>  then use --staged")
        print("  - Or use an existing diff: graphguard analyze --diff ./diff.txt")
        return

    # ── Step 2: build call graph (always needed — we ask approach after) ──────
    only_c = [f for f in changed_files if f.endswith(".c")]
    scope_files = only_c if only_c else changed_files   # fall back if only .h changed
    all_c_files = find_project_c_files(scope_files)

    print("\n" + "=" * 68)
    print("  GraphGuard  —  C Code Impact Analyzer")
    print("=" * 68)
    rel_changed = [os.path.relpath(f, cwd) for f in changed_files]
    print(f"\n  Detected change(s) in: {rel_changed}")

    print("  Building call graph...", end=" ", flush=True)
    cache_path = get_cache_path(scope_files) if scope_files else None
    cg = CallGraph.load(cache_path, all_c_files) if (cache_path and all_c_files) else None
    if cg:
        print(f"done  ({len(all_c_files)} file(s), from cache)")
    elif all_c_files:
        cg = CallGraph()
        cg.build(all_c_files)
        if cache_path:
            cg.save(cache_path)
        print(f"done  ({len(all_c_files)} file(s) parsed, cache saved)")
    else:
        cg = CallGraph()
        print("done  (no .c files found)")
    file_to_lines = parse_diff(diff_text, repo_root=git_root)
    changed_fns   = ImpactAnalyzer(cg).find_changed_functions(file_to_lines) if all_c_files else set()

    if changed_fns:
        print(f"  Functions directly modified: {sorted(changed_fns)}")
    else:
        print("  No function bodies matched (header-only or declaration change).")

    # ── Step 3: ask approach first (algorithmic skips the model step) ────────
    if getattr(args, "approach", None):
        approach = args.approach
    else:
        approach = ask_choice(
            "Which analysis approach?",
            [
                ("diff",        "Diff only            — AI sees only the code change"),
                ("graph",       "Diff + Call Graph    — AI also sees which functions call which"),
                ("agent",       "Agent                — AI retrieves context iteratively"),
                ("algorithmic", "Algorithmic          — Pure graph traversal, no AI, no API key"),
            ]
        )

    # ── Step 4: ask model only if the approach actually needs one ────────────
    chosen_model_key = None
    client = provider = None
    if approach != "algorithmic":
        if getattr(args, "model", None):
            chosen_model_key = resolve_model(args.model)
        else:
            chosen_model_key = ask_choice(
                "Which AI model would you like to use?",
                [
                    ("gpt-4o",            "GPT-4o          (OpenAI)"),
                    ("gpt-4o-mini",       "GPT-4o mini     (OpenAI, faster)"),
                    ("claude-sonnet-4-6", "Claude Sonnet 4.6  (Anthropic)"),
                    ("claude-opus-4-7",   "Claude Opus 4.7    (Anthropic, most capable)"),
                    ("claude-haiku-4-5-20251001", "Claude Haiku 4.5   (Anthropic, fastest)"),
                ]
            )
        client, provider = get_api_client(chosen_model_key, cfg, args)

    # ── Step 5: query ─────────────────────────────────────────────────────────
    cg_content = build_diff_with_graph(diff_text, cg, changed_fns)

    approach_label = {"diff": "Diff only", "graph": "Diff + Call Graph",
                      "agent": "Agent", "algorithmic": "Algorithmic"}[approach]
    runner_label = chosen_model_key if chosen_model_key else "pure graph traversal"
    print(f"\n  Running {runner_label} ({approach_label})...", end=" ", flush=True)

    try:
        if approach == "diff":
            resp = query_model(build_diff_only(diff_text), client, provider, chosen_model_key)
        elif approach == "graph":
            resp = query_model(cg_content, client, provider, chosen_model_key)
        elif approach == "algorithmic":
            from analyzer.impact import algorithmic_predict
            resp = algorithmic_predict(changed_fns, cg)
        else:
            print()  # newline before agent tool call log
            resp = run_agent(diff_text, changed_fns, cg, all_c_files, client, chosen_model_key,
                             provider=provider, cg_content=cg_content)
    except RuntimeError as e:
        print(f"\n  ERROR: {e}", flush=True)
        return
    if approach != "agent":
        print("done")

    # ── Step 6: display result ────────────────────────────────────────────────
    div  = "=" * 68
    div2 = "-" * 68
    changed_out    = sorted(resp.get("changed_functions",  []))
    structural_out = resp.get("structural_changes", [])
    affected_out   = sorted(resp.get("affected_functions", []))
    bugs_out       = resp.get("bugs_introduced", [])
    severity       = resp.get("severity", "unknown").upper()
    concerns       = resp.get("concerns", "")

    severity_marker = {"LOW": "[LOW]", "MEDIUM": "[MEDIUM]",
                       "HIGH": "[HIGH]", "CRITICAL": "[CRITICAL]"}.get(severity, f"[{severity}]")

    print(f"\n{div}")
    print(f"  IMPACT ANALYSIS RESULT")
    print(f"  Model    : {chosen_model_key or '— (no AI used)'}")
    print(f"  Approach : {approach_label}")
    print(f"  Severity : {severity_marker}")
    print(div)

    print(f"\n  FUNCTIONS DIRECTLY MODIFIED")
    print(div2)
    for fn in changed_out:
        print(f"    - {fn}")
    if not changed_out:
        print("    (none identified)")

    if structural_out:
        print(f"\n  STRUCTURAL CHANGES  (types / structs / macros / globals)")
        print(div2)
        for s in structural_out:
            print(f"    - {s}")

    print(f"\n  WHAT WILL BE AFFECTED")
    print(div2)
    for fn in affected_out:
        print(f"    - {fn}")
    if not affected_out:
        print("    (none — change appears self-contained)")

    if bugs_out:
        print(f"\n  BUGS / RISKS INTRODUCED")
        print(div2)
        for bug in bugs_out:
            print(f"    ! {bug}")

    print(f"\n  SUMMARY")
    print(div2)
    print(f"    {concerns}")

    tool_log = resp.get("_tool_log", [])
    if tool_log:
        print(f"\n  TOOLS CALLED BY AGENT")
        print(div2)
        for i, t in enumerate(tool_log, 1):
            print(f"    {i}. {t}")

    if approach == "diff" and all_c_files:
        print(f"\n  TIP: Re-run and choose 'Diff + Call Graph' to see if the")
        print(f"       call graph reveals additional affected functions.")
    elif approach == "graph" and all_c_files:
        print(f"\n  TIP: Re-run and choose 'Agent' for iterative analysis that")
        print(f"       can also detect contract violations and function pointers.")

    print(f"\n{div}\n")

    # ── Step 7: optionally save ───────────────────────────────────────────────
    if getattr(args, "save", False):
        out = os.path.join(cwd, "graphguard_analysis.txt")
        lines = [
            div, "GraphGuard Impact Analysis",
            f"Model    : {chosen_model_key}",
            f"Approach : {approach_label}",
            div, "",
            "WHAT CHANGED", div2,
        ] + [f"  - {fn}" for fn in changed_out] + [
            "", "WHAT MIGHT BE AFFECTED", div2,
        ] + [f"  - {fn}" for fn in affected_out] + [
            "", "CONCERNS / RISKS", div2,
            f"  {concerns}", "", div, "",
        ]
        with open(out, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"  Analysis saved -> {os.path.relpath(out)}")


# ── Per-project processing (for batch/thesis mode) ────────────────────────────

def process_project(project_dir: str, client, provider: str, model: str,
                    out_suffix: str = "", run_agent_eval: bool = False) -> dict | None:
    name      = os.path.basename(project_dir)
    src_dir   = os.path.join(project_dir, "src")
    diff_file = os.path.join(project_dir, "diff.txt")
    gt_file   = os.path.join(project_dir, "ground_truth.json")
    cg_file   = os.path.join(project_dir, "diff_with_callgraph.txt")
    eval_file = os.path.join(project_dir, f"evaluation{out_suffix}.txt")

    for path in [diff_file, gt_file]:
        if not os.path.isfile(path):
            print(f"  [{name}] Missing {os.path.basename(path)} — skipping.")
            return None

    c_files = sorted(glob.glob(os.path.join(src_dir, "*.c")))
    if not c_files:
        print(f"  [{name}] No .c files in src/ — skipping.")
        return None

    print(f"  [{name}] Building call graph ({len(c_files)} file(s))...")
    cg = CallGraph()
    cg.build(c_files)

    with open(diff_file, encoding="utf-8") as f:
        diff_text = f.read()

    file_to_lines = parse_diff(diff_text, repo_root=os.path.abspath(project_dir))
    changed_fns   = ImpactAnalyzer(cg).find_changed_functions(file_to_lines)
    cg_content    = build_diff_with_graph(diff_text, cg, changed_fns)

    with open(cg_file, "w", encoding="utf-8") as f:
        f.write(cg_content)

    with open(gt_file, encoding="utf-8") as f:
        gt = json.load(f)
    all_fns = set(gt["all_functions"])
    gt_pos  = set(gt["changed_functions"]) | set(gt["affected_functions"])

    def predicted_set(resp):
        return (set(resp.get("changed_functions", [])) |
                set(resp.get("affected_functions", []))) & all_fns

    model_label = f"{provider.upper()} / {model}"
    print(f"  [{name}] Querying {model_label} (Baseline)...")
    r1 = query_model(build_diff_only(diff_text), client, provider, model, PROMPT_BATCH)

    print(f"  [{name}] Querying {model_label} (Context-Augmented)...")
    r2 = query_model(cg_content, client, provider, model, PROMPT_BATCH)

    m1 = compute_metrics(predicted_set(r1), gt_pos, all_fns)
    m2 = compute_metrics(predicted_set(r2), gt_pos, all_fns)

    # ── Agent-Based — opt-in, works with any provider ───────────────────
    m3 = r3 = None
    if run_agent_eval:
        print(f"  [{name}] Querying {model_label} (Agent-Based)...")
        try:
            raw3 = run_agent(diff_text, changed_fns, cg, c_files, client, model,
                             provider=provider, cg_content=cg_content)
            r3   = raw3
            m3   = compute_metrics(predicted_set(raw3), gt_pos, all_fns)
        except RuntimeError as e:
            print(f"  [{name}] Agent error: {e} — skipping Agent-Based.")

    # ── Algorithmic — pure graph traversal, no LLM, always-on ─────
    print(f"  [{name}] Computing Algorithmic...")
    r4 = algorithmic_predict(changed_fns, cg)
    m4 = compute_metrics(predicted_set(r4), gt_pos, all_fns)

    # ── Winner among the LLM friends (algorithmic excluded from "winner") ────
    scores = [m1["F1"], m2["F1"]] + ([m3["F1"]] if m3 else [])
    best   = max(scores)
    if m3 and m3["F1"] == best and m3["F1"] > m2["F1"]:
        winner = "Agent-Based"
    elif m2["F1"] == best and m2["F1"] > m1["F1"]:
        winner = "Context-Augmented"
    elif m1["F1"] == best and m1["F1"] > m2["F1"]:
        winner = "Baseline (diff only)"
    else:
        winner = "Tie"

    div  = "=" * 72
    div2 = "-" * 72
    lines = [
        div, f"Project : {name}  [{model_label}]", div, "",
        "GROUND TRUTH",
        f"  Changed  : {sorted(gt['changed_functions'])}",
        f"  Affected : {sorted(gt['affected_functions'])}",
        f"  All fns  : {sorted(gt['all_functions'])}",
        "", div2, "APPROACH 1 - BASELINE (diff only)", div2,
        f"  Predicted changed  : {sorted(r1.get('changed_functions', []))}",
        f"  Predicted affected : {sorted(r1.get('affected_functions', []))}",
        f"  Concerns : {r1.get('concerns', '')}",
        metrics_line(m1),
    ]
    if m1["FP_fns"]: lines.append(f"  False alarms : {m1['FP_fns']}")
    if m1["FN_fns"]: lines.append(f"  Missed       : {m1['FN_fns']}")
    lines += [
        "", div2, "APPROACH 2 - CONTEXT-AUGMENTED (diff + call graph)", div2,
        f"  Predicted changed  : {sorted(r2.get('changed_functions', []))}",
        f"  Predicted affected : {sorted(r2.get('affected_functions', []))}",
        f"  Concerns : {r2.get('concerns', '')}",
        metrics_line(m2),
    ]
    if m2["FP_fns"]: lines.append(f"  False alarms : {m2['FP_fns']}")
    if m2["FN_fns"]: lines.append(f"  Missed       : {m2['FN_fns']}")

    if m3 and r3:
        tool_log = r3.get("_tool_log", [])
        lines += [
            "", div2, "APPROACH 3 - AGENT-BASED (iterative tool calls)", div2,
            f"  Tools called   : {', '.join(tool_log) if tool_log else '(none recorded)'}",
            f"  Predicted changed  : {sorted(r3.get('changed_functions', []))}",
            f"  Predicted affected : {sorted(r3.get('affected_functions', []))}",
            f"  Concerns : {r3.get('concerns', '')}",
            metrics_line(m3),
        ]
        if m3["FP_fns"]: lines.append(f"  False alarms : {m3['FP_fns']}")
        if m3["FN_fns"]: lines.append(f"  Missed       : {m3['FN_fns']}")
        f3_summary = f"    Agent-Based F1 = {m3['F1']:.3f}"
    else:
        f3_summary = ""

    lines += [
        "", div2, "APPROACH 4 - ALGORITHMIC (pure graph traversal, no LLM)", div2,
        f"  Predicted changed  : {sorted(r4.get('changed_functions', []))}",
        f"  Predicted affected : {sorted(r4.get('affected_functions', []))}",
        metrics_line(m4),
    ]
    if m4["FP_fns"]: lines.append(f"  False alarms : {m4['FP_fns']}")
    if m4["FN_fns"]: lines.append(f"  Missed       : {m4['FN_fns']}")
    f4_summary = f"    Algorithmic F1 = {m4['F1']:.3f}"

    lines += [
        "", div, f"WINNER : {winner}",
        f"  Baseline F1 = {m1['F1']:.3f}    Context-Augmented F1 = {m2['F1']:.3f}"
        f"{f3_summary}{f4_summary}",
        div, "",
    ]

    with open(eval_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    f3_str = f"  F3={m3['F1']:.3f}" if m3 else ""
    f4_str = f"  F4={m4['F1']:.3f}"
    print(f"  [{name}] {os.path.basename(eval_file)} written "
          f"(F1={m1['F1']:.3f}  F2={m2['F1']:.3f}{f3_str}{f4_str}  Winner: {winner})")
    result = {"project": name, "baseline": m1, "context_augmented": m2, "algorithmic": m4}
    if m3:
        result["agent_based"] = m3
    return result


# ── Batch results writer ───────────────────────────────────────────────────────

def write_batch_results(results: list, batch_dir: str, model: str,
                        batch_label: str = "", out_suffix: str = ""):
    valid      = [r for r in results if r]
    has_agent  = any("agent_based" in r for r in valid)
    COL        = 24
    header     = (f"{'Project':<{COL}} | {'Approach':<22} | "
                  f"{'TP':>4} {'TN':>4} {'FP':>4} {'FN':>4} | "
                  f"{'Prec':>6} {'Rec':>6} {'F1':>6} {'Acc':>6}")
    sep        = "-" * len(header)
    lines      = [
        f"Batch : {batch_label or os.path.basename(batch_dir)}",
        f"Model : {model}",
        f"Projects evaluated : {len(valid)}/{len(results)}",
        "", header, sep,
    ]
    f1_list, f2_list, f3_list, f4_list = [], [], [], []
    for r in valid:
        rows = [
            ("Baseline (diff only)",  r["baseline"], f1_list),
            ("Context-Augmented", r["context_augmented"], f2_list),
        ]
        if "agent_based" in r:
            rows.append(("Agent-Based", r["agent_based"], f3_list))
        if "algorithmic" in r:
            rows.append(("Algorithmic", r["algorithmic"], f4_list))
        for label, m, lst in rows:
            lst.append(m["F1"])
            lines.append(
                f"{r['project']:<{COL}} | {label:<22} | "
                f"{m['TP']:>4} {m['TN']:>4} {m['FP']:>4} {m['FN']:>4} | "
                f"{m['Precision']:>6.3f} {m['Recall']:>6.3f} "
                f"{m['F1']:>6.3f} {m['Accuracy']:>6.3f}"
            )
        lines.append(sep)

    def avg(lst): return sum(lst) / len(lst) if lst else 0.0
    d12  = avg(f2_list) - avg(f1_list)
    lines += [
        "",
        f"{'Avg F1  Baseline (diff only)   :':<42} {avg(f1_list):.3f}",
        f"{'Avg F1  Context-Augmented  :':<42} {avg(f2_list):.3f}",
        f"{'Delta (Context-Augmented - Baseline)    :':<42} {'+' if d12>=0 else ''}{d12:.3f}",
    ]
    if has_agent and f3_list:
        d23 = avg(f3_list) - avg(f2_list)
        lines += [
            f"{'Avg F1  Agent-Based       :':<42} {avg(f3_list):.3f}",
            f"{'Delta (Agent-Based - Context-Augmented)    :':<42} {'+' if d23>=0 else ''}{d23:.3f}",
        ]
    if f4_list:
        d42 = avg(f4_list) - avg(f2_list)
        lines += [
            f"{'Avg F1  Algorithmic :':<42} {avg(f4_list):.3f}",
            f"{'Delta (Algorithmic - Context-Augmented)    :':<42} {'+' if d42>=0 else ''}{d42:.3f}",
        ]
    lines.append("")
    out_path = os.path.join(batch_dir, f"batch_results{out_suffix}.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nBatch results saved -> {os.path.relpath(out_path)}")
    for line in lines:
        print(line)


# ── Subcommand: batch ──────────────────────────────────────────────────────────

def cmd_batch(args, cfg):
    model    = resolve_model(args.model)
    client, provider = get_api_client(model, cfg, args)
    out_suffix = "" if provider == "openai" else f"_{provider}"
    run_agent_eval = getattr(args, "agent", False)

    if run_agent_eval:
        print(f"Agent evaluation enabled — Agent-Based will run with {model}.")

    batch_dir = os.path.abspath(args.batch_dir)
    if not os.path.isdir(batch_dir):
        sys.exit(f"ERROR: Batch directory not found: {batch_dir}")

    projects = sorted([
        os.path.join(batch_dir, d)
        for d in os.listdir(batch_dir)
        if os.path.isdir(os.path.join(batch_dir, d))
    ])

    batch_label = os.path.relpath(batch_dir, ROOT)
    print(f"Batch : {batch_label}")
    print(f"Model : {model}")
    print(f"Projects found : {len(projects)}\n")

    results = []
    for pdir in projects:
        try:
            results.append(process_project(pdir, client, provider, model, out_suffix, run_agent_eval))
        except Exception as e:
            print(f"  [{os.path.basename(pdir)}] ERROR: {e}")
            results.append(None)

    write_batch_results(results, batch_dir, model, batch_label, out_suffix)


# ── Subcommand: algorithmic ───────────────────────────────────────────────────
#
# Pure graph-traversal evaluation — no LLM, no API key. Iterates every batch's
# projects, builds the call graph, predicts the affected set with
# `algorithmic_predict`, and writes a small `evaluation_algorithmic.txt` per
# project plus a `batch_results_algorithmic.txt` per batch.

def _run_algorithmic_for_project(project_dir: str) -> dict | None:
    name      = os.path.basename(project_dir)
    src_dir   = os.path.join(project_dir, "src")
    diff_file = os.path.join(project_dir, "diff.txt")
    gt_file   = os.path.join(project_dir, "ground_truth.json")
    out_file  = os.path.join(project_dir, "evaluation_algorithmic.txt")

    for path in [diff_file, gt_file]:
        if not os.path.isfile(path):
            print(f"  [{name}] missing {os.path.basename(path)} — skipping.")
            return None

    c_files = sorted(glob.glob(os.path.join(src_dir, "*.c")))
    if not c_files:
        print(f"  [{name}] no .c files — skipping.")
        return None

    cg = CallGraph()
    cg.build(c_files)

    with open(diff_file, encoding="utf-8") as f:
        diff_text = f.read()
    file_to_lines = parse_diff(diff_text, repo_root=os.path.abspath(project_dir))
    changed_fns   = ImpactAnalyzer(cg).find_changed_functions(file_to_lines)

    with open(gt_file, encoding="utf-8") as f:
        gt = json.load(f)
    all_fns = set(gt["all_functions"])
    gt_pos  = set(gt["changed_functions"]) | set(gt["affected_functions"])

    pred = algorithmic_predict(changed_fns, cg)
    predicted = (set(pred["changed_functions"]) |
                 set(pred["affected_functions"])) & all_fns
    m = compute_metrics(predicted, gt_pos, all_fns)

    div  = "=" * 72
    div2 = "-" * 72
    lines = [
        div, f"Project : {name}  [ALGORITHMIC — pure graph traversal]", div, "",
        "GROUND TRUTH",
        f"  Changed  : {sorted(gt['changed_functions'])}",
        f"  Affected : {sorted(gt['affected_functions'])}",
        f"  All fns  : {sorted(gt['all_functions'])}",
        "", div2, "APPROACH 4 - ALGORITHMIC (pure graph traversal, no LLM)", div2,
        f"  Predicted changed  : {sorted(pred['changed_functions'])}",
        f"  Predicted affected : {sorted(pred['affected_functions'])}",
        metrics_line(m),
    ]
    if m["FP_fns"]: lines.append(f"  False alarms : {m['FP_fns']}")
    if m["FN_fns"]: lines.append(f"  Missed       : {m['FN_fns']}")
    lines += ["", div, ""]

    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  [{name}] F1={m['F1']:.3f}  TP={m['TP']} FP={m['FP']} FN={m['FN']}")
    return {"project": name, "metrics": m}


def cmd_algorithmic(args, cfg):
    batches_root = os.path.abspath(args.batch_dir) if args.batch_dir else os.path.join(ROOT, "batches")
    if not os.path.isdir(batches_root):
        sys.exit(f"ERROR: directory not found: {batches_root}")

    # If user passed a single batch directly, treat it as a batch. Otherwise
    # iterate every batch_* subdirectory inside batches/.
    if os.path.basename(batches_root).startswith("batch_"):
        batch_dirs = [batches_root]
    else:
        batch_dirs = sorted(
            d for d in glob.glob(os.path.join(batches_root, "batch_*"))
            if os.path.isdir(d)
        )
    if not batch_dirs:
        sys.exit("ERROR: no batch_* directories found.")

    overall_f1: list[float] = []
    for bdir in batch_dirs:
        label = os.path.basename(bdir)
        print(f"\nBatch : {label}")
        projects = sorted(d for d in glob.glob(os.path.join(bdir, "*"))
                          if os.path.isdir(d))
        rows = []
        for pdir in projects:
            try:
                r = _run_algorithmic_for_project(pdir)
                if r:
                    rows.append(r)
            except Exception as e:
                print(f"  [{os.path.basename(pdir)}] ERROR: {e}")

        if not rows:
            continue
        avg = sum(r["metrics"]["F1"] for r in rows) / len(rows)
        overall_f1.extend(r["metrics"]["F1"] for r in rows)

        header = "Project                  |   TP   TN   FP   FN |   Prec    Rec     F1    Acc"
        sep = "-" * len(header)
        lines = [
            f"Batch : {label}", "Approach : Algorithmic",
            f"Projects evaluated : {len(rows)}", "", header, sep,
        ]
        for r in rows:
            m = r["metrics"]
            lines.append(
                f"{r['project']:<24} | {m['TP']:>4} {m['TN']:>4} {m['FP']:>4} {m['FN']:>4} | "
                f"{m['Precision']:>6.3f} {m['Recall']:>6.3f} {m['F1']:>6.3f} {m['Accuracy']:>6.3f}"
            )
        lines += [sep, "", f"Avg F1 (algorithmic) : {avg:.3f}", ""]
        out_path = os.path.join(bdir, "batch_results_algorithmic.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"  -> {os.path.relpath(out_path, ROOT)}  (avg F1 = {avg:.3f})")

    if overall_f1:
        print(f"\nOverall avg F1 (algorithmic, {len(overall_f1)} projects) : "
              f"{sum(overall_f1)/len(overall_f1):.3f}")


# ── Subcommand: summary ────────────────────────────────────────────────────────

def _parse_eval_file(path: str) -> dict | None:
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        text = f.read()
    vals: list[float] = []
    for line in text.splitlines():
        line = line.strip()
        if "F1=" in line and "TP=" in line:
            parts = {p.split("=")[0].strip(): p.split("=")[1].strip()
                     for p in line.split() if "=" in p}
            vals.append(float(parts.get("F1", 0)))
        if "WINNER" in line:
            break
    if len(vals) < 2:
        return None
    result = {"f1": vals[0], "f2": vals[1]}
    if len(vals) >= 3:
        result["f3"] = vals[2]
    return result


def cmd_summary(args, cfg):
    all_rows = []
    batch_summaries = []

    for label, bd in BATCHES:
        if not os.path.isdir(bd):
            print(f"  Skipping {label} (not found)")
            continue
        rows = []
        for proj_dir in sorted(glob.glob(os.path.join(bd, "*"))):
            if not os.path.isdir(proj_dir):
                continue
            data = _parse_eval_file(os.path.join(proj_dir, "evaluation.txt"))
            if data:
                row = {"batch": label, "project": os.path.basename(proj_dir),
                       "f1_f1": data["f1"], "f2_f1": data["f2"]}
                if "f3" in data:
                    row["f3_f1"] = data["f3"]
                rows.append(row)
        if not rows:
            print(f"  Skipping {label} (no evaluation.txt files)")
            continue
        all_rows.extend(rows)
        avg1 = sum(r["f1_f1"] for r in rows) / len(rows)
        avg2 = sum(r["f2_f1"] for r in rows) / len(rows)
        bs   = {"batch": label, "n": len(rows), "avg_f1": avg1, "avg_f2": avg2}
        f3_rows = [r for r in rows if "f3_f1" in r]
        if f3_rows:
            bs["avg_f3"] = sum(r["f3_f1"] for r in f3_rows) / len(f3_rows)
        batch_summaries.append(bs)

    if not all_rows:
        print("No evaluation data found. Run 'batch' on each batch first.")
        return

    has_f3 = any("f3_f1" in r for r in all_rows)
    COL    = 24
    f3_col = f" {'F1 AgentBased':>10}" if has_f3 else ""
    header = (f"{'Batch':<14} {'Project':<{COL}} | "
              f"{'F1 Baseline':>10} {'F1 ContextAugmented':>10}{f3_col} | {'Winner':<22}")
    sep = "-" * len(header)
    lines = [
        "=" * len(header), "CROSS-BATCH SUMMARY", "=" * len(header),
        "", header, sep,
    ]

    prev_batch = None
    win1 = win2 = win3 = ties = 0
    for r in all_rows:
        if r["batch"] != prev_batch:
            if prev_batch is not None:
                lines.append(sep)
            prev_batch = r["batch"]
        scores = {"Baseline": r["f1_f1"], "ContextAugmented": r["f2_f1"]}
        if "f3_f1" in r:
            scores["AgentBased"] = r["f3_f1"]
        best_score = max(scores.values())
        winners    = [k for k, v in scores.items() if v == best_score]
        winner     = winners[0] if len(winners) == 1 else "Tie"
        if winner == "AgentBased": win3 += 1
        elif winner == "ContextAugmented": win2 += 1
        elif winner == "Baseline": win1 += 1
        else: ties += 1
        f3_val = f" {r['f3_f1']:>10.3f}" if has_f3 else ""
        lines.append(
            f"{r['batch']:<14} {r['project']:<{COL}} | "
            f"{r['f1_f1']:>10.3f} {r['f2_f1']:>10.3f}{f3_val} | {winner:<22}"
        )
    lines.append(sep)

    lines += ["", "PER-BATCH AVERAGES", sep]
    for bs in batch_summaries:
        delta = bs["avg_f2"] - bs["avg_f1"]
        f3_part = (f"  AgentBased={bs['avg_f3']:.3f}  "
                   f"Delta(F3-F2)={bs['avg_f3']-bs['avg_f2']:+.3f}"
                   if "avg_f3" in bs else "")
        lines.append(
            f"{bs['batch']:<14} n={bs['n']:<4} "
            f"Baseline={bs['avg_f1']:.3f}  ContextAugmented={bs['avg_f2']:.3f}  "
            f"Delta(F2-F1)={delta:+.3f}{f3_part}"
        )
    lines.append(sep)

    total = len(all_rows)
    ov1   = sum(r["f1_f1"] for r in all_rows) / total
    ov2   = sum(r["f2_f1"] for r in all_rows) / total
    f3rows = [r for r in all_rows if "f3_f1" in r]
    lines += [
        "", f"OVERALL  ({total} projects across {len(batch_summaries)} batches)", sep,
        f"  Avg F1  Baseline (diff only)   : {ov1:.3f}",
        f"  Avg F1  Context-Augmented  : {ov2:.3f}",
        f"  Delta  (ContextAugmented - Baseline)     : {ov2-ov1:+.3f}",
    ]
    if f3rows:
        ov3 = sum(r["f3_f1"] for r in f3rows) / len(f3rows)
        lines += [
            f"  Avg F1  Agent-Based       : {ov3:.3f}  (n={len(f3rows)})",
            f"  Delta  (AgentBased - ContextAugmented)     : {ov3-ov2:+.3f}",
        ]
    lines += [
        "",
        f"  ContextAugmented wins : {win2}/{total}  ({100*win2/total:.1f}%)",
        f"  Baseline wins : {win1}/{total}  ({100*win1/total:.1f}%)",
    ]
    if has_f3:
        lines.append(f"  AgentBased wins : {win3}/{total}  ({100*win3/total:.1f}%)")
    lines += [f"  Ties         : {ties}/{total}  ({100*ties/total:.1f}%)", sep, ""]

    out_path = os.path.join(ROOT, "reports", "all_batches_summary.txt")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))
    print(f"Summary saved -> {os.path.relpath(out_path)}")


# ── Subcommand: compare ────────────────────────────────────────────────────────

def cmd_compare(args, cfg):
    rows = []
    for label, bd in BATCHES:
        if not os.path.isdir(bd):
            continue
        for proj_dir in sorted(glob.glob(os.path.join(bd, "*"))):
            if not os.path.isdir(proj_dir):
                continue
            proj   = os.path.basename(proj_dir)
            gpt    = _parse_eval_file(os.path.join(proj_dir, "evaluation.txt"))
            claude = _parse_eval_file(os.path.join(proj_dir, "evaluation_claude.txt"))
            if gpt is None or claude is None:
                print(f"  [{label}/{proj}] Missing evaluation file(s) — skipping.")
                continue
            rows.append({
                "batch": label, "project": proj,
                "gpt_f1": gpt["f1"], "gpt_f2": gpt["f2"],
                "claude_f1": claude["f1"], "claude_f2": claude["f2"],
            })

    if not rows:
        print("No data. Run 'batch --model gpt' and 'batch --model claude' first.")
        return

    C1, C2, C3 = 14, 24, 10
    W = C1 + C2 + C3 * 4 + 20
    div  = "=" * W
    div2 = "-" * W
    header = (f"{'Batch':<{C1}} {'Project':<{C2}} | "
              f"{'GPT F1-1':>{C3}} {'GPT F1-2':>{C3}} | "
              f"{'CLD F1-1':>{C3}} {'CLD F1-2':>{C3}} | "
              f"{'Better (F2)':>14}")
    lines = [
        div,
        "GPT-4o  vs  Claude (claude-sonnet-4-6)  --  50 Projects / 5 Batches",
        "F1-1 = Baseline (diff only)   F1-2 = Context-Augmented",
        div, "", header, div2,
    ]

    prev_batch = None
    gpt_f1_all, gpt_f2_all, cld_f1_all, cld_f2_all = [], [], [], []
    batch_agg: dict = {}

    for r in rows:
        if r["batch"] != prev_batch:
            if prev_batch is not None:
                lines.append(div2)
            prev_batch = r["batch"]
            batch_agg.setdefault(r["batch"], {"gf1": [], "gf2": [], "cf1": [], "cf2": []})

        ba = batch_agg[r["batch"]]
        ba["gf1"].append(r["gpt_f1"]);    ba["gf2"].append(r["gpt_f2"])
        ba["cf1"].append(r["claude_f1"]); ba["cf2"].append(r["claude_f2"])
        gpt_f1_all.append(r["gpt_f1"]);   gpt_f2_all.append(r["gpt_f2"])
        cld_f1_all.append(r["claude_f1"]); cld_f2_all.append(r["claude_f2"])

        better = ("GPT" if r["gpt_f2"] > r["claude_f2"]
                  else "Claude" if r["claude_f2"] > r["gpt_f2"]
                  else "Tie")
        lines.append(
            f"{r['batch']:<{C1}} {r['project']:<{C2}} | "
            f"{r['gpt_f1']:>{C3}.3f} {r['gpt_f2']:>{C3}.3f} | "
            f"{r['claude_f1']:>{C3}.3f} {r['claude_f2']:>{C3}.3f} | "
            f"{better:>14}"
        )
    lines.append(div2)

    def avg(lst): return sum(lst) / len(lst) if lst else 0.0

    lines += ["", "PER-BATCH AVERAGES (Context-Augmented -- diff + call graph)", div2]
    for label, _ in BATCHES:
        if label not in batch_agg:
            continue
        ba = batch_agg[label]
        gf2 = avg(ba["gf2"]); cf2 = avg(ba["cf2"])
        gf1 = avg(ba["gf1"]); cf1 = avg(ba["cf1"])
        winner = "GPT" if gf2 > cf2 else "Claude" if cf2 > gf2 else "Tie"
        lines.append(
            f"{label:<14} n={len(ba['gf2'])}  "
            f"GPT  F1(diff-only)={gf1:.3f}  F1(+graph)={gf2:.3f}   "
            f"Claude F1(diff-only)={cf1:.3f}  F1(+graph)={cf2:.3f}   "
            f"Better(F2): {winner}"
        )
    lines.append(div2)

    n = len(rows)
    og_f1 = avg(gpt_f1_all); og_f2 = avg(gpt_f2_all)
    oc_f1 = avg(cld_f1_all); oc_f2 = avg(cld_f2_all)
    gpt_wins  = sum(1 for r in rows if r["gpt_f2"] > r["claude_f2"])
    cld_wins  = sum(1 for r in rows if r["claude_f2"] > r["gpt_f2"])
    ties_f2   = sum(1 for r in rows if r["gpt_f2"] == r["claude_f2"])
    gpt_delta = og_f2 - og_f1
    cld_delta = oc_f2 - oc_f1

    lines += [
        "", f"OVERALL  ({n} projects across 5 batches)", div, "",
        f"  {'Metric':<42} {'GPT-4o':>10} {'Claude':>10}",
        f"  {'-'*62}",
        f"  {'Avg F1 -- Baseline  (diff only)':<42} {og_f1:>10.3f} {oc_f1:>10.3f}",
        f"  {'Avg F1 -- Context-Augmented  (diff + call graph)':<42} {og_f2:>10.3f} {oc_f2:>10.3f}",
        f"  {'Graph context improvement (F2-F1)':<42} {gpt_delta:>+10.3f} {cld_delta:>+10.3f}",
        "",
        f"  Context-Augmented head-to-head (which model scored higher per project):",
        f"    GPT-4o wins  : {gpt_wins}/{n}  ({100*gpt_wins/n:.1f}%)",
        f"    Claude wins  : {cld_wins}/{n}  ({100*cld_wins/n:.1f}%)",
        f"    Ties         : {ties_f2}/{n}  ({100*ties_f2/n:.1f}%)",
        "",
        f"  Overall winner (Context-Augmented Avg F1): "
        f"{'GPT-4o' if og_f2 > oc_f2 else 'Claude' if oc_f2 > og_f2 else 'Tie'}"
        f"  (GPT={og_f2:.3f}  Claude={oc_f2:.3f}  delta={oc_f2-og_f2:+.3f})",
        "", div, "",
    ]

    out_path = os.path.join(ROOT, "reports", "gpt_vs_claude.txt")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))
    print(f"Comparison saved -> {os.path.relpath(out_path)}")


# ── Subcommand: config ─────────────────────────────────────────────────────────

def cmd_config(args, cfg):
    if args.gpt_key:
        cfg["openai_key"] = args.gpt_key
    if args.claude_key:
        cfg["anthropic_key"] = args.claude_key
    if args.gpt_key or args.claude_key:
        save_config(cfg)
    else:
        print("Current config:")
        gpt = cfg.get("openai_key", "(not set)")
        ant = cfg.get("anthropic_key", "(not set)")
        if gpt != "(not set)":
            gpt = gpt[:12] + "..." + gpt[-4:]
        if ant != "(not set)":
            ant = ant[:16] + "..." + ant[-4:]
        print(f"  OpenAI key   : {gpt}")
        print(f"  Anthropic key: {ant}")
        print(f"\nConfig file: {os.path.relpath(CONFIG_FILE)}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="graphguard",
        description="GraphGuard -- AI-powered C code impact analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
commands:
  analyze   Detect git changes and analyze impact (run from your C project)
  batch     Run evaluation on a thesis batch directory (with ground truth)
  summary   Regenerate cross-batch GPT summary -> reports/all_batches_summary.txt
  compare   Regenerate GPT vs Claude comparison -> reports/gpt_vs_claude.txt
  config    View or set API keys

model aliases (--model):
  gpt / gpt-4o / gpt-4o-mini
  claude / claude-sonnet / claude-sonnet-4-6
  claude-opus / claude-opus-4-7
  claude-haiku / claude-haiku-4-5

analyze examples:
  python graphguard.py analyze                     # auto-detect all uncommitted changes
  python graphguard.py analyze --staged            # only staged changes
  python graphguard.py analyze --unpushed          # committed but not yet pushed
  python graphguard.py analyze --model claude      # use Claude instead of GPT
  python graphguard.py analyze --save              # also save result to graphguard_analysis.txt

batch examples:
  python graphguard.py batch ./batches/batch_01 --model gpt
  python graphguard.py batch ./batches/batch_02 --model claude
""")

    sub = parser.add_subparsers(dest="command")

    # analyze
    p_analyze = sub.add_parser("analyze", help="Analyze git changes in current directory")
    p_analyze.add_argument("--staged", action="store_true",
                           help="Only analyze staged changes")
    p_analyze.add_argument("--unpushed", action="store_true",
                           help="Analyze committed but not yet pushed changes")
    p_analyze.add_argument("--save", action="store_true",
                           help="Save analysis to graphguard_analysis.txt")
    p_analyze.add_argument("--api-key", help="Override API key for this run")
    p_analyze.add_argument("--diff", dest="diff_file",
                           help="Use a specific diff file instead of git diff")
    p_analyze.add_argument("--model", "-m", default=None,
                           help="Skip model menu (gpt, claude, claude-opus, claude-haiku)")
    p_analyze.add_argument("--approach",
                           choices=["diff", "graph", "agent", "algorithmic"],
                           default=None,
                           help="Skip approach menu (diff, graph, agent, algorithmic)")

    # batch
    p_batch = sub.add_parser("batch", help="Evaluate a batch directory (thesis mode)")
    p_batch.add_argument("batch_dir", help="Path to batch directory")
    p_batch.add_argument("--model", "-m", default="gpt", help="Model (default: gpt)")
    p_batch.add_argument("--api-key", help="Override API key for this run")
    p_batch.add_argument("--agent", action="store_true",
                         help="Also run Agent-Based evaluation — Anthropic models only")

    # algorithmic
    p_alg = sub.add_parser(
        "algorithmic",
        help="Run Algorithmic (pure graph traversal, no LLM) across batches"
    )
    p_alg.add_argument("batch_dir", nargs="?", default=None,
                       help="Single batch dir, or omit to run all batches/batch_*")

    # summary
    sub.add_parser("summary", help="Regenerate cross-batch GPT summary")

    # compare
    sub.add_parser("compare", help="Regenerate GPT vs Claude comparison")

    # config
    p_config = sub.add_parser("config", help="View or set API keys")
    p_config.add_argument("--gpt-key", help="Set OpenAI API key")
    p_config.add_argument("--claude-key", help="Set Anthropic API key")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    cfg = load_config()
    dispatch = {
        "analyze":     cmd_analyze,
        "batch":       cmd_batch,
        "algorithmic": cmd_algorithmic,
        "summary":     cmd_summary,
        "compare":     cmd_compare,
        "config":      cmd_config,
    }
    dispatch[args.command](args, cfg)


if __name__ == "__main__":
    main()
