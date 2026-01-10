import ast
import os
from typing import Any, Dict, List, Optional

# Cache for parsed files: {path: {"mtime": float, "result": Dict}}
# This avoids re-parsing files that haven't changed
_parse_cache: Dict[str, Dict[str, Any]] = {}


def clear_parse_cache() -> None:
    """Clear the file parse cache."""
    global _parse_cache
    _parse_cache.clear()


def _get_annotation_str(node: Optional[ast.AST]) -> Optional[str]:
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        try:
            if isinstance(node, ast.Name):
                return node.id
            if isinstance(node, ast.Attribute):
                parts: List[str] = []
                cur = node
                while isinstance(cur, ast.Attribute):
                    parts.append(cur.attr)
                    cur = cur.value
                if isinstance(cur, ast.Name):
                    parts.append(cur.id)
                return ".".join(reversed(parts))
        except Exception:
            return None
    return None


def _get_default_str(node: Optional[ast.AST]) -> Optional[str]:
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        try:
            return ast.dump(node)
        except Exception:
            return None


def _simple_complexity(node: ast.FunctionDef) -> int:
    count = 1
    for n in ast.walk(node):
        if isinstance(n, (ast.If, ast.For, ast.While, ast.Try, ast.With, ast.AsyncFor)):
            count += 1
        elif isinstance(n, ast.BoolOp):
            count += max(0, len(n.values) - 1)
    return count


def _max_nesting_depth(node: ast.FunctionDef) -> int:
    max_depth = 0

    def _visit(n: ast.AST, depth: int) -> None:
        nonlocal max_depth
        if isinstance(
            n,
            (
                ast.If,
                ast.For,
                ast.While,
                ast.Try,
                ast.With,
                ast.AsyncFor,
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            max_depth = max(max_depth, depth)
            for c in ast.iter_child_nodes(n):
                _visit(c, depth + 1)
        else:
            for c in ast.iter_child_nodes(n):
                _visit(c, depth)

    _visit(node, 0)
    return max_depth


def parse_functions(node: ast.AST, source: str = "") -> List[Dict[str, Any]]:
    """Parse functions from an AST node.
    
    Args:
        node: The AST node to parse.
        source: The original source code (needed to extract function source).
    """
    results: List[Dict[str, Any]] = []

    for fn in [n for n in ast.walk(node) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        args_meta: List[Dict[str, Optional[str]]] = []
        for a in fn.args.args:
            args_meta.append(
                {
                    "name": getattr(a, "arg", None),
                    "annotation": _get_annotation_str(getattr(a, "annotation", None)),
                }
            )

        defaults: List[Optional[str]] = []
        if getattr(fn.args, "defaults", None):
            for d in fn.args.defaults:
                defaults.append(_get_default_str(d))

        doc = ast.get_docstring(fn)

        # Returns
        has_return = any(
            isinstance(n, ast.Return) and n.value is not None
            for n in ast.walk(fn)
        )

        # Yields
        has_yields = False
        yields_type: Optional[str] = None
        for n in ast.walk(fn):
            if isinstance(n, ast.Yield):
                has_yields = True
                yields_type = _get_annotation_str(getattr(fn, "returns", None))
                break

        # Raises
        raises: List[str] = []
        for n in ast.walk(fn):
            if isinstance(n, ast.Raise) and n.exc:
                if isinstance(n.exc, ast.Call):
                    exc_name = _get_annotation_str(n.exc.func)
                else:
                    exc_name = _get_annotation_str(n.exc)
                if exc_name:
                    raises.append(exc_name)

        # Attributes (e.g., self.x = ...)
        attributes: List[str] = []
        for n in ast.walk(fn):
            if isinstance(n, ast.Assign):
                for target in n.targets:
                    if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                        attributes.append(target.attr)

        # Extract function source code (without docstring for cleaner prompt)
        source_code = ""
        if source:
            try:
                source_code = ast.get_source_segment(source, fn) or ""
            except Exception:
                # Fallback: extract from line numbers
                try:
                    lines = source.splitlines()
                    start = (fn.lineno or 1) - 1
                    end = fn.end_lineno or fn.lineno or 1
                    source_code = "\n".join(lines[start:end])
                except Exception:
                    source_code = ""

        results.append(
            {
                "name": fn.name,
                "start_line": getattr(fn, "lineno", None),
                "end_line": getattr(fn, "end_lineno", getattr(fn, "lineno", None)),
                "args": [a["name"] for a in args_meta],
                "args_meta": args_meta,
                "defaults": defaults,
                "returns": _get_annotation_str(getattr(fn, "returns", None)),
                "has_return": has_return,
                "has_yields": has_yields,
                "yields": yields_type,
                "raises": sorted(set(raises)),
                "attributes": sorted(set(attributes)),
                "has_docstring": bool(doc),
                "docstring": doc,
                "complexity": _simple_complexity(fn),
                "nesting": _max_nesting_depth(fn),
                "source_code": source_code,
            }
        )

    return sorted(results, key=lambda x: (x["start_line"] or 0))


def parse_classes(node: ast.AST) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for cls in [n for n in ast.walk(node) if isinstance(n, ast.ClassDef)]:
        methods: List[Dict[str, Any]] = []
        for body_item in cls.body:
            if isinstance(body_item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(
                    {
                        "name": body_item.name,
                        "start_line": getattr(body_item, "lineno", None),
                        "end_line": getattr(body_item, "end_lineno", getattr(body_item, "lineno", None)),
                        "has_docstring": bool(ast.get_docstring(body_item)),
                        "docstring": ast.get_docstring(body_item),
                        "args": [arg.arg for arg in body_item.args.args],
                        "complexity": _simple_complexity(body_item),
                        "nesting": _max_nesting_depth(body_item),
                    }
                )
        results.append(
            {
                "name": cls.name,
                "start_line": getattr(cls, "lineno", None),
                "end_line": getattr(cls, "end_lineno", getattr(cls, "lineno", None)),
                "methods": sorted(methods, key=lambda m: (m["start_line"] or 0)),
                "has_docstring": bool(ast.get_docstring(cls)),
                "docstring": ast.get_docstring(cls),
            }
        )
    return sorted(results, key=lambda x: (x["start_line"] or 0))


def parse_imports(node: ast.AST) -> List[str]:
    found: List[str] = []
    for n in ast.walk(node):
        if isinstance(n, ast.Import):
            for alias in n.names:
                found.append(alias.name)
        elif isinstance(n, ast.ImportFrom):
            module = n.module or ""
            for alias in n.names:
                found.append(f"{module}.{alias.name}" if module else alias.name)
    return sorted(set(found))


def parse_file(path: str, use_cache: bool = True) -> Dict[str, Any]:
    """Parse a Python file and extract its structure.
    
    Args:
        path: Path to the Python file.
        use_cache: If True, skip parsing if file hasn't changed since last parse.
    """
    global _parse_cache
    
    # Check if file exists
    abs_path = os.path.abspath(path)
    
    # Get file modification time
    try:
        mtime = os.path.getmtime(abs_path)
    except OSError:
        mtime = 0
    
    # Check cache - return cached result if file hasn't changed
    if use_cache and abs_path in _parse_cache:
        cached = _parse_cache[abs_path]
        if cached.get("mtime") == mtime:
            return cached["result"]
    
    parsing_errors: List[str] = []

    try:
        with open(path, "r", encoding="utf-8") as fh:
            src = fh.read()
    except Exception as e:
        parsing_errors.append(f"read_error: {type(e).__name__}: {e}")
        return {
            "path": path,
            "imports": [],
            "functions": [],
            "classes": [],
            "has_module_docstring": False,
            "parsing_errors": parsing_errors,
        }

    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        line_text = ""
        try:
            lines = src.splitlines()
            if e.lineno and 1 <= e.lineno <= len(lines):
                line_text = lines[e.lineno - 1]
        except Exception:
            line_text = e.text or ""
        parsing_errors.append(f"SyntaxError: {e.msg} at line {e.lineno}\nText: {line_text}")
        return {
            "path": path,
            "imports": [],
            "functions": [],
            "classes": [],
            "has_module_docstring": False,
            "parsing_errors": parsing_errors,
        }

    result = {
        "path": path,
        "imports": parse_imports(tree),
        "functions": parse_functions(tree, src),
        "classes": parse_classes(tree),
        "has_module_docstring": bool(ast.get_docstring(tree)),
        "parsing_errors": parsing_errors,
    }
    
    # Store in cache
    _parse_cache[abs_path] = {"mtime": mtime, "result": result}
    
    return result


def parse_path(path: str, recursive: bool = True, skip_dirs: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    skip_dirs = skip_dirs or []
    results: List[Dict[str, Any]] = []

    if os.path.isfile(path) and path.endswith(".py"):
        results.append(parse_file(path))
        return results

    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for f in files:
            if f.endswith(".py"):
                results.append(parse_file(os.path.join(root, f)))
        if not recursive:
            break
    return results
