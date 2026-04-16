import clang.cindex
from clang.cindex import Index, CursorKind
import os

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
