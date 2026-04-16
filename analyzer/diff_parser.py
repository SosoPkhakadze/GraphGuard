"""
Parse a unified diff and return which line numbers changed per file.

Returns: {normalized_abs_path: set_of_changed_line_numbers_in_new_file}

For added lines   (+): exact new-file line number.
For deleted lines (-): the surrounding new-file position is marked so the
                       enclosing function is still flagged as changed.
"""

import re
import os

_NEW_FILE_RE = re.compile(r'^\+\+\+ (.+)$')
_OLD_FILE_RE = re.compile(r'^--- (.+)$')   # "--- a/path" separates file sections
_HUNK_RE = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@')


def parse(diff_text, repo_root=None):
    """
    diff_text : str  — contents of a unified diff file
    repo_root : str  — project root used to resolve relative paths from the diff.
                       If None, paths are resolved from cwd.

    Returns dict mapping normalized absolute path -> set of ints (line numbers).
    """
    result = {}
    current_file = None
    new_line = 0
    in_hunk = False

    for raw in diff_text.splitlines():
        m = _NEW_FILE_RE.match(raw)
        if m:
            # Strip trailing timestamp that `diff -u` appends after a tab
            # e.g. "test/foo.c\t2026-04-15 19:31:52" -> "test/foo.c"
            path = m.group(1).split('\t')[0].strip()
            # Git prefixes new-file paths with "b/"
            if path.startswith('b/'):
                path = path[2:]
            if repo_root:
                path = os.path.join(repo_root, path)
            current_file = os.path.normcase(os.path.abspath(path))
            result.setdefault(current_file, set())
            in_hunk = False
            continue

        # "--- a/path" marks the start of a new file section — reset hunk state
        # so the line is never misread as a deletion in the previous file.
        if _OLD_FILE_RE.match(raw):
            in_hunk = False
            continue

        m = _HUNK_RE.match(raw)
        if m:
            new_line = int(m.group(1))
            in_hunk = True
            continue

        if not in_hunk or current_file is None:
            continue

        if raw.startswith('+'):
            result[current_file].add(new_line)
            new_line += 1
        elif raw.startswith('-'):
            # Deletion: mark this position in the new file so the surrounding
            # function is captured; do NOT advance new_line.
            result[current_file].add(new_line)
        elif raw.startswith(' '):
            new_line += 1
        # Lines starting with '\' (no newline at EOF) are ignored

    return result
