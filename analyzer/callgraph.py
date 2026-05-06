import clang.cindex
from clang.cindex import Index, CursorKind
import os
import json

clang.cindex.Config.set_library_file(
    r"C:\Program Files\LLVM\bin\libclang.dll"
)


class CallGraph:
    def __init__(self):
        self.graph = {}          # caller -> set(callees)
        self.reverse_graph = {}  # callee -> set(callers)
        self.defined_functions = set()
        self._fn_extents = []    # (norm_path, start_line, end_line, fn_name)

    def get_callers(self, fn):
        return self.reverse_graph.get(fn, set())

    def get_callees(self, fn):
        return self.graph.get(fn, set())

    def function_at_line(self, filepath, line):
        """Return the name of the user-defined function containing the given line."""
        norm = os.path.normcase(os.path.abspath(filepath))
        for (path, start, end, fn) in self._fn_extents:
            if path == norm and start <= line <= end:
                return fn
        return None

    def save(self, cache_path: str):
        """Serialize the call graph to JSON, recording file mtimes for cache validation."""
        files = {}
        for (path, _, _, _) in self._fn_extents:
            try:
                files[path] = os.path.getmtime(path)
            except OSError:
                pass
        data = {
            "version": 1,
            "files": files,
            "graph": {k: sorted(v) for k, v in self.graph.items()},
            "reverse_graph": {k: sorted(v) for k, v in self.reverse_graph.items()},
            "defined_functions": sorted(self.defined_functions),
            "fn_extents": [[p, s, e, fn] for (p, s, e, fn) in self._fn_extents],
        }
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, cache_path: str, file_paths: list) -> "CallGraph | None":
        """
        Load from cache if it exists and all source files are unchanged.
        Returns None if cache is missing, stale, or corrupt.
        """
        if not os.path.isfile(cache_path):
            return None
        try:
            with open(cache_path, encoding="utf-8") as f:
                data = json.load(f)
            if data.get("version") != 1:
                return None

            norm_input = {os.path.normcase(os.path.abspath(p)) for p in file_paths}
            cached_files = {os.path.normcase(k): v for k, v in data["files"].items()}

            if set(cached_files.keys()) != norm_input:
                return None

            for path, mtime in cached_files.items():
                if abs(os.path.getmtime(path) - mtime) > 0.001:
                    return None

            cg = cls()
            cg.graph            = {k: set(v) for k, v in data["graph"].items()}
            cg.reverse_graph    = {k: set(v) for k, v in data["reverse_graph"].items()}
            cg.defined_functions = set(data["defined_functions"])
            cg._fn_extents      = [(p, s, e, fn) for [p, s, e, fn] in data["fn_extents"]]
            return cg
        except (json.JSONDecodeError, KeyError, OSError, ValueError):
            return None

    def add_call(self, caller, callee):
        if caller and callee and callee in self.defined_functions:
            self.graph.setdefault(caller, set()).add(callee)
            self.reverse_graph.setdefault(callee, set()).add(caller)

    def build(self, file_paths):
        """Accept a single file path or a list of file paths."""
        if isinstance(file_paths, str):
            file_paths = [file_paths]

        index = Index.create()
        abs_paths = [os.path.abspath(p) for p in file_paths]
        include_dirs = {os.path.dirname(p) for p in abs_paths}
        args = ["-x", "c", "-std=c11"] + [f"-I{d}" for d in include_dirs]

        translation_units = []
        for path in abs_paths:
            tu = index.parse(
                path,
                args=args,
                options=clang.cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD,
            )
            if not tu:
                raise Exception(f"Failed to parse {path}")
            translation_units.append((path, tu))

        norm_user_files = {os.path.normcase(p) for p in abs_paths}

        # Pass 1: collect all user-defined functions and their line extents
        for _, tu in translation_units:
            self._collect_functions(tu.cursor, norm_user_files)

        # Pass 2: build call edges
        for _, tu in translation_units:
            self._visit(tu.cursor, None, norm_user_files)

        # Ensure every function node exists in both graphs
        for fn in self.defined_functions:
            self.graph.setdefault(fn, set())
            self.reverse_graph.setdefault(fn, set())

        return self

    def _collect_functions(self, node, norm_user_files):
        if (
            node.kind == CursorKind.FUNCTION_DECL
            and node.is_definition()
            and node.location.file
            and os.path.normcase(node.location.file.name) in norm_user_files
        ):
            self.defined_functions.add(node.spelling)
            self._fn_extents.append((
                os.path.normcase(node.location.file.name),
                node.extent.start.line,
                node.extent.end.line,
                node.spelling,
            ))

        for child in node.get_children():
            self._collect_functions(child, norm_user_files)

    def _visit(self, node, current_function, norm_user_files):
        if (
            node.kind == CursorKind.FUNCTION_DECL
            and node.is_definition()
            and node.location.file
            and os.path.normcase(node.location.file.name) in norm_user_files
        ):
            current_function = node.spelling

        if node.kind == CursorKind.CALL_EXPR:
            callee = node.spelling or node.displayname
            self.add_call(current_function, callee)

        for child in node.get_children():
            self._visit(child, current_function, norm_user_files)
