import json
from typing import List, Dict, Any

def compute_coverage(per_file_results: List[Dict[str, Any]],generate_baseline: bool = False) -> Dict[str, Any]:
    files_report: List[Dict[str, Any]] = []

    agg_total_files = 0
    agg_total_functions = 0
    agg_already_documented = 0
    agg_generated_docstrings = 0
    agg_parsing_errors_total = 0

    for f in per_file_results:
        path = f.get("path", "")
        funcs = f.get("functions", []) or []
        parsing_errors = f.get("parsing_errors", []) or []

        total_functions = len(funcs)
        already_documented = sum(1 for fn in funcs if fn.get("has_docstring"))

        generated_docstrings = 0
        if generate_baseline:
            generated_docstrings = sum(
                1 for fn in funcs if not fn.get("has_docstring")
            )

        coverage_numerator = already_documented + generated_docstrings
        coverage_percent = (
            (coverage_numerator / total_functions) * 100
            if total_functions > 0
            else 100.0
        )

        files_report.append(
            {
                "file_path": path,
                "total_functions": total_functions,
                "already_documented": already_documented,
                "generated_docstrings": generated_docstrings,
                "coverage_percent": round(coverage_percent, 2),
                "parsing_errors": parsing_errors,
            }
        )

        agg_total_files += 1
        agg_total_functions += total_functions
        agg_already_documented += already_documented
        agg_generated_docstrings += generated_docstrings
        agg_parsing_errors_total += len(parsing_errors)

    agg_coverage_percent = (
        ((agg_already_documented + agg_generated_docstrings) / agg_total_functions) * 100
        if agg_total_functions > 0
        else 100.0
    )

    aggregate = {
        "total_files": agg_total_files,
        "total_functions": agg_total_functions,
        "already_documented": agg_already_documented,
        "generated_docstrings": agg_generated_docstrings,
        "coverage_percent": round(agg_coverage_percent, 2),
        "parsing_errors_total": agg_parsing_errors_total,
    }

    return {
        "files": files_report,
        "aggregate": aggregate,
    }


def write_report(report: Dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
