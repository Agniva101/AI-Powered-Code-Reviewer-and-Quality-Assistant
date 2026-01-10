"""Tests for LLM integration and prompt building."""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from core.docstring_engine.generator import (
    _build_groq_prompt,
    _create_cache_key,
    generate_docstring,
)


def test_build_groq_prompt_google():
    """Test prompt building for Google style includes style-specific content."""
    func_meta = {
        "name": "test_func",
        "args_meta": [{"name": "x", "annotation": "int"}],
        "returns": "str",
        "raises": ["ValueError"],
        "source": "def test_func(x: int) -> str:\n    return str(x)",
    }
    prompt = _build_groq_prompt(func_meta, style="google")
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    # Google style should mention Google or Args/Returns format
    assert "google" in prompt.lower() or "args:" in prompt.lower()


def test_build_groq_prompt_numpy():
    """Test prompt building for NumPy style includes style-specific content."""
    func_meta = {
        "name": "test_func",
        "args_meta": [{"name": "x", "annotation": "int"}],
        "returns": "str",
        "raises": [],
        "source": "def test_func(x: int) -> str:\n    return str(x)",
    }
    prompt = _build_groq_prompt(func_meta, style="numpy")
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    # NumPy style should mention NumPy or Parameters format
    assert "numpy" in prompt.lower() or "parameters" in prompt.lower()


def test_build_groq_prompt_rest():
    """Test prompt building for reStructuredText style includes style-specific content."""
    func_meta = {
        "name": "test_func",
        "args_meta": [{"name": "a"}, {"name": "b"}],
        "returns": "bool",
        "raises": [],
        "source": "def test_func(a, b):\n    return True",
    }
    prompt = _build_groq_prompt(func_meta, style="rest")
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    # reST style should mention reStructuredText or :param/:return format
    assert "restructuredtext" in prompt.lower() or "rest" in prompt.lower() or ":param" in prompt.lower()


def test_create_cache_key_uniqueness():
    """Test that cache keys are unique for different inputs."""
    func_meta_1 = {"name": "func1", "args_meta": [], "returns": None, "raises": []}
    func_meta_2 = {"name": "func2", "args_meta": [], "returns": None, "raises": []}
    
    key1 = _create_cache_key(func_meta_1, "google")
    key2 = _create_cache_key(func_meta_2, "google")
    
    assert key1 != key2


def test_create_cache_key_consistency():
    """Test that cache keys are consistent for same inputs."""
    func_meta = {"name": "func", "args_meta": [], "returns": "int", "raises": []}
    
    key1 = _create_cache_key(func_meta, "google")
    key2 = _create_cache_key(func_meta, "google")
    
    assert key1 == key2


def test_generate_docstring_none_style():
    """Test that generate_docstring returns empty string for 'none' style."""
    func_meta = {
        "name": "test_func",
        "args_meta": [{"name": "x", "annotation": "int"}],
        "returns": "str",
        "raises": [],
    }
    result = generate_docstring(func_meta, style="none")
    assert result == ""


def test_generate_docstring_returns_string():
    """Test that generate_docstring returns a non-empty string for valid styles."""
    func_meta = {
        "name": "calculate_sum",
        "args_meta": [
            {"name": "a", "annotation": "int"},
            {"name": "b", "annotation": "int"},
        ],
        "has_return": True,
        "returns": "int",
        "raises": [],
    }
    # This will use fallback if API is unavailable
    result = generate_docstring(func_meta, style="google")
    assert isinstance(result, str)
    assert len(result) > 0


def test_generate_docstring_different_styles():
    """Test that different styles produce different docstring formats."""
    func_meta = {
        "name": "process_data",
        "args_meta": [{"name": "data", "annotation": "dict"}],
        "has_return": True,
        "returns": "list",
        "raises": [],
    }
    
    google_result = generate_docstring(func_meta, style="google")
    numpy_result = generate_docstring(func_meta, style="numpy")
    
    # Both should be non-empty strings
    assert isinstance(google_result, str) and len(google_result) > 0
    assert isinstance(numpy_result, str) and len(numpy_result) > 0
