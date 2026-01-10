"""Tests for validator module."""

import os
import sys
import tempfile

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from core.validator.validator import (
    _parse_pydocstyle_output,
    run_pydocstyle,
    run_radon_cc,
    run_validators,
    summarize_pydocstyle_on_files,
)


def test_parse_pydocstyle_output_empty():
    """Test parsing empty pydocstyle output."""
    result = _parse_pydocstyle_output("")
    assert result == {}


def test_parse_pydocstyle_output_with_errors():
    """Test parsing pydocstyle output with function errors."""
    output = '''test.py:10 in public function "foo":
        D103: Missing docstring in public function'''
    result = _parse_pydocstyle_output(output)
    assert "foo" in result


def test_run_pydocstyle_on_file():
    """Test running pydocstyle on a temporary file."""
    code = '''def undocumented():
    pass
'''
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        temp_path = f.name
    
    try:
        mapping, available = run_pydocstyle(temp_path)
        # pydocstyle may or may not be installed
        assert isinstance(mapping, dict)
        assert isinstance(available, bool)
    finally:
        os.remove(temp_path)


def test_run_radon_cc_on_file():
    """Test running radon complexity on a temporary file."""
    code = '''def simple():
    return 1

def complex_func(x):
    if x > 0:
        if x > 10:
            return "big"
        return "small"
    return "negative"
'''
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        temp_path = f.name
    
    try:
        entries, available = run_radon_cc(temp_path)
        assert isinstance(entries, list)
        assert isinstance(available, bool)
    finally:
        os.remove(temp_path)


def test_run_validators_returns_dict():
    """Test that run_validators returns proper structure."""
    code = '''def test():
    """A docstring."""
    pass
'''
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        temp_path = f.name
    
    try:
        result = run_validators(temp_path)
        assert "pydocstyle" in result
        assert "radon" in result
    finally:
        os.remove(temp_path)


def test_summarize_pydocstyle_empty():
    """Test summarizing with empty file list."""
    result = summarize_pydocstyle_on_files([])
    assert result["total_functions"] == 0
    assert result["compliant"] == 0


def test_summarize_pydocstyle_structure():
    """Test that summary has expected structure."""
    result = summarize_pydocstyle_on_files([])
    assert "available" in result
    assert "total_functions" in result
    assert "compliant" in result
    assert "violations" in result
    assert "violations_list" in result
