import re
import subprocess
from typing import Any, Dict, List, Tuple


def _parse_pydocstyle_output(output: str) -> Dict[str, List[str]]:
    """
    Parse pydocstyle CLI output into a mapping.

    Args:
        output: Raw pydocstyle command output

    Returns:
        Dictionary mapping entity names to their error messages.
        Entity names can be function names, '<class>', or '<module>'.
    """
    errors: Dict[str, List[str]] = {}
    current_fn: str = ""

    for raw in output.splitlines():
        line = raw.strip()
        if not line:
            continue

        # Context line: "file.py:N at module level:" - sets context but doesn't add as error
        m_ctx = re.search(r"\.py:\d+.*at module level", line)
        if m_ctx:
            current_fn = ""  # Reset to module level context
            continue

        # Context: function
        m = re.search(
            r"in (?:public|private|nested) function [\"'`]?(?P<name>[^\"'`]+)[\"'`]?",
            line,
        )
        if m:
            current_fn = m.group("name")
            continue

        # Generic D-code line - use current_fn context if available
        m3 = re.search(r"(D\d{3})\b[:]?\s*(.*)", line)
        if m3:
            code = m3.group(1)
            desc = (m3.group(2) or "").lower()

            # Explicitly ignore D101 (missing class docstring)
            if code == "D101" and "class" in desc:
                continue

            if "class" in desc:
                errors.setdefault("<class>", []).append(line)
                continue

            if "module" in desc and not current_fn:
                errors.setdefault("<module>", []).append(line)
                continue

            if current_fn:
                errors.setdefault(current_fn, []).append(line)
            else:
                errors.setdefault("<module>", []).append(line)
            continue

        # Context: class
        m_class = re.search(
            r"in (?:public|private|nested) class [\"'`]?(?P<name>[^\"'`]+)[\"'`]?",
            line,
        )
        if m_class:
            current_fn = m_class.group("name")
            continue

        # Context: method
        m_method = re.search(
            r"in (?:public|private|nested) method [\"'`]?(?P<name>[^\"'`]+)[\"'`]?",
            line,
        )
        if m_method:
            current_fn = m_method.group("name")
            continue

        # Fallback: def mentioned
        m4 = re.search(r"def\s+[\"'`]?(?P<name>[A-Za-z_][A-Za-z0-9_]*)", line)
        if m4:
            fn = m4.group("name")
            errors.setdefault(fn, []).append(line)
            current_fn = fn
            continue

        # Last-resort fallback - ONLY add if line contains a D-code
        if re.search(r"D\d{3}", line):
            if current_fn:
                errors.setdefault(current_fn, []).append(line)
            else:
                errors.setdefault("<module>", []).append(line)

    return errors


def run_pydocstyle(file_path: str) -> Tuple[Dict[str, List[str]], bool]:
    """
    Run pydocstyle on a file using the CLI.

    Args:
        file_path: Path to the Python file to analyze

    Returns:
        Tuple of (error mapping, availability flag)
    """
    try:
        proc = subprocess.run(
            ["pydocstyle", file_path],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return ({}, False)

    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    return _parse_pydocstyle_output(out), True


def run_radon_cc(file_path: str) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Compute cyclomatic complexity using radon.

    Args:
        file_path: Path to the Python file to analyze

    Returns:
        Tuple of (complexity results, availability flag)
    """
    try:
        from radon.complexity import cc_visit, cc_rank
    except Exception:
        return ([], False)

    try:
        with open(file_path, "r", encoding="utf-8") as fh:
            src = fh.read()
    except Exception:
        return ([], True)

    try:
        blocks = cc_visit(src)
    except Exception:
        return ([], True)

    results: List[Dict[str, Any]] = []
    for b in blocks:
        entry: Dict[str, Any] = {
            "name": getattr(b, "name", "<unknown>"),
            "lineno": getattr(b, "lineno", None),
            "complexity": getattr(b, "complexity", None),
            "rank": cc_rank(getattr(b, "complexity", 0)),
        }
        if hasattr(b, "endline"):
            entry["endline"] = getattr(b, "endline")
        results.append(entry)

    return (results, True)


def run_validators(file_path: str) -> Dict[str, Any]:
    """
    Run pydocstyle and radon validators on a file.

    Args:
        file_path: Path to the Python file to validate

    Returns:
        Dictionary containing results from both validators
    """
    pydoc_map, pydoc_available = run_pydocstyle(file_path)
    radon_entries, radon_available = run_radon_cc(file_path)

    return {
        "pydocstyle": {"available": pydoc_available, "mapping": pydoc_map},
        "radon": {"available": radon_available, "entries": radon_entries},
    }


def summarize_pydocstyle_on_files(per_file_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Summarize PEP 257 results across parsed files.

    Args:
        per_file_results: List of file analysis results

    Returns:
        Dictionary with summary statistics and violation details
    """
    total_functions = 0
    compliant_functions = 0
    violations_list: List[Dict[str, Any]] = []
    per_file_counts: List[Dict[str, Any]] = []
    any_available = False

    for fr in per_file_results:
        path = fr.get("path")
        funcs = fr.get("functions", []) or []
        has_module = bool(fr.get("has_module_docstring"))

        mapping, available = run_pydocstyle(path)
        if available:
            any_available = True

        file_comp = 0
        file_viol = 0

        # Function-level validation
        for fn in funcs:
            total_functions += 1
            name = fn.get("name")
            errors = mapping.get(name, [])
            if errors:
                file_viol += 1
                violations_list.append(
                    {"file": path, "function": name, "errors": errors}
                )
            else:
                file_comp += 1
                compliant_functions += 1

        # Class-level validation (D101 already filtered at parse stage)
        class_errors = mapping.get("<class>", [])
        if class_errors:
            file_viol += 1
            violations_list.append(
                {"file": path, "function": "<class>", "errors": class_errors}
            )

        # Module-level validation
        # FIXED: Don't manually add D100 error - pydocstyle already detects it
        module_errors = mapping.get("<module>", [])
        
        # Only report if there are actual errors from pydocstyle
        if module_errors:
            file_viol += 1
            violations_list.append(
                {"file": path, "function": "<module>", "errors": module_errors}
            )

        per_file_counts.append(
            {
                "file": path,
                "compliant": file_comp,
                "violations": file_viol,
                "module_docstring": has_module,
            }
        )

    return {
        "available": any_available,
        "total_functions": total_functions,
        "compliant": compliant_functions,
        "violations": len(violations_list),
        "violations_list": violations_list,
        "per_file_counts": per_file_counts,
    }