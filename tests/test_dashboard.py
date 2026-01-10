"""Tests for dashboard UI utilities."""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from core.dashboard.dashboard import load_pytest_results, filter_functions


def test_dashboard_loads_pytest_results():
    """
    Test loading of pytest results.
    
    Args:
        None: This function does not take any parameters.
    """
    data = load_pytest_results()
    assert data is None or isinstance(data, dict)


def test_filter_functions_search():
    """
    Filter functions based on search term and status.
    
    Args:
        functions (list): A list of dictionaries containing function metadata.
        search (str): The search term to filter by.
        status (any): The status to filter by (optional).
    """
    functions = [
        {"name": "test_function", "has_docstring": True, "file_path": "test.py"},
        {"name": "other_function", "has_docstring": False, "file_path": "test.py"}
    ]

    filtered = filter_functions(functions, search="test", status=None)
    assert len(filtered) == 1
    assert filtered[0]["name"] == "test_function"


def test_filter_functions_status():
    """
    Filter functions by status.
    
    Args:
        functions (list[dict]): A list of dictionaries containing function metadata.
        search (any, optional): Not used in this function. Defaults to None.
        status (str, optional): The status to filter by. Defaults to None.
    """
    functions = [
        {"name": "documented_fn", "is_valid": True, "file_path": "test.py"},
        {"name": "missing_fn", "is_valid": False, "file_path": "test.py"}
    ]

    # Filter for valid (OK) functions
    filtered = filter_functions(functions, search=None, status="OK")
    assert len(filtered) == 1
    assert filtered[0]["name"] == "documented_fn"


def test_filter_functions_combined():
    """
    Filter functions based on search and status criteria.
    
    Args:
        functions (list[dict]): A list of dictionaries containing function metadata.
        search (str): The search term to filter functions by name.
        status (str): The status to filter functions by.
    """
    functions = [
        {"name": "test_valid", "is_valid": True, "file_path": "a.py"},
        {"name": "test_invalid", "is_valid": False, "file_path": "b.py"},
        {"name": "other_valid", "is_valid": True, "file_path": "c.py"}
    ]

    filtered = filter_functions(functions, search="test", status="OK")
    assert len(filtered) == 1
    assert filtered[0]["name"] == "test_valid"
