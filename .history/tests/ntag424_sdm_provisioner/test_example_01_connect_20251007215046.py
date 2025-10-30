import ast
from pathlib import Path


def test_examples_01_defines_list_readers_with_docstring():
    """Statically verify that examples/01_connect.py defines a
    `list_readers` function and that it has a docstring.

    This test performs static analysis (AST) only — it does not import
    or execute the module and therefore requires no hardware or mocks.
    """
    p = Path("examples/01_connect.py")
    src = p.read_text(encoding="utf8")
    tree = ast.parse(src)

    # Find a function definition named `list_readers`
    func_nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "list_readers"]
    assert func_nodes, "examples/01_connect.py must define a function named 'list_readers'"

    doc = ast.get_docstring(func_nodes[0])
    assert doc is not None and doc.strip() != "", "'list_readers' must have a non-empty docstring"
