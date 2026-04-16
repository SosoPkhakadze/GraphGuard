"""
Impact analysis: given a parsed diff and a CallGraph, find which functions
changed and what the blast radius looks like.
"""

from dataclasses import dataclass, field


@dataclass
class ImpactReport:
    # Functions whose source lines were touched by the diff
    changed_functions: set

    # For each changed function: functions one hop up (direct callers)
    direct_callers: dict        # fn -> set[str]

    # For each changed function: functions one hop down (direct callees)
    direct_callees: dict        # fn -> set[str]

    # For each changed function: ALL upstream callers (full blast radius)
    transitive_callers: dict    # fn -> set[str]


class ImpactAnalyzer:
    def __init__(self, call_graph):
        self.cg = call_graph

    def find_changed_functions(self, file_to_lines):
        """
        file_to_lines: {norm_abs_path: set_of_line_numbers}  (output of diff_parser.parse)
        Returns: set of function names that were touched.
        """
        changed = set()
        for filepath, lines in file_to_lines.items():
            for line in lines:
                fn = self.cg.function_at_line(filepath, line)
                if fn:
                    changed.add(fn)
        return changed

    def analyze(self, changed_functions):
        """
        Build a full ImpactReport for the given set of changed function names.
        """
        direct_callers = {}
        direct_callees = {}
        transitive_callers = {}

        for fn in changed_functions:
            direct_callers[fn] = self.cg.get_callers(fn)
            direct_callees[fn] = self.cg.get_callees(fn)
            transitive_callers[fn] = self._all_callers(fn)

        return ImpactReport(
            changed_functions=changed_functions,
            direct_callers=direct_callers,
            direct_callees=direct_callees,
            transitive_callers=transitive_callers,
        )

    def _all_callers(self, fn, visited=None):
        """Recursively collect all upstream callers of fn."""
        if visited is None:
            visited = set()
        if fn in visited:
            return set()
        visited.add(fn)
        result = set()
        for caller in self.cg.get_callers(fn):
            result.add(caller)
            result |= self._all_callers(caller, visited)
        return result
