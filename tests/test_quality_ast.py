"""AST-based quality checks for type hints, docstrings, line length, and variable naming."""
from __future__ import annotations

import ast
from pathlib import Path
import unittest


class QualityASTTests(unittest.TestCase):
    """Enforce repository-wide source-quality conventions."""

    def test_functions_have_annotations_and_docstrings(self) -> None:
        """Every function must have argument/return annotations and a docstring."""
        failures: list[str] = []
        for path in Path("visualcpsa").rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if ast.get_docstring(node) is None or node.returns is None:
                        failures.append(f"{path}:{node.lineno}:{node.name}")
                    arguments = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
                    for argument in arguments:
                        if argument.arg not in {"self", "cls"} and argument.annotation is None:
                            failures.append(f"{path}:{node.lineno}:{node.name}:{argument.arg}")
        self.assertEqual(failures, [])

    def test_source_lines_do_not_exceed_135_characters(self) -> None:
        """Python source lines should fit the requested 135-character editor width."""
        failures = []
        for path in Path("visualcpsa").rglob("*.py"):
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if len(line) > 135:
                    failures.append(f"{path}:{line_number}:{len(line)}")
        self.assertEqual(failures, [])

    def test_no_single_character_assignments_outside_loops(self) -> None:
        """Single-character assignment names are prohibited outside loop targets."""
        failures: list[str] = []
        for path in Path("visualcpsa").rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            loop_names = set()
            for loop_node in ast.walk(tree):
                if isinstance(loop_node, (ast.For, ast.comprehension)):
                    loop_names.update(name.id for name in ast.walk(loop_node.target) if isinstance(name, ast.Name))
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store) and len(node.id) == 1 and node.id not in loop_names:
                    failures.append(f"{path}:{node.lineno}:{node.id}")
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
