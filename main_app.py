import ast
import difflib
import json
import os

import streamlit as st
import altair as alt

from core.docstring_engine.generator import generate_docstring, generate_module_docstring, insert_module_docstring
from core.parser.python_parser import parse_path
from core.reporter.coverage_reporter import compute_coverage, write_report
from core.validator.validator import run_validators, summarize_pydocstyle_on_files
from core.dashboard.dashboard import render_export_tab, render_search_tab, render_advanced_filters_tab, render_help_tips_tab, render_tests_tab


def insert_or_replace_docstring(file_path: str, func_name: str, doc_body: str) -> bool:
    """
    Insert or replace a function docstring in-place with correct indentation.
    Returns True on success.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            src = f.read()
    except OSError:
        return False

    try:
        tree = ast.parse(src)
    except SyntaxError:
        return False

    lines = src.splitlines()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            def_line = node.lineno - 1

            indent = lines[def_line][: len(lines[def_line]) - len(lines[def_line].lstrip())]
            body_indent = indent + " " * 4

            # D301: Use raw string if docstring contains backslashes
            quote_prefix = 'r' if '\\' in doc_body else ''
            
            new_doc = [body_indent + quote_prefix + '"""']
            for line in doc_body.splitlines():
                new_doc.append(body_indent + line if line.strip() else body_indent)
            new_doc.append(body_indent + '"""')

            # Replace existing docstring
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                start = node.body[0].lineno - 1
                end = node.body[0].end_lineno
                
                # D201: Remove blank lines before the docstring (between def line and docstring)
                # Check lines between def_line and start (docstring) for blank lines
                while start - 1 > def_line and lines[start - 1].strip() == "":
                    start -= 1
                
                # D202: Remove blank lines after the docstring
                while end < len(lines) and lines[end].strip() == "":
                    end += 1
                
                lines = lines[:start] + new_doc + lines[end:]
            else:
                insert_at = node.body[0].lineno - 1 if node.body else def_line + 1
                lines = lines[:insert_at] + new_doc + lines[insert_at:]

            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n")
            except OSError:
                return False

            return True

    return False


# Configure Streamlit
st.set_page_config(page_title="AI Code Reviewer", layout="wide")

# Session State Defaults
if "ui_path_input" not in st.session_state:
    st.session_state["ui_path_input"] = "examples"

if "ui_out_json_input" not in st.session_state:
    st.session_state["ui_out_json_input"] = "storage/review_logs.json"

if "ui_docstring_style" not in st.session_state:
    st.session_state["ui_docstring_style"] = "google"


# Helper callbacks
def _use_examples_folder():
    st.session_state["ui_path_input"] = "examples"
    st.session_state["ui_path"] = "examples"


# Load CSS from external file for better maintainability
def load_css():
    """Load CSS from external file."""
    css_path = os.path.join(os.path.dirname(__file__), "static", "styles.css")
    try:
        with open(css_path, "r", encoding="utf-8") as f:
            return f"<style>{f.read()}</style>"
    except FileNotFoundError:
        return ""

st.markdown(load_css(), unsafe_allow_html=True)

# Header
st.markdown(
    '<div class="topbar"><h1>AI Code Reviewer</h1>'
    '<p>Made by Agniva Bhattacharya</p></div>',
    unsafe_allow_html=True,
)

# Layout
left_col, main_col = st.columns([0.95, 3.05])

# Scan Controls (Top of Main Panel)
with main_col:
    st.markdown('<span class="title-badge">🛠️ AST Parsing Controls</span>', unsafe_allow_html=True)

    c1, c2 = st.columns([3, 1])
    with c1:
        path = st.text_input("Path to scan", key="ui_path_input")
        out_json = st.text_input("Output JSON path", key="ui_out_json_input")

    with c2:
        if st.button("🔍Scan"):
            if not os.path.exists(path):
                st.error("Invalid path.")
            else:
                generate_baseline = st.session_state.get("ui_docstring_style", "google") != "none"

                per_file = parse_path(path, recursive=True)

                for file_result in per_file:
                    v = run_validators(file_result.get("path"))
                    pydoc_map = v["pydocstyle"]["mapping"]
                    # expose module-level pydocstyle errors (if any) on the file result
                    file_result["pydocstyle_module_errors"] = pydoc_map.get("<module>", []) if pydoc_map else []
                    radon_entries = v["radon"]["entries"]
                    radon_by_name = {e.get("name"): e for e in radon_entries}
                    for fn in file_result.get("functions", []):
                        fn_name = fn.get("name")
                        pydoc_errors = pydoc_map.get(fn_name, [])
                        fn["pydocstyle_errors"] = pydoc_errors
                        fn["radon"] = radon_by_name.get(fn_name, {})
                        
                        # Fix: Check both existence AND correctness (no pydocstyle errors)
                        has_doc = bool(fn.get("has_docstring"))
                        is_valid_style = not pydoc_errors
                        fn["is_valid"] = has_doc and is_valid_style

                report = compute_coverage(per_file, generate_baseline)

                os.makedirs(os.path.dirname(out_json) or ".", exist_ok=True)
                write_report(report, out_json)

                st.session_state["last_report"] = report
                st.session_state["last_scan_results"] = per_file

                st.session_state["success_message"] = f"Scan complete — report written to {out_json}"
                st.rerun()

    if "success_message" in st.session_state:
        c2.success(st.session_state["success_message"])
        del st.session_state["success_message"]

# Left Panel
with left_col:
    st.markdown('<div class="sidebar-title">🗃️ Project Files</div>', unsafe_allow_html=True)

    display_path = st.session_state.get("ui_path_input", "examples")
    if os.path.isdir(display_path):
        try:
            files = sorted(f for f in os.listdir(display_path) if f.endswith(".py"))
            if files:
                # If we have previous scan results, use them to show file status badges
                scan_results = st.session_state.get("last_scan_results") or []
                scanned = {os.path.basename(r.get("path", "")): r for r in scan_results}
                for f in files[:20]:
                    badge = ""
                    r = scanned.get(f)
                    if r:
                        funcs = r.get("functions", []) or []
                        # If module docstring missing or any function is invalid, mark the file as needing fixes
                        module_ok = bool(r.get("has_module_docstring", False)) and not bool(r.get("pydocstyle_module_errors", []))
                        needs_fix = (not module_ok) or any(not fn.get("is_valid", False) for fn in funcs)
                        if needs_fix:
                            badge = '<span style="float:right;color:#7a0b0b;font-weight:700;">🔴 Fix</span>'
                        else:
                            badge = '<span style="float:right;color:#0b7a3e;font-weight:700;">🟢 OK</span>'

                    st.markdown(f'<div class="file-item">{f}{badge}</div>', unsafe_allow_html=True)
                if len(files) > 20:
                    st.markdown(f"<div class='muted'>{len(files)-20} more files…</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='muted'>No Python files found.</div>", unsafe_allow_html=True)
        except Exception:
            st.markdown("<div class='muted'>Unable to list files.</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='muted'>Path not available — click Use examples.</div>", unsafe_allow_html=True)

    st.button("📁Use examples folder", on_click=_use_examples_folder)

    DOCSTRING_STYLE_OPTIONS = {
        "Google style docstring.": "google",
        "NumPy style docstring.": "numpy",
        "reStructuredText style docstring.": "rest",
        "None (disable docstring generation).": "none",
    }

    # Initialize widget state from current app state if not present
    if "ui_style_select" not in st.session_state:
        curr = st.session_state.get("ui_docstring_style", "google")
        # Reverse lookup to find label
        initial_label = next(
            (k for k, v in DOCSTRING_STYLE_OPTIONS.items() if v == curr),
            "Google style docstring.",
        )
        st.session_state["ui_style_select"] = initial_label

    st.markdown('<div class="input-label">Docstring style</div>', unsafe_allow_html=True)

    # Bind selectbox to session state key "ui_style_select"
    st.selectbox(
        label="Docstring style selector",
        options=list(DOCSTRING_STYLE_OPTIONS.keys()),
        key="ui_style_select",
        label_visibility="collapsed",
    )

    # Determine new style from widget selection
    selected_label = st.session_state["ui_style_select"]
    new_style = DOCSTRING_STYLE_OPTIONS[selected_label]

    # Check if style changed
    prev_style = st.session_state.get("ui_docstring_style", "google")

    if prev_style != new_style:
        st.session_state["ui_docstring_style"] = new_style

        if "last_scan_results" in st.session_state:
            per_file = st.session_state["last_scan_results"]
            generate_baseline = new_style != "none"
            report = compute_coverage(per_file, generate_baseline)
            st.session_state["last_report"] = report

            out_json = st.session_state["ui_out_json_input"]
            os.makedirs(os.path.dirname(out_json) or ".", exist_ok=True)
            write_report(report, out_json)

    # KPI Section
    report = st.session_state.get("last_report")
    if report:
        agg = report.get("aggregate", {})
        total_functions = agg.get("total_functions", 0)
        # Coverage KPI now shows only already-documented functions (exclude generated baseline)
        already_documented = agg.get("already_documented", 0)
        coverage_val = round((already_documented / total_functions) * 100, 2) if total_functions > 0 else 0.0
    else:
        coverage_val = 0.0
        total_functions = 0

    coverage_deg = int(min(max(coverage_val, 0.0), 100.0) * 3.6)
    func_deg = int(min(max(total_functions, 0), 100) * 3.6)

    coverage_html = f"""
      <div class="kpi" style="background: conic-gradient(from 0deg, #0ea5e9 {coverage_deg}deg, rgba(255,255,255,0.05) {coverage_deg}deg);">
        <div class="kpi-inner">
          <div class="kpi-value">{coverage_val}%</div>
          <div class="kpi-label">Coverage</div>
        </div>
      </div>
    """

    functions_html = f"""
      <div class="kpi" style="background: conic-gradient(from 0deg, #06b6d4 {func_deg}deg, rgba(255,255,255,0.05) {func_deg}deg);">
        <div class="kpi-inner">
          <div class="kpi-value">{total_functions}</div>
          <div class="kpi-label">Functions</div>
        </div>
      </div>
    """

    st.markdown('<div class="kpi-row">', unsafe_allow_html=True)
    st.markdown(coverage_html, unsafe_allow_html=True)
    st.markdown(functions_html, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Main Panel
with main_col:
    tab_dashboard, tab1, tab2, tab3 = st.tabs(["🧰 Dashboard", "📜 Generated Docstrings", "📈 Coverage Report", "📊 Validator"])

    with tab_dashboard:
        st.markdown("#### 🧰 Dashboard")
        
        # Dashboard sub-tabs
        sub_tab1, sub_tab2, sub_tab3, sub_tab4, sub_tab5 = st.tabs(["🔧 Advanced Filters", "🔍 Search", "📤 Export", "🧪 Tests", "💡 Help and Tips"])
        
        with sub_tab1:
            render_advanced_filters_tab()
        
        with sub_tab2:
            render_search_tab()
        
        with sub_tab3:
            render_export_tab()
        
        with sub_tab4:
            render_tests_tab()
        
        with sub_tab5:
            render_help_tips_tab()

    with tab1:
        results = st.session_state.get("last_scan_results", [])
        style = st.session_state.get("ui_docstring_style", "google")
        baseline_on = style != "none"

        if not results:
            st.info("Run Scan to preview docstrings.")
        else:
            options = []
            mapping = {}
            for r in results:
                file_basename = os.path.basename(r.get("path", ""))
                for fn in r.get("functions", []):
                    status = "🟢 Fixed" if fn.get("is_valid") else "🔴 Fix"
                    label = f"{fn.get('name')} {status}"
                    options.append(label)
                    mapping[label] = (r, fn)

            if not options:
                st.markdown(
                    "<div class='muted'>No functions found in scanned files.</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="input-label">Select function to preview</div>',
                    unsafe_allow_html=True,
                )

                # Check for pending selection update from a button click in the previous run
                if "pending_selection" in st.session_state:
                    pending = st.session_state.pop("pending_selection")
                    if pending in options:
                        st.session_state["ui_selected_fn_select"] = pending

                selected_label = st.selectbox(
                    label="Function selector",
                    options=options,
                    index=0,
                    key="ui_selected_fn_select",
                    label_visibility="collapsed",
                )

                # Show success message if present from previous run
                if "temp_success_msg" in st.session_state:
                    st.success(st.session_state["temp_success_msg"])
                    del st.session_state["temp_success_msg"]
                
                # Show info message if present (e.g., no changes)
                if "temp_info_msg" in st.session_state:
                    st.info(st.session_state["temp_info_msg"])
                    del st.session_state["temp_info_msg"]

                selected_r, selected_fn = mapping[selected_label]
                
                # Function info section
                file_path = selected_r.get("path", "")
                file_name = os.path.basename(file_path)
                fn_lines = f"lines {selected_fn.get('start_line')}–{selected_fn.get('end_line')}"
                fn_name_display = selected_fn.get("name", "")
                
                # Styled function metadata card
                st.markdown(f'''
                <div class="info-card">
                    <div class="info-item">
                        <div class="info-item-label">📄 File</div>
                        <div class="info-item-value">{file_name}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-item-label">🔧 Function</div>
                        <div class="info-item-value">{fn_name_display}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-item-label">📍 Location</div>
                        <div class="info-item-value">{fn_lines}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-item-label">🎨 Style</div>
                        <div class="info-item-value">{style.capitalize()}</div>
                    </div>
                </div>
                ''', unsafe_allow_html=True)

                # Create a stable cache key based on function signature + style
                fn_name = selected_fn.get("name", "")
                fn_args = json.dumps(selected_fn.get("args_meta", []), sort_keys=True)
                fn_returns = selected_fn.get("returns", "")
                fn_raises = json.dumps(selected_fn.get("raises", []), sort_keys=True)
                cache_key = f"docstring_cache_{fn_name}_{fn_args}_{fn_returns}_{fn_raises}_{style}"
                
                # Track if user requested regeneration
                regen_flag_key = f"needs_regen_{cache_key}"
                
                # Initialize docstring cache in session state if not present
                if "docstring_cache" not in st.session_state:
                    st.session_state["docstring_cache"] = {}

                before_text = selected_fn.get("docstring") or ""
                
                if baseline_on:
                    # Check if regeneration was requested
                    skip_cache = st.session_state.pop(regen_flag_key, False)
                    
                    # If regeneration requested, delete old cache entry first
                    if skip_cache and cache_key in st.session_state["docstring_cache"]:
                        del st.session_state["docstring_cache"][cache_key]
                    
                    # Check session state cache first
                    if cache_key in st.session_state["docstring_cache"]:
                        after_text = st.session_state["docstring_cache"][cache_key]
                    else:
                        # Generate fresh and cache
                        after_text = generate_docstring(selected_fn, style=style, skip_cache=True)
                        st.session_state["docstring_cache"][cache_key] = after_text
                else:
                    after_text = ""

                # Comparison columns
                col_before, col_after, col_diff = st.columns([1, 1, 1])
                with col_before:
                    st.markdown("#### 📖 Current Docstring")
                    if before_text.strip():
                        st.code(before_text, language="python")
                    else:
                        st.markdown(
                            "<div class='muted'>No docstring present.</div>",
                            unsafe_allow_html=True,
                        )

                with col_after:
                    st.markdown("#### ✨ Generated Preview")
                    if not baseline_on:
                        st.markdown(
                            "<div class='muted'>Generation disabled for style 'none'.</div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        preview = '"""\n' + (after_text.strip() or "") + '\n"""'
                        st.code(preview, language="python")
                        if baseline_on:
                            # Layout for Update and Reject buttons
                            btn_col1, btn_col2 = st.columns([1, 1])

                            with btn_col1:
                                if st.button("✅ Apply", key=f"update_{selected_fn['name']}"):
                                    # Compare cleaned strings to determine if an update is needed
                                    clean_before = before_text.strip()
                                    clean_after = after_text.strip()
                                    if clean_before == clean_after:
                                        st.session_state["temp_info_msg"] = "No changes to update."
                                        st.rerun()
                                    else:
                                        ok = insert_or_replace_docstring(
                                            selected_r["path"],
                                            selected_fn["name"],
                                            after_text,
                                        )
                                        if ok:
                                            # Update the in-memory object referenced by session state
                                            selected_fn["docstring"] = after_text
                                            selected_fn["has_docstring"] = True
                                            selected_fn["pydocstyle_errors"] = []  # Assume fixed
                                            selected_fn["is_valid"] = True

                                            # Construct the new label to preserve selection across rerun
                                            file_basename = os.path.basename(
                                                selected_r.get("path", "")
                                            )
                                            new_status = "🟢 Fixed"
                                            new_label = f"{file_basename} :: {selected_fn.get('name')} (lines {selected_fn.get('start_line')}-{selected_fn.get('end_line')}) {new_status}"

                                            # Store in a temporary state variable to update the widget in the NEXT run
                                            st.session_state["pending_selection"] = new_label

                                            st.session_state[
                                                "temp_success_msg"
                                            ] = "Docstring updated in file!"
                                            st.rerun()

                            with btn_col2:
                                if st.button("❌ Reject", key=f"reject_{selected_fn['name']}"):
                                    # Set flag to skip cache and regenerate fresh docstring
                                    st.session_state[regen_flag_key] = True
                                    st.session_state["temp_info_msg"] = "Generating a new docstring suggestion..."
                                    st.rerun()

                with col_diff:
                    st.markdown("#### 📊 Diff View")
                    before_lines = (before_text or "").splitlines(keepends=True)
                    after_lines = (after_text or "").splitlines(keepends=True)
                    if baseline_on:
                        diff_lines = list(
                            difflib.unified_diff(
                                before_lines,
                                after_lines,
                                fromfile="Before",
                                tofile="After",
                                lineterm="",
                            )
                        )
                        if diff_lines:
                            diff_text = "\n".join(diff_lines)
                            st.code(diff_text, language="diff")
                        else:
                            st.markdown(
                                "<div class='muted'>No changes between Before and After.</div>",
                                unsafe_allow_html=True,
                            )
                    else:
                        st.markdown(
                            "<div class='muted'>Generation disabled — no diff to show.</div>",
                            unsafe_allow_html=True,
                        )

    with tab2:
        report = st.session_state.get("last_report")
        results = st.session_state.get("last_scan_results", [])

        if not report or not results:
            st.info("Run Scan to compute coverage.")
        else:
            # Coverage table
            st.markdown("#### 📊 File-by-File Coverage")
            rows = []
            for p in report.get("files", []):
                rows.append(
                    {
                        "File": p.get("file_path"),
                        "Functions": p.get("total_functions"),
                        "Already Documented": p.get("already_documented", 0),
                        "Generated Docstrings": p.get("generated_docstrings", 0),
                        "Parsing Errors": len(p.get("parsing_errors", [])),
                    }
                )

            st.dataframe(rows, width="stretch")

            st.download_button(
                "⬇️ Download Report JSON",
                data=json.dumps(report, indent=2),
                file_name=os.path.basename(
                    st.session_state.get("ui_out_json_input", "review_logs.json")
                ),
                mime="application/json",
            )

            # File details section
            st.markdown("#### 📂 File Details")

            for r in results:
                file_name = os.path.basename(r.get("path", "unknown"))
                func_count = len(r.get("functions", []))
                with st.expander(f"📄 {file_name} — {func_count} function(s)", expanded=False):
                    
                    # Imports section
                    st.markdown("**📦 Imports**")
                    imports = r.get("imports", [])
                    if imports:
                        st.code("\n".join(imports), language="python")
                    else:
                        st.caption("No imports found.")

                    # Parsing errors section
                    pe = r.get("parsing_errors", []) or []
                    if pe:
                        st.markdown("**⚠️ Parsing Errors**")
                        for i, err in enumerate(pe, 1):
                            st.error(f"Error {i}: {err}")

                    # Functions section with structured display
                    st.markdown("**🔧 Functions**")
                    for fn in r.get("functions", []):
                        fn_status = "✅" if fn.get("has_docstring") else "❌"
                        with st.container():
                            st.markdown(f"##### {fn_status} `{fn.get('name')}` (lines {fn.get('start_line')}–{fn.get('end_line')})")
                            
                            # Function metadata in columns
                            c1, c2, c3 = st.columns(3)
                            with c1:
                                st.caption("**Arguments**")
                                args = fn.get("args", [])
                                st.text(", ".join(args) if args else "None")
                            with c2:
                                st.caption("**Returns**")
                                st.text(fn.get("returns") or "None")
                            with c3:
                                st.caption("**Raises**")
                                raises = fn.get("raises", [])
                                st.text(", ".join(raises) if raises else "None")
                            
                            # Additional info row
                            c4, c5, c6 = st.columns(3)
                            with c4:
                                st.caption("**Yields**")
                                st.text("Yes" if fn.get("has_yields") else "No")
                            with c5:
                                st.caption("**Complexity**")
                                st.text(str(fn.get("complexity", "N/A")))
                            with c6:
                                st.caption("**Nesting**")
                                st.text(str(fn.get("nesting", "N/A")))

    with tab3:
        # Auto-rescan if triggered by Fix All button
        if st.session_state.get("trigger_rescan"):
            del st.session_state["trigger_rescan"]
            path = st.session_state.get("last_scan_path", "")
            if path:
                new_results = parse_path(path)
                if new_results:
                    st.session_state["last_scan_results"] = new_results
        
        results = st.session_state.get("last_scan_results", [])

        if not results:
            st.info("Run Scan to compute PEP257 validation summary.")
        else:
            summary = summarize_pydocstyle_on_files(results)

            if not summary.get("available"):
                st.warning(
                    "pydocstyle not available in this environment. Install it to enable validator summaries."
                )

            total = summary.get("total_functions", 0)
            compliant = summary.get("compliant", 0)
            violations = summary.get("violations", 0)

            # Styled summary metrics card
            st.markdown(f'''
            <div class="info-card">
                <div class="info-item">
                    <div class="info-item-label">📊 Total Scanned</div>
                    <div class="info-item-value">{total}</div>
                </div>
                <div class="info-item">
                    <div class="info-item-label">✅ Compliant</div>
                    <div class="info-item-value">{compliant}</div>
                </div>
                <div class="info-item">
                    <div class="info-item-label">❌ Violations</div>
                    <div class="info-item-value">{violations}</div>
                </div>
            </div>
            ''', unsafe_allow_html=True)

            # Chart section
            st.markdown("#### 📈 Compliance Overview")
            
            comp_val = int(summary.get("compliant", 0))
            viol_val = int(summary.get("violations", 0))

            chart_data = [{"label": "Compliant", "Count": comp_val}, {"label": "Violations", "Count": viol_val}]
            base = alt.Chart(alt.Data(values=chart_data))

            bar = (
                base.mark_bar()
                .encode(
                    x=alt.X("label:N", sort=None, axis=alt.Axis(labelAngle=0, title=None)),
                    y=alt.Y("Count:Q", axis=alt.Axis(tickMinStep=1)),
                    color=alt.Color(
                        "label:N",
                        scale=alt.Scale(domain=["Compliant", "Violations"], range=["#16a34a", "#ef4444"]),
                        legend=None,
                    ),
                )
            )

            labels = (
                base.mark_text(dy=-10, color="white", fontWeight="bold")
                .encode(
                    x=alt.X("label:N", sort=None),
                    y=alt.Y("Count:Q"),
                    text=alt.Text("Count:Q"),
                )
            )

            chart = (bar + labels).properties(height=320)

            st.altair_chart(chart, width="stretch")

            # Show success message from Fix All if present
            if "fix_all_success" in st.session_state:
                st.toast(st.session_state["fix_all_success"], icon="🎉")
                del st.session_state["fix_all_success"]

            # Violations section
            if summary.get("violations_list"):
                # Use columns to put header and button on the same row
                v_col1, v_col2 = st.columns([0.7, 0.3])
                
                with v_col1:
                    st.markdown("#### ⚠️ Violation Details")
                    
                with v_col2:
                    # Fix All button - only show if there are violations
                    if violations > 0:
                        if st.button("🔧 Fix All Violations", key="fix_all_pep257", use_container_width=True):
                            # Always use 'google' style for Fix All, independent of UI dropdown
                            style = "google"
                            with st.spinner("Fixing PEP 257 violations with AI..."):
                                fixed_count = 0
                                failed_count = 0
                                processed = set()  # Track processed (file, function) pairs
                                
                                # Iterate through violations and fix each one
                                for v in summary.get("violations_list", []):
                                    file_path = v.get("file")
                                    func_name = v.get("function")
                                    
                                    # Skip if already processed this (file, function) pair
                                    key = (file_path, func_name)
                                    if key in processed:
                                        continue
                                    processed.add(key)
                                    
                                    # Handle module-level violations (D100)
                                    if func_name == "<module>":
                                        try:
                                            # Generate module docstring
                                            module_doc = generate_module_docstring(file_path)
                                            if module_doc:
                                                ok = insert_module_docstring(file_path, module_doc)
                                                if ok:
                                                    # Update in-memory metadata
                                                    for r in results:
                                                        if r.get("path") == file_path:
                                                            r["has_module_docstring"] = True
                                                            r["pydocstyle_module_errors"] = []
                                                            break
                                                    fixed_count += 1
                                                else:
                                                    failed_count += 1
                                            else:
                                                failed_count += 1
                                        except Exception:
                                            failed_count += 1
                                        continue
                                    
                                    # Skip class-level violations (not supported)
                                    if func_name == "<class>":
                                        continue
                                    
                                    # Find the function metadata in results
                                    func_meta = None
                                    file_result = None
                                    for r in results:
                                        if r.get("path") == file_path:
                                            file_result = r
                                            for fn in r.get("functions", []):
                                                if fn.get("name") == func_name:
                                                    func_meta = fn
                                                    break
                                            break
                                    
                                    if func_meta and file_result:
                                        try:
                                            # Generate new docstring using AI (use cache if available)
                                            new_docstring = generate_docstring(func_meta, style=style, skip_cache=False)
                                            
                                            if new_docstring:
                                                # Apply the fix to the source file
                                                ok = insert_or_replace_docstring(file_path, func_name, new_docstring)
                                                if ok:
                                                    # Update in-memory metadata
                                                    func_meta["docstring"] = new_docstring
                                                    func_meta["has_docstring"] = True
                                                    func_meta["pydocstyle_errors"] = []
                                                    func_meta["is_valid"] = True
                                                    fixed_count += 1
                                                else:
                                                    failed_count += 1
                                            else:
                                                failed_count += 1
                                        except Exception:
                                            failed_count += 1
                                
                                # Store success message and rerun to refresh
                                if fixed_count > 0:
                                    msg = f"Fixed {fixed_count} item(s) with AI!"
                                    if failed_count > 0:
                                        msg += f" ({failed_count} could not be fixed)"
                                    st.session_state["fix_all_success"] = msg
                                    # Trigger a rescan to refresh the violations list
                                    st.session_state["trigger_rescan"] = True
                                else:
                                    st.session_state["fix_all_success"] = "No items could be fixed. Try scanning again."
                                
                                st.rerun()
                
                for v in summary.get("violations_list"):
                    file_name = os.path.basename(v.get('file', 'unknown'))
                    func_name = v.get('function', '<unknown>')
                    error_count = len(v.get("errors", []))
                    
                    with st.expander(f"📄 {file_name} :: `{func_name}` — {error_count} error(s)"):
                        errors = v.get("errors", [])
                        if errors:
                            st.error("\n".join(errors))
            else:
                st.success("🎉 No PEP257 docstring violations found!")

            # Files listing intentionally omitted here (shown in Coverage tab)