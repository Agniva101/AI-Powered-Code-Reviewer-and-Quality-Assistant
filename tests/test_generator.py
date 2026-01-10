"""Tests for docstring generator module."""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from core.docstring_engine.generator import (
    _humanize_name,
    _build_google_body,
    _build_numpy_body,
    _build_rest_body,
    _fix_imperative_mood,
    _fix_pep257_first_line,
)


def test_humanize_name_simple():
    """Test humanizing a simple function name."""
    result = _humanize_name("get_user_data")
    assert "user" in result.lower()
    assert "data" in result.lower()


def test_humanize_name_with_underscores():
    """Test humanizing names with multiple underscores."""
    result = _humanize_name("parse_json_file")
    assert isinstance(result, str)
    assert len(result) > 0


def test_build_google_body_basic():
    """Test Google-style docstring body contains Args section."""
    func_meta = {
        "name": "example_func",
        "args_meta": [{"name": "x", "annotation": "int"}],
        "returns": "str",
        "raises": [],
    }
    body = _build_google_body(func_meta)
    assert isinstance(body, str)
    assert len(body) > 0
    # Google style should have Args section
    assert "Args:" in body


def test_build_numpy_body_basic():
    """Test NumPy-style docstring body contains Parameters section."""
    func_meta = {
        "name": "example_func",
        "args_meta": [{"name": "x", "annotation": "int"}],
        "returns": "str",
        "raises": [],
    }
    body = _build_numpy_body(func_meta)
    assert isinstance(body, str)
    assert len(body) > 0
    # NumPy style should have Parameters section
    assert "Parameters" in body


def test_build_rest_body_basic():
    """Test reST-style docstring body contains :param directives."""
    func_meta = {
        "name": "example_func",
        "args_meta": [{"name": "x", "annotation": "int"}, {"name": "y", "annotation": "str"}],
        "returns": "bool",
        "raises": ["ValueError"],
    }
    body = _build_rest_body(func_meta)
    assert isinstance(body, str)
    assert len(body) > 0
    # reST style should have :param directives
    assert ":param" in body


# ============================================================================
# Tests for PEP 257 fix functions
# ============================================================================

def test_fix_imperative_mood_calculates():
    """Test D401 fix: 'Calculates' should become 'Calculate'."""
    result = _fix_imperative_mood("Calculates the average of numbers.")
    assert result.startswith("Calculate ")


def test_fix_imperative_mood_returns():
    """Test D401 fix: 'Returns' should become 'Return'."""
    result = _fix_imperative_mood("Returns the user data.")
    assert result.startswith("Return ")


def test_fix_imperative_mood_raises():
    """Test D401 fix: 'Raises' should become 'Raise'."""
    result = _fix_imperative_mood("Raises an exception when input is invalid.")
    assert result.startswith("Raise ")


def test_fix_imperative_mood_already_imperative():
    """Test D401 fix: already imperative mood should not change."""
    result = _fix_imperative_mood("Calculate the average of numbers.")
    assert result == "Calculate the average of numbers."


def test_fix_imperative_mood_empty():
    """Test D401 fix: empty string should return empty."""
    result = _fix_imperative_mood("")
    assert result == ""


def test_fix_pep257_first_line_add_period():
    """Test D400 fix: adds period if missing."""
    result = _fix_pep257_first_line("Calculate the average")
    assert result.endswith(".")


def test_fix_pep257_first_line_capitalize():
    """Test D403 fix: capitalizes first word."""
    result = _fix_pep257_first_line("calculate the average.")
    assert result[0].isupper()


def test_fix_pep257_first_line_remove_this():
    """Test D404 fix: removes 'This' from start."""
    result = _fix_pep257_first_line("This function calculates the average.")
    assert not result.lower().startswith("this ")


def test_fix_pep257_first_line_combined():
    """Test multiple D4xx fixes combined."""
    result = _fix_pep257_first_line("this module provides utilities")
    assert result[0].isupper()  # D403
    assert result.endswith(".")  # D400
    assert not result.lower().startswith("this ")  # D404


def test_fix_pep257_first_line_preserves_punctuation():
    """Test D400 fix: doesn't add period if other punctuation exists."""
    result = _fix_pep257_first_line("Is this valid?")
    assert result.endswith("?")
    assert not result.endswith("?.")


def test_post_process_removes_attributes_section():
    """Test D414 fix: Attributes section should be removed from function docstrings."""
    from core.docstring_engine.generator import _post_process_docstring
    
    docstring_with_attributes = """
    Calculate value.
    
    Args:
        x (int): Value.
        
    Attributes:
        some_attr (int): An attribute.
        
    Returns:
        int: Result.
    """
    
    func_meta = {
        "name": "calc",
        "raises": [],
        "has_return": True,
        "has_yields": False
    }
    
    result = _post_process_docstring(docstring_with_attributes, func_meta, style="google")
    assert "Attributes:" not in result
    assert "Args:" in result
    assert "Returns:" in result

