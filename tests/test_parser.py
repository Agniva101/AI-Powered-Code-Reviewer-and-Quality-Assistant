"""Tests for Python parser module."""

import os
import sys
import tempfile

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from core.parser.python_parser import (
    parse_path,
    parse_file,
    parse_functions,
    parse_imports,
    parse_classes,
)
import ast


def test_parse_examples():
    """Test parsing the examples folder."""
    base = os.path.join(PROJECT_ROOT, "examples")
    assert os.path.exists(base), f"examples folder not found at {base}"
    results = parse_path(base)
    assert isinstance(results, list)
    assert len(results) >= 1
    for r in results:
        assert "path" in r
        assert "functions" in r
        assert "parsing_errors" in r


def test_parse_file_returns_dict():
    """Test that parse_file returns a dictionary with expected keys."""
    code = '''def hello():
    """A greeting function."""
    return "Hello"
'''
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        temp_path = f.name
    
    try:
        result = parse_file(temp_path)
        assert isinstance(result, dict)
        assert "path" in result
        assert "functions" in result
        assert "imports" in result
    finally:
        os.remove(temp_path)


def test_parse_functions_extracts_metadata():
    """Test that parse_functions extracts function metadata correctly."""
    code = '''def greet(name: str) -> str:
    """Greet someone."""
    return f"Hello, {name}"
'''
    tree = ast.parse(code)
    functions = parse_functions(tree, code)
    
    assert len(functions) == 1
    func = functions[0]
    assert func["name"] == "greet"
    assert func["has_docstring"] is True


def test_parse_imports_extracts_imports():
    """Test that parse_imports extracts import statements."""
    code = '''import os
from sys import path
import json as j
'''
    tree = ast.parse(code)
    imports = parse_imports(tree)
    
    assert isinstance(imports, list)
    assert len(imports) >= 1


def test_parse_path_recursive():
    """Test recursive parsing of directories."""
    base = os.path.join(PROJECT_ROOT, "examples")
    if os.path.exists(base):
        results = parse_path(base, recursive=True)
        assert isinstance(results, list)
        # Should find at least one Python file
        assert len(results) >= 1
