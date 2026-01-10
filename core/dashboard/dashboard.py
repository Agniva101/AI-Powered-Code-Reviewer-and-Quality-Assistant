"""Dashboard export functionality for the AI Code Reviewer."""

import json
import csv
import io
import os
import subprocess
from typing import Any, Dict, List, Optional

import altair as alt
import streamlit as st

def render_export_tab():
    """Render the Export Data tab with JSON and CSV export options.
    
    Displays an export summary showing total functions, documented functions,
    and missing docstrings count. Provides download buttons for JSON and CSV formats.
    """
    # Header with gradient background (matching app theme)
    st.markdown('''
    <div style="
        background: linear-gradient(135deg, #0ea5e9 0%, #0369a1 100%);
        color: white;
        padding: 24px 32px;
        border-radius: 16px;
        margin-bottom: 24px;
    ">
        <h2 style="margin: 0; color: white; font-size: 1.8rem;">📤 Export Data</h2>
        <p style="margin: 8px 0 0 0; color: rgba(255,255,255,0.9); font-size: 14px;">
            Download analysis results in JSON or CSV format
        </p>
    </div>
    ''', unsafe_allow_html=True)
    
    # Get scan results from session state
    results = st.session_state.get("last_scan_results", [])
    
    if not results:
        st.info("Run a scan first to generate exportable data.")
        return
    
    # Calculate summary stats
    total_functions = sum(len(r.get("functions", [])) for r in results)
    documented = sum(
        1 for r in results 
        for fn in r.get("functions", []) 
        if fn.get("has_docstring", False)
    )
    missing = total_functions - documented
    
    # Export Summary Card
    st.markdown(f'''
    <div style="
        background: rgba(14, 165, 233, 0.08);
        border: 1px solid rgba(14, 165, 233, 0.3);
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 24px;
    ">
        <div style="font-weight: 600; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
            📊 Export Summary
        </div>
        <div style="font-size: 14px; line-height: 1.8;">
            • Total Functions: <strong>{total_functions}</strong><br>
            • Documented: <strong>{documented}</strong><br>
            • Missing Docstrings: <strong>{missing}</strong>
        </div>
    </div>
    ''', unsafe_allow_html=True)
    
    # Export buttons
    col1, col2 = st.columns(2)
    
    with col1:
        # Prepare JSON data with same structure as CSV
        json_rows = []
        for r in results:
            file_path = r.get("path", "")
            for fn in r.get("functions", []):
                json_rows.append({
                    "File": file_path,
                    "Function": fn.get("name", ""),
                    "Start Line": fn.get("start_line", ""),
                    "End Line": fn.get("end_line", ""),
                    "Has Docstring": "Yes" if fn.get("has_docstring") else "No",
                    "Is Valid": "Yes" if fn.get("is_valid") else "No",
                    "Complexity": fn.get("radon", {}).get("complexity", "N/A"),
                })
        
        json_data = json.dumps(json_rows, indent=2)
        
        st.download_button(
            label="📋 Export as JSON",
            data=json_data,
            file_name="code_review_report.json",
            mime="application/json",
            use_container_width=True,
        )
        st.caption("📁 JSON format for programmatic access")
    
    with col2:
        # Prepare CSV data
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        
        # Write header
        writer.writerow([
            "File", "Function", "Start Line", "End Line", 
            "Has Docstring", "Is Valid", "Complexity"
        ])
        
        # Write data rows
        for r in results:
            file_path = r.get("path", "")
            for fn in r.get("functions", []):
                writer.writerow([
                    file_path,
                    fn.get("name", ""),
                    fn.get("start_line", ""),
                    fn.get("end_line", ""),
                    "Yes" if fn.get("has_docstring") else "No",
                    "Yes" if fn.get("is_valid") else "No",
                    fn.get("radon", {}).get("complexity", "N/A"),
                ])
        
        csv_data = csv_buffer.getvalue()
        
        st.download_button(
            label="📊 Export as CSV",
            data=csv_data,
            file_name="code_review_report.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.caption("📁 CSV format for Excel/spreadsheets")


def render_advanced_filters_tab():
    """Render the Advanced Filters tab with documentation status filtering.
    
    Provides filtering by documentation status (OK, Fix, All) and displays
    filtered results in a styled table with showing/total count cards.
    """
    
    # Header with gradient background (matching app theme)
    st.markdown('''
    <div style="
        background: linear-gradient(135deg, #0ea5e9 0%, #0369a1 100%);
        color: white;
        padding: 24px 32px;
        border-radius: 16px;
        margin-bottom: 24px;
    ">
        <h2 style="margin: 0; color: white; font-size: 1.8rem;">🔧 Advanced Filters</h2>
        <p style="margin: 8px 0 0 0; color: rgba(255,255,255,0.9); font-size: 14px;">
            Filter dynamically by file, function, and documentation status
        </p>
    </div>
    ''', unsafe_allow_html=True)
    
    # Get scan results from session state
    results = st.session_state.get("last_scan_results", [])
    
    if not results:
        st.info("Run a scan first to use advanced filters.")
        return
    
    # Documentation status filter
    st.markdown("**📊 Documentation status**")
    status_filter = st.selectbox(
        label="Documentation status filter",
        options=["All", "OK", "Fix"],
        key="dashboard_status_filter",
        label_visibility="collapsed",
    )
    
    # Collect all functions
    all_functions = []
    for r in results:
        file_path = r.get("path", "")
        file_name = os.path.basename(file_path)
        for fn in r.get("functions", []):
            all_functions.append({
                "file": file_name,
                "file_path": file_path,
                "name": fn.get("name", ""),
                "has_docstring": fn.get("has_docstring", False),
                "is_valid": fn.get("is_valid", False),
            })
    
    total_count = len(all_functions)
    
    # Filter based on status
    if status_filter == "OK":
        filtered = [f for f in all_functions if f["is_valid"]]
    elif status_filter == "Fix":
        filtered = [f for f in all_functions if not f["is_valid"]]
    else:
        filtered = all_functions
    
    showing_count = len(filtered)
    
    # Showing / Total count cards
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f'''
        <div style="
            background: linear-gradient(135deg, #0ea5e9 0%, #0369a1 100%);
            color: white;
            padding: 20px;
            border-radius: 12px;
            text-align: center;
        ">
            <div style="font-size: 2rem; font-weight: 800; color: white;">{showing_count}</div>
            <div style="font-size: 14px; color: rgba(255,255,255,0.9); font-weight: 600;">Showing</div>
        </div>
        ''', unsafe_allow_html=True)
    
    with col2:
        st.markdown(f'''
        <div style="
            background: linear-gradient(135deg, #0ea5e9 0%, #0369a1 100%);
            color: white;
            padding: 20px;
            border-radius: 12px;
            text-align: center;
        ">
            <div style="font-size: 2rem; font-weight: 800; color: white;">{total_count}</div>
            <div style="font-size: 14px; color: rgba(255,255,255,0.9); font-weight: 600;">Total</div>
        </div>
        ''', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if not filtered:
        st.warning("No functions match the selected filter.")
        return
    
    # Table header
    st.markdown('''
    <div class="dashboard-table-header" style="
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        background: linear-gradient(135deg, #0ea5e9 0%, #0369a1 100%);
        font-weight: 700;
        padding: 12px 16px;
        border-radius: 8px 8px 0 0;
        font-size: 13px;
        text-transform: uppercase;
    ">
        <div>📁 FILE</div>
        <div>🔧 FUNCTION</div>
        <div style="text-align: center;">✅ DOCSTRING</div>
    </div>
    ''', unsafe_allow_html=True)
    
    # Table rows
    for i, fn in enumerate(filtered):
        bg_color = "var(--card-bg)" if i % 2 == 0 else "var(--card-hover-bg)"
        docstring_badge = (
            '<span style="background: #10b981; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600;">✅ Yes</span>'
            if fn["has_docstring"]
            else '<span style="background: #ef4444; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600;">❌ No</span>'
        )
        
        st.markdown(f'''
        <div class="dashboard-table-row" style="
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            background: {bg_color};
            padding: 14px 16px;
            border-left: 1px solid var(--border-color);
            border-right: 1px solid var(--border-color);
            border-bottom: 1px solid var(--border-color);
            font-size: 14px;
        ">
            <div class="file-name">{fn["file"]}</div>
            <div class="fn-name">{fn["name"]}</div>
            <div style="text-align: center;">{docstring_badge}</div>
        </div>
        ''', unsafe_allow_html=True)


def render_search_tab():
    """Render the Search Functions tab with instant search functionality.
    
    Provides a search input to filter functions by name across all parsed files.
    Displays matching results in a styled table.
    """
    
    # Header with gradient background (matching app theme)
    st.markdown('''
    <div style="
        background: linear-gradient(135deg, #0ea5e9 0%, #0369a1 100%);
        color: white;
        padding: 24px 32px;
        border-radius: 16px;
        margin-bottom: 24px;
    ">
        <h2 style="margin: 0; color: white; font-size: 1.8rem;">🔍 Search Functions</h2>
        <p style="margin: 8px 0 0 0; color: rgba(255,255,255,0.9); font-size: 14px;">
            Instant search across all parsed functions
        </p>
    </div>
    ''', unsafe_allow_html=True)
    
    # Get scan results from session state
    results = st.session_state.get("last_scan_results", [])
    
    if not results:
        st.info("Run a scan first to search functions.")
        return
    
    # Search input
    st.markdown("**🔎 Enter function name**")
    search_query = st.text_input(
        label="Search functions",
        placeholder="Enter function name...",
        key="dashboard_search_input",
        label_visibility="collapsed",
    )
    
    # Collect all functions
    all_functions = []
    for r in results:
        file_path = r.get("path", "")
        file_name = os.path.basename(file_path)
        for fn in r.get("functions", []):
            all_functions.append({
                "file": file_name,
                "file_path": file_path,
                "name": fn.get("name", ""),
                "has_docstring": fn.get("has_docstring", False),
            })
    
    # Filter functions based on search query
    if not search_query.strip():
        # Don't show anything until user searches
        st.markdown('''
        <div style="
            background: rgba(14, 165, 233, 0.08);
            border: 1px solid rgba(14, 165, 233, 0.3);
            border-radius: 12px;
            padding: 24px;
            text-align: center;
            color: #64748b;
        ">
            🔍 Enter a function name above to search
        </div>
        ''', unsafe_allow_html=True)
        return
    
    filtered = [
        f for f in all_functions 
        if search_query.lower() in f["name"].lower()
    ]
    
    # Results count bar
    result_text = f'{len(filtered)} results found for "{search_query}"'
    
    st.markdown(f'''
    <div style="
        background: linear-gradient(135deg, #38bdf8 0%, #0284c7 100%);
        color: white;
        padding: 12px 24px;
        border-radius: 8px;
        text-align: center;
        font-weight: 600;
        margin: 16px 0;
    ">
        {result_text}
    </div>
    ''', unsafe_allow_html=True)
    
    if not filtered:
        st.error("No functions match your search.")
        return
    
    # Table header
    st.markdown('''
    <div class="dashboard-table-header" style="
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        background: linear-gradient(135deg, #0ea5e9 0%, #0369a1 100%);
        font-weight: 700;
        padding: 12px 16px;
        border-radius: 8px 8px 0 0;
        font-size: 13px;
        text-transform: uppercase;
    ">
        <div>📁 FILE</div>
        <div>🔧 FUNCTION</div>
        <div style="text-align: center;">✅ DOCSTRING</div>
    </div>
    ''', unsafe_allow_html=True)
    
    # Table rows
    for i, fn in enumerate(filtered):
        bg_color = "var(--card-bg)" if i % 2 == 0 else "var(--card-hover-bg)"
        docstring_badge = (
            '<span style="background: #10b981; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600;">✅ Yes</span>'
            if fn["has_docstring"]
            else '<span style="background: #ef4444; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600;">❌ No</span>'
        )
        
        st.markdown(f'''
        <div class="dashboard-table-row" style="
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            background: {bg_color};
            padding: 14px 16px;
            border-left: 1px solid var(--border-color);
            border-right: 1px solid var(--border-color);
            border-bottom: 1px solid var(--border-color);
            font-size: 14px;
        ">
            <div class="file-name">{fn["file"]}</div>
            <div class="fn-name">{fn["name"]}</div>
            <div style="text-align: center;">{docstring_badge}</div>
        </div>
        ''', unsafe_allow_html=True)


def render_help_tips_tab():
    """Render the Help & Tips tab with contextual help and quick reference guide.
    
    Provides documentation on how to use the AI Code Reviewer app, including
    coverage metrics, function status, docstring styles, and export options.
    """
    # Header with gradient background (matching app theme)
    st.markdown('''
    <div style="
        background: linear-gradient(135deg, #0ea5e9 0%, #0369a1 100%);
        color: white;
        padding: 24px 32px;
        border-radius: 16px;
        margin-bottom: 24px;
    ">
        <h2 style="margin: 0; color: white; font-size: 1.8rem;">💡 Interactive Help & Tips</h2>
        <p style="margin: 8px 0 0 0; color: rgba(255,255,255,0.9); font-size: 14px;">
            Contextual help and quick reference guide
        </p>
    </div>
    ''', unsafe_allow_html=True)
    
    # Info cards in 2x2 grid
    col1, col2 = st.columns(2)
    
    with col1:
        # Getting Started card (green tinted)
        st.markdown('''
        <div style="
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(5, 150, 105, 0.05) 100%);
            border: 1px solid rgba(16, 185, 129, 0.3);
            border-radius: 12px;
            padding: 20px 24px;
            margin-bottom: 16px;
        ">
            <div style="font-weight: 700; font-size: 1.1rem; color: #34d399; margin-bottom: 12px;">
                🚀 Getting Started
            </div>
            <div class="help-card-text" style="font-size: 14px; line-height: 1.8;">
                • Enter a file or folder path in the <strong style="color: #34d399;">Path to scan</strong> field<br>
                • Click <strong style="color: #34d399;">🔍 Scan</strong> to analyze your Python code<br>
                • Use <strong style="color: #34d399;">📁 Use examples folder</strong> for a quick demo<br>
                • Select your preferred docstring style from the sidebar
            </div>
        </div>
        ''', unsafe_allow_html=True)
        
        # Validator & Auto-Fixes card (blue tinted)
        st.markdown('''
        <div style="
            background: linear-gradient(135deg, rgba(14, 165, 233, 0.1) 0%, rgba(3, 105, 161, 0.05) 100%);
            border: 1px solid rgba(14, 165, 233, 0.3);
            border-radius: 12px;
            padding: 20px 24px;
            margin-bottom: 16px;
        ">
            <div style="font-weight: 700; font-size: 1.1rem; color: #38bdf8; margin-bottom: 12px;">
                🔧 Validator & Auto-Fixes
            </div>
            <div class="help-card-text" style="font-size: 14px; line-height: 1.8;">
                • <strong style="color: #38bdf8;">Validator Tab</strong>: Check PEP 257 compliance<br>
                • <strong style="color: #38bdf8;">Fix All Button</strong>: Auto-fix module & function errors<br>
                • <span style="color: #34d399;">🟢 Supports</span>: D100, D102-D107, D200-D210, D400+<br>
                • <span style="color: #f87171;">🔴 Skips</span>: Class docstrings (D101) as per config
            </div>
        </div>
        ''', unsafe_allow_html=True)
    
    with col2:
        # Docstring Styles card (orange/peach tinted)
        st.markdown('''
        <div style="
            background: linear-gradient(135deg, rgba(251, 146, 60, 0.1) 0%, rgba(234, 88, 12, 0.05) 100%);
            border: 1px solid rgba(251, 146, 60, 0.3);
            border-radius: 12px;
            padding: 20px 24px;
            margin-bottom: 16px;
        ">
            <div style="font-weight: 700; font-size: 1.1rem; color: #fb923c; margin-bottom: 12px;">
                📝 Docstring Styles
            </div>
            <div class="help-card-text" style="font-size: 14px; line-height: 1.8;">
                • <strong style="color: #fb923c;">Google</strong>: Args, Returns, Raises sections<br>
                • <strong style="color: #fb923c;">NumPy</strong>: Parameters, Returns with dashes<br>
                • <strong style="color: #fb923c;">reST</strong>: :param, :type, :return directives<br>
                • AI generates style-compliant docstrings automatically
            </div>
        </div>
        ''', unsafe_allow_html=True)
        
        # Export Options card (purple/pink tinted)
        st.markdown('''
        <div style="
            background: linear-gradient(135deg, rgba(168, 85, 247, 0.1) 0%, rgba(126, 34, 206, 0.05) 100%);
            border: 1px solid rgba(168, 85, 247, 0.3);
            border-radius: 12px;
            padding: 20px 24px;
            margin-bottom: 16px;
        ">
            <div style="font-weight: 700; font-size: 1.1rem; color: #c084fc; margin-bottom: 12px;">
                📤 Export Options
            </div>
            <div class="help-card-text" style="font-size: 14px; line-height: 1.8;">
                • <strong style="color: #c084fc;">JSON</strong>: Structured data for programmatic access<br>
                • <strong style="color: #c084fc;">CSV</strong>: Spreadsheet-friendly for Excel analysis<br>
                • Export includes file, function, line numbers, status<br>
                • Use for documentation audits & compliance reports
            </div>
        </div>
        ''', unsafe_allow_html=True)
    
    # Running Tests card (cyan/teal tinted) - full width
    st.markdown('''
    <div style="
        background: linear-gradient(135deg, rgba(6, 182, 212, 0.1) 0%, rgba(8, 145, 178, 0.05) 100%);
        border: 1px solid rgba(6, 182, 212, 0.3);
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 16px;
    ">
        <div style="font-weight: 700; font-size: 1.1rem; color: #22d3ee; margin-bottom: 12px;">
            🧪 Running Tests
        </div>
        <div class="help-card-text" style="font-size: 14px; line-height: 1.8;">
            • <strong style="color: #22d3ee;">43 tests</strong> across 6 test modules covering all core functionality<br>
            • Test modules: <code style="background: rgba(0,0,0,0.2); padding: 2px 6px; border-radius: 4px;">parser</code>, <code style="background: rgba(0,0,0,0.2); padding: 2px 6px; border-radius: 4px;">generator</code>, <code style="background: rgba(0,0,0,0.2); padding: 2px 6px; border-radius: 4px;">validator</code>, <code style="background: rgba(0,0,0,0.2); padding: 2px 6px; border-radius: 4px;">coverage_reporter</code>, <code style="background: rgba(0,0,0,0.2); padding: 2px 6px; border-radius: 4px;">dashboard</code>, <code style="background: rgba(0,0,0,0.2); padding: 2px 6px; border-radius: 4px;">llm_integration</code><br>
            • Use the <strong style="color: #22d3ee;">Tests tab</strong> to run & visualize results<br>
            • Or run manually: <code style="background: rgba(0,0,0,0.2); padding: 2px 6px; border-radius: 4px;">pytest tests/ --json-report --json-report-file=storage/reports/pytest_results.json</code>
        </div>
    </div>
    ''', unsafe_allow_html=True)
    
    # Advanced Usage Guide expander
    with st.expander("📘 Advanced Usage Guide"):
        st.markdown('''
        ### Dashboard Features
        
        **🔧 Fix All Violations**
        - One-click fix for PEP 257 docstring errors in the **Validator** tab
        - **Supported Error Codes**:
          - **Missing Docstrings**: D100 (Module), D102-D105, D107 (Functions/Methods/Init)
          - **Whitespace & Formatting**: D200-D210 (No blank lines, proper indentation)
          - **Quotes**: D300-D301 (Triple double quotes, raw strings for backslashes)
          - **Content & Style**: D400-D413 (First line periods, imperative mood, section formatting)
        - *Note: Class docstrings (D101, D106) are explicitly skipped by design.*
        
        **🔍 Search**
        - Instant search across all parsed functions
        - Filter by function name as you type
        - See docstring status for each result
        
        **📤 Export**
        - Download analysis results in JSON or CSV format
        - Summary shows total, documented, and missing counts
        - Perfect for documentation audits
        
        **🧪 Tests**
        - Click ▶️ **Run Tests** in the Tests tab to execute pytest
        - View pass/fail counts by category with visual charts
        - 43 tests covering: parser, generator, validator, coverage_reporter, dashboard, llm_integration
        
        ---
        
        ### Test Suite Overview
        
        | Module | Tests | Description |
        |--------|-------|-------------|
        | `test_parser.py` | 5 | File/function parsing, imports, classes |
        | `test_generator.py` | 16 | Docstring body builders & PEP 257 fixes |
        | `test_llm_integration.py` | 8 | Prompt building, caching, `generate_docstring()` API |
        | `test_validator.py` | 7 | pydocstyle, radon complexity analysis |
        | `test_coverage_reporter.py` | 3 | Coverage computation, report writing |
        | `test_dashboard.py` | 4 | Result loading, function filtering |
        
        ---
        
        ### Running Tests Manually
        
        ```bash
        # Activate virtual environment first
        & "path/to/ai_powered/Scripts/Activate.ps1"
        
        # Run all tests with JSON report
        pytest tests/ --json-report --json-report-file=storage/reports/pytest_results.json -v
        
        # Run specific test file
        pytest tests/test_parser.py -v
        ```
        
        ---
        
        ### Tips for Best Results
        
        1. **Scan entire projects**: Point to a folder to analyze all Python files recursively
        2. **Use Fix All**: Quickly resolve bulk PEP 257 violations in one go
        3. **Review before applying**: Always preview generated docstrings before applying
        4. **Check Coverage Report**: Monitor your project's documentation coverage over time
        5. **Validate with PEP257**: The Validator tab shows PEP257 compliance issues
        6. **Run tests regularly**: Use the Tests tab to ensure code quality
        ''')


# =============================================================================
# TESTS TAB FUNCTIONS
# =============================================================================

def load_pytest_results() -> Optional[Dict[str, Any]]:
    """Load pytest JSON report from storage/reports/pytest_results.json.
    
    Returns:
        Dictionary containing pytest results, or None if file doesn't exist.
    """
    report_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "storage", "reports", "pytest_results.json"
    )
    report_path = os.path.abspath(report_path)
    
    if not os.path.exists(report_path):
        return None
    
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def filter_functions(
    functions: List[Dict[str, Any]], 
    search: Optional[str] = None, 
    status: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Filter functions by search term and/or status.
    
    Args:
        functions: List of function dictionaries.
        search: Optional search term to filter by name.
        status: Optional status filter ("OK" or "Fix").
    
    Returns:
        Filtered list of functions.
    """
    result = functions
    
    if search:
        search_lower = search.lower()
        result = [f for f in result if search_lower in f.get("name", "").lower()]
    
    if status == "OK":
        result = [f for f in result if f.get("is_valid", False)]
    elif status == "Fix":
        result = [f for f in result if not f.get("is_valid", False)]
    
    return result


def _run_pytest_with_json() -> bool:
    """Run pytest and generate JSON report.
    
    Returns:
        True if pytest ran successfully, False otherwise.
    """
    import sys
    
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    reports_dir = os.path.join(project_root, "storage", "reports")
    
    # Ensure reports directory exists
    os.makedirs(reports_dir, exist_ok=True)
    
    report_path = os.path.join(reports_dir, "pytest_results.json")
    
    try:
        # Use sys.executable to ensure we use the same Python that's running Streamlit
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "--json-report",
                f"--json-report-file={report_path}",
                "-q",
            ],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return result.returncode == 0 or os.path.exists(report_path)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _parse_test_categories(data: Dict[str, Any]) -> Dict[str, Dict[str, int]]:
    """Parse pytest results into test categories with pass/fail counts.
    
    Args:
        data: Pytest JSON report data.
    
    Returns:
        Dictionary mapping category names to pass/fail/total counts.
    """
    categories: Dict[str, Dict[str, int]] = {}
    
    tests = data.get("tests", [])
    
    for test in tests:
        nodeid = test.get("nodeid", "")
        outcome = test.get("outcome", "")
        
        # Parse category from nodeid (e.g., "tests/test_parser.py::test_name")
        if "::" in nodeid:
            file_part = nodeid.split("::")[0]
            # Extract test file name without path and extension
            file_name = os.path.basename(file_part).replace("test_", "").replace(".py", "")
            # Convert to title case for display
            category = file_name.replace("_", " ").title() + " Tests"
        else:
            category = "Other Tests"
        
        if category not in categories:
            categories[category] = {"passed": 0, "failed": 0, "total": 0}
        
        categories[category]["total"] += 1
        if outcome == "passed":
            categories[category]["passed"] += 1
        else:
            categories[category]["failed"] += 1
    
    return categories


def render_tests_tab():
    """Render the Tests tab with pytest results visualization.
    
    Shows an Altair bar chart of passed tests per category and
    styled test result cards with pass/total counts.
    """
    # Header with gradient background (matching app theme)
    st.markdown('''
    <div style="
        background: linear-gradient(135deg, #0ea5e9 0%, #0369a1 100%);
        color: white;
        padding: 24px 32px;
        border-radius: 16px;
        margin-bottom: 24px;
    ">
        <h2 style="margin: 0; color: white; font-size: 1.8rem;">🧪 Tests</h2>
        <p style="margin: 8px 0 0 0; color: rgba(255,255,255,0.9); font-size: 14px;">
            Run and visualize pytest results
        </p>
    </div>
    ''', unsafe_allow_html=True)
    
    # Run Tests button
    col1, col2 = st.columns([1, 4])
    with col1:
        run_clicked = st.button("▶️ Run Tests", key="run_tests_btn")
    
    if run_clicked:
        with st.spinner("Running pytest..."):
            success = _run_pytest_with_json()
            if success:
                st.success("Tests completed! Results updated.")
                st.rerun()
            else:
                st.error("Failed to run pytest. Make sure pytest and pytest-json-report are installed.")
    
    # Load and display results
    data = load_pytest_results()
    
    if not data:
        st.info("No test results found. Click 'Run Tests' to execute pytest and generate results.")
        
        # Installation hint
        st.markdown('''
        <div style="
            background: rgba(251, 191, 36, 0.1);
            border: 1px solid rgba(251, 191, 36, 0.3);
            border-radius: 12px;
            padding: 20px 24px;
            margin-top: 16px;
        ">
            <div style="font-weight: 600; margin-bottom: 12px;">💡 First time setup</div>
            <div style="font-size: 14px; margin-bottom: 12px;">
                Make sure <code style="background: rgba(0,0,0,0.15); padding: 2px 6px; border-radius: 4px;">pytest-json-report</code> is installed:
            </div>
            <div style="
                background: #1e293b;
                color: #22d3ee;
                padding: 12px 16px;
                border-radius: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 14px;
            ">
                pip install pytest-json-report
            </div>
        </div>
        ''', unsafe_allow_html=True)
        return
    
    # Parse categories
    categories = _parse_test_categories(data)
    
    if not categories:
        st.warning("No test results to display.")
        return
    
    # Summary stats
    summary = data.get("summary", {})
    total_tests = summary.get("total", 0)
    passed_tests = summary.get("passed", 0)
    failed_tests = summary.get("failed", 0)
    # Duration is at top level in pytest-json-report output
    duration = data.get("duration", 0)
    
    # Summary cards
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.markdown(f'''
        <div style="
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            padding: 16px;
            border-radius: 12px;
            text-align: center;
        ">
            <div style="font-size: 1.8rem; font-weight: 800; color: white;">{passed_tests}</div>
            <div style="font-size: 12px; font-weight: 600; opacity: 0.9; color: white;">PASSED</div>
        </div>
        ''', unsafe_allow_html=True)
    
    with c2:
        st.markdown(f'''
        <div style="
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            color: white;
            padding: 16px;
            border-radius: 12px;
            text-align: center;
        ">
            <div style="font-size: 1.8rem; font-weight: 800; color: white;">{failed_tests}</div>
            <div style="font-size: 12px; font-weight: 600; opacity: 0.9; color: white;">FAILED</div>
        </div>
        ''', unsafe_allow_html=True)
    
    with c3:
        st.markdown(f'''
        <div style="
            background: linear-gradient(135deg, #0ea5e9 0%, #0369a1 100%);
            color: white;
            padding: 16px;
            border-radius: 12px;
            text-align: center;
        ">
            <div style="font-size: 1.8rem; font-weight: 800; color: white;">{total_tests}</div>
            <div style="font-size: 12px; font-weight: 600; opacity: 0.9; color: white;">TOTAL</div>
        </div>
        ''', unsafe_allow_html=True)
    
    with c4:
        st.markdown(f'''
        <div style="
            background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
            color: white;
            padding: 16px;
            border-radius: 12px;
            text-align: center;
        ">
            <div style="font-size: 1.8rem; font-weight: 800; color: white;">{duration:.2f}s</div>
            <div style="font-size: 12px; font-weight: 600; opacity: 0.9; color: white;">DURATION</div>
        </div>
        ''', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Altair bar chart - stacked with passed (green) and failed (red)
    st.markdown("#### 📊 Tests by Category")
    
    # Build chart data with both passed and failed
    chart_data = []
    for cat, counts in sorted(categories.items()):
        chart_data.append({"Category": cat, "Status": "Passed", "Count": counts["passed"]})
        if counts["failed"] > 0:
            chart_data.append({"Category": cat, "Status": "Failed", "Count": counts["failed"]})
    
    chart = alt.Chart(alt.Data(values=chart_data)).mark_bar(
        cornerRadiusTopLeft=4,
        cornerRadiusTopRight=4,
    ).encode(
        x=alt.X("Category:N", sort=None, axis=alt.Axis(labelAngle=-45, title=None)),
        y=alt.Y("Count:Q", axis=alt.Axis(tickMinStep=1, title="Tests")),
        color=alt.Color(
            "Status:N",
            scale=alt.Scale(domain=["Passed", "Failed"], range=["#10b981", "#ef4444"]),
            legend=alt.Legend(title="Status", orient="top"),
        ),
        order=alt.Order("Status:N", sort="descending"),  # Failed on top
        tooltip=[alt.Tooltip("Category:N"), alt.Tooltip("Status:N"), alt.Tooltip("Count:Q")],
    ).properties(
        height=300,
    )
    
    st.altair_chart(chart, width="stretch")
    
    # Test result cards
    st.markdown("#### 📋 Test Results by Category")
    
    for category, counts in sorted(categories.items()):
        passed = counts["passed"]
        total = counts["total"]
        all_passed = passed == total
        
        # Card styling based on pass/fail status
        if all_passed:
            border_color = "#10b981"
            bg_color = "rgba(16, 185, 129, 0.08)"
            icon = "✅"
        else:
            border_color = "#ef4444"
            bg_color = "rgba(239, 68, 68, 0.08)"
            icon = "❌"
        
        st.markdown(f'''
        <div style="
            background: {bg_color};
            border-left: 4px solid {border_color};
            border-radius: 0 8px 8px 0;
            padding: 16px 20px;
            margin-bottom: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        ">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 1.2rem;">{icon}</span>
                <span style="font-weight: 600;">{category}</span>
            </div>
            <div style="font-weight: 600; color: {'#10b981' if all_passed else '#ef4444'};">
                {passed}/{total} passed
            </div>
        </div>
        ''', unsafe_allow_html=True)

