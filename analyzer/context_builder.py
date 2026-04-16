"""
Build the two prompts used in the thesis experiment:
  A) diff only
  B) diff + call graph impact context
"""

QUESTIONS = """\
Answer the following:
1. What do these changes actually do?
2. Which functions or components might be affected by this change?
3. What could break or behave differently as a result?
4. What should be tested to verify correctness after this change?"""


def build_diff_only(diff_text):
    return f"""\
You are a senior software engineer reviewing a code change.
{QUESTIONS}

=== DIFF ===
{diff_text}
"""


def build_diff_with_graph(diff_text, call_graph, changed_fns):
    """
    call_graph  : CallGraph object (has .graph and .defined_functions)
    changed_fns : set of function names touched by the diff
    """
    lines = []
    lines.append("=== DIFF ===")
    lines.append(diff_text)
    lines.append("=== CALL GRAPH ===")
    lines.append("(format: function -> [functions it calls])")
    lines.append(f"(functions marked with * were modified in this diff)\n")

    for fn in sorted(call_graph.defined_functions):
        callees = sorted(call_graph.get_callees(fn))
        marker = " *" if fn in changed_fns else ""
        callees_str = ", ".join(callees) if callees else "-"
        lines.append(f"  {fn}{marker} -> [{callees_str}]")

    return "\n".join(lines)
