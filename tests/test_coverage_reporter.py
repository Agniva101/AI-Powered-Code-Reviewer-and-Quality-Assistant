"""Tests for coverage reporter module."""

import os
import sys
import json
import tempfile

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from core.reporter.coverage_reporter import compute_coverage, write_report


def test_compute_coverage_empty():
    """Test compute_coverage with empty input."""
    result = compute_coverage([])
    assert "files" in result
    assert "aggregate" in result
    assert result["aggregate"]["total_functions"] == 0


def test_compute_coverage_single_file():
    """Test compute_coverage with a single file result."""
    per_file = [
        {
            "path": "test.py",
            "functions": [
                {"name": "foo", "has_docstring": True},
                {"name": "bar", "has_docstring": False},
            ],
            "parsing_errors": [],
        }
    ]
    result = compute_coverage(per_file, generate_baseline=False)
    
    assert result["aggregate"]["total_functions"] == 2
    assert result["aggregate"]["already_documented"] == 1
    assert len(result["files"]) == 1


def test_write_report_creates_file():
    """
    Test that a report is written to a valid JSON file.
    
    Args:
        report (dict): The report data to be written.
        path (str): The path to the file where the report will be written.
    """
    report = {"files": [], "aggregate": {"total_functions": 0}}
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_path = f.name
    
    try:
        write_report(report, temp_path)
        assert os.path.exists(temp_path)
        
        with open(temp_path, "r", encoding="utf-8") as fh:
            loaded = json.load(fh)
        
        assert loaded == report
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
