import hashlib
import json
import os
import random
import re
from typing import Dict, List, Optional

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

# Load environment variables
load_dotenv()

# Initialize Groq client
_groq_client: Optional[ChatGroq] = None

# Cache for generated docstrings to reduce API calls
# Key: hash of (func_name, args, returns, style)
# Value: generated docstring
_docstring_cache: Dict[str, str] = {}

# Pre-compiled regex patterns for performance (compiled once at module load)
_GOOGLE_SECTION_PATTERN = re.compile(
    r'^(Args|Parameters|Returns|Raises|Yields|Attributes|Examples?|Notes?|See Also|Warnings?):',
    re.IGNORECASE
)
_NUMPY_SECTION_PATTERN = re.compile(
    r'^(Parameters|Returns|Raises|Yields|Attributes|Examples?|Notes?|See Also|Warnings?)\s*$',
    re.IGNORECASE
)
_REST_SECTION_PATTERN = re.compile(
    r'^:(param|returns?|rtype|raises?|yields?|type|note|example)',
    re.IGNORECASE
)
_EXCEPTION_PATTERN = re.compile(r'^[A-Z][a-zA-Z]*(Error|Exception)$')
_MULTIPLE_NEWLINES_PATTERN = re.compile(r'\n{3,}')

# Common non-imperative to imperative verb mappings for D401 fix
_IMPERATIVE_FIXES = {
    # Third person singular -> Imperative
    "Raises": "Raise",
    "Returns": "Return",
    "Yields": "Yield",
    "Calculates": "Calculate",
    "Computes": "Compute",
    "Creates": "Create",
    "Generates": "Generate",
    "Gets": "Get",
    "Sets": "Set",
    "Checks": "Check",
    "Validates": "Validate",
    "Parses": "Parse",
    "Processes": "Process",
    "Handles": "Handle",
    "Executes": "Execute",
    "Performs": "Perform",
    "Builds": "Build",
    "Initializes": "Initialize",
    "Converts": "Convert",
    "Extracts": "Extract",
    "Loads": "Load",
    "Saves": "Save",
    "Writes": "Write",
    "Reads": "Read",
    "Sends": "Send",
    "Receives": "Receive",
    "Updates": "Update",
    "Deletes": "Delete",
    "Removes": "Remove",
    "Adds": "Add",
    "Inserts": "Insert",
    "Finds": "Find",
    "Searches": "Search",
    "Sorts": "Sort",
    "Filters": "Filter",
    "Maps": "Map",
    "Reduces": "Reduce",
    "Transforms": "Transform",
    "Applies": "Apply",
    "Runs": "Run",
    "Starts": "Start",
    "Stops": "Stop",
    "Opens": "Open",
    "Closes": "Close",
    "Connects": "Connect",
    "Disconnects": "Disconnect",
    "Formats": "Format",
    "Prints": "Print",
    "Logs": "Log",
    "Tests": "Test",
    "Verifies": "Verify",
    "Determines": "Determine",
    "Evaluates": "Evaluate",
    "Fetches": "Fetch",
    "Retrieves": "Retrieve",
    "Stores": "Store",
    "Caches": "Cache",
    "Clears": "Clear",
    "Resets": "Reset",
    "Copies": "Copy",
    "Moves": "Move",
    "Merges": "Merge",
    "Splits": "Split",
    "Joins": "Join",
    "Concatenates": "Concatenate",
    "Appends": "Append",
    "Prepends": "Prepend",
    "Wraps": "Wrap",
    "Unwraps": "Unwrap",
    "Encodes": "Encode",
    "Decodes": "Decode",
    "Encrypts": "Encrypt",
    "Decrypts": "Decrypt",
    "Compresses": "Compress",
    "Decompresses": "Decompress",
    "Serializes": "Serialize",
    "Deserializes": "Deserialize",
    "Normalizes": "Normalize",
    "Sanitizes": "Sanitize",
    "Escapes": "Escape",
    "Unescapes": "Unescape",
    "Trims": "Trim",
    "Strips": "Strip",
    "Pads": "Pad",
    "Aligns": "Align",
    "Centers": "Center",
    "Justifies": "Justify",
    "Truncates": "Truncate",
    "Expands": "Expand",
    "Collapses": "Collapse",
    "Flattens": "Flatten",
    "Groups": "Group",
    "Partitions": "Partition",
    "Chunks": "Chunk",
    "Batches": "Batch",
    "Queues": "Queue",
    "Dequeues": "Dequeue",
    "Pushes": "Push",
    "Pops": "Pop",
    "Peeks": "Peek",
    "Polls": "Poll",
    "Waits": "Wait",
    "Sleeps": "Sleep",
    "Delays": "Delay",
    "Schedules": "Schedule",
    "Dispatches": "Dispatch",
    "Invokes": "Invoke",
    "Calls": "Call",
    "Triggers": "Trigger",
    "Emits": "Emit",
    "Publishes": "Publish",
    "Subscribes": "Subscribe",
    "Unsubscribes": "Unsubscribe",
    "Listens": "Listen",
    "Broadcasts": "Broadcast",
    "Notifies": "Notify",
    "Alerts": "Alert",
    "Warns": "Warn",
    "Configures": "Configure",
    "Registers": "Register",
    "Unregisters": "Unregister",
    "Binds": "Bind",
    "Unbinds": "Unbind",
    "Attaches": "Attach",
    "Detaches": "Detach",
    "Mounts": "Mount",
    "Unmounts": "Unmount",
    "Enables": "Enable",
    "Disables": "Disable",
    "Activates": "Activate",
    "Deactivates": "Deactivate",
    "Locks": "Lock",
    "Unlocks": "Unlock",
    "Acquires": "Acquire",
    "Releases": "Release",
    "Allocates": "Allocate",
    "Deallocates": "Deallocate",
    "Frees": "Free",
    "Disposes": "Dispose",
    "Destroys": "Destroy",
    "Terminates": "Terminate",
    "Aborts": "Abort",
    "Cancels": "Cancel",
    "Interrupts": "Interrupt",
    "Resumes": "Resume",
    "Pauses": "Pause",
    "Suspends": "Suspend",
    "Restarts": "Restart",
    "Reboots": "Reboot",
    "Refreshes": "Refresh",
    "Reloads": "Reload",
    "Syncs": "Sync",
    "Synchronizes": "Synchronize",
    "Imports": "Import",
    "Exports": "Export",
    "Downloads": "Download",
    "Uploads": "Upload",
    "Installs": "Install",
    "Uninstalls": "Uninstall",
    "Deploys": "Deploy",
    "Undeploys": "Undeploy",
    "Migrates": "Migrate",
    "Upgrades": "Upgrade",
    "Downgrades": "Downgrade",
    "Patches": "Patch",
    "Fixes": "Fix",
    "Repairs": "Repair",
    "Recovers": "Recover",
    "Restores": "Restore",
    "Backs": "Back",  # "Backs up" -> "Back up"
    "Doubles": "Double",
}


def _fix_imperative_mood(content: str) -> str:
    """Fix D401 imperative mood violations in the first line of docstring.
    
    Converts common non-imperative verbs (e.g., 'Raises', 'Returns') to
    their imperative form (e.g., 'Raise', 'Return').
    """
    if not content:
        return content
    
    lines = content.split('\n')
    if not lines:
        return content
    
    first_line = lines[0]
    
    # Check if the first word needs to be converted to imperative
    words = first_line.split(' ', 1)
    if words:
        first_word = words[0]
        if first_word in _IMPERATIVE_FIXES:
            # Replace with imperative form
            imperative = _IMPERATIVE_FIXES[first_word]
            if len(words) > 1:
                lines[0] = imperative + ' ' + words[1]
            else:
                lines[0] = imperative
    
    return '\n'.join(lines)


def _fix_pep257_first_line(content: str) -> str:
    """Fix PEP 257 first-line issues: D400, D403, D404.
    
    - D400: First line should end with a period
    - D403: First word should be properly capitalized
    - D404: First word should not be "This"
    """
    if not content:
        return content
    
    lines = content.split('\n')
    if not lines:
        return content
    
    first_line = lines[0].strip()
    
    if not first_line:
        return content
    
    # D404: Remove "This" from the start and rephrase
    if first_line.lower().startswith("this "):
        # Try to extract the meaningful part after "This"
        # e.g., "This function calculates..." -> "Calculate..."
        rest = first_line[5:].strip()
        if rest:
            # Common patterns: "This function/method/class X" -> remove and capitalize
            for pattern in ["function ", "method ", "class ", "module ", "is a ", "is an ", "will "]:
                if rest.lower().startswith(pattern):
                    rest = rest[len(pattern):]
                    break
            first_line = rest
    
    # D403: Capitalize first word
    if first_line and first_line[0].islower():
        first_line = first_line[0].upper() + first_line[1:]
    
    # D400: Ensure first line ends with a period
    if first_line and not first_line.endswith('.'):
        # Don't add period if it ends with other punctuation
        if not first_line[-1] in '!?:':
            first_line = first_line + '.'
    
    lines[0] = first_line
    return '\n'.join(lines)


def _get_groq_client() -> ChatGroq:
    """Get or create the Groq client singleton."""
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        _groq_client = ChatGroq(
            api_key=api_key,
            model_name="llama-3.1-8b-instant",
            temperature=0.3,
        )
    return _groq_client


def _build_groq_prompt(func_meta: Dict, style: str, variation_seed: int = 0) -> str:
    """Build the prompt for Groq to generate a docstring.
    
    Args:
        func_meta: Function metadata.
        style: Docstring style.
        variation_seed: Random seed to add variation to prompts for regeneration.
    """
    name = func_meta.get("name", "<function>")
    args_meta = func_meta.get("args_meta", [])
    has_return = func_meta.get("has_return", False)
    returns = func_meta.get("returns")
    raises = func_meta.get("raises", [])
    yields = func_meta.get("yields")
    attributes = func_meta.get("attributes", [])
    
    # Add variation hint for regeneration requests
    variation_hints = [
        "",
        "Use clear and professional language.",
        "Focus on clarity and brevity.",
        "Emphasize the function's purpose.",
        "Use descriptive parameter explanations.",
        "Be precise about types and returns.",
        "Write in an informative tone.",
        "Prioritize readability.",
    ]
    variation_hint = variation_hints[variation_seed % len(variation_hints)]

    
    # Style-specific instructions
    style_instructions = {
        "google": """Generate a Google-style docstring with these sections (if applicable):
- One-line summary (imperative mood, e.g., "Calculate the sum...")
- Blank line after summary
- Args: section with each parameter on its own line, indented with 4 spaces
- Returns: section describing what is returned
- Yields: section if the function yields values
- Raises: section listing exceptions that may be raised
- Attributes: section if applicable

Example format:
Short description of the function.

Args:
    param1 (type): Description of param1.
    param2 (type): Description of param2.

Returns:
    type: Description of return value.

Raises:
    ExceptionType: When this exception is raised.""",

        "numpy": """Generate a NumPy-style docstring with these sections (if applicable):
- One-line summary
- Blank line after summary
- Parameters section with dashed underline
- Returns section with dashed underline
- Yields section if applicable
- Raises section if applicable
- Attributes section if applicable

Example format:
Short description of the function.

Parameters
----------
param1 : type
    Description of param1.
param2 : type
    Description of param2.

Returns
-------
type
    Description of return value.

Raises
------
ExceptionType
    When this exception is raised.""",

        "rest": """Generate a reStructuredText-style docstring with these sections (if applicable):
- One-line summary
- Blank line after summary
- :param directives for each parameter
- :returns: directive for return value
- :rtype: directive for return type
- :raises: directives for exceptions
- :yields: directive if applicable

Example format:
Short description of the function.

:param type param1: Description of param1.
:param type param2: Description of param2.
:returns: Description of return value.
:rtype: type
:raises ExceptionType: When this exception is raised."""
    }
    
    style_instruction = style_instructions.get(style, style_instructions["google"])
    
    # Get the actual function source code
    source_code = func_meta.get("source_code", "")
    
    # Build variation instruction if present
    variation_instruction = f"\n{variation_hint}" if variation_hint else ""
    
    # If source code is available, use it directly for the most accurate docstring
    if source_code:
        prompt = f"""Analyze this Python function and generate a docstring for it.

```python
{source_code}
```

Generate a docstring in the following style:
{style_instruction}

RULES:
- Analyze the ACTUAL code to understand what it does
- Only include Returns section if the function has an explicit return statement that returns a value
- Do NOT include "Returns: None" or any Returns section for functions that don't return anything
- Only include Raises section if the code contains an explicit `raise ExceptionType` statement
- Do NOT include Raises section for potential runtime errors like TypeError, AttributeError, etc. unless they are EXPLICITLY raised with the `raise` keyword in the function body
- Do NOT include "Raises: None" or any Raises section if no `raise` statements exist in the code
- Only include Yields section if the code actually uses `yield`
- Infer parameter types from how they are used in the code
- Be accurate and concise
- Return ONLY the docstring content, no triple quotes
- Do NOT include any preamble like "Here's the docstring" or "Here is the Google-style docstring"
- Do NOT suggest code changes, refactoring, or improvements to the function
- Do NOT rewrite or modify the function in any way
- Do NOT include example code, usage examples, or code snippets
- Do NOT include "Note:", "Example:", "See Also:", or any other extra sections
- Do NOT include commentary about the function's design or structure
- ONLY output the docstring text itself, nothing else
- Start directly with the docstring summary line

PEP 257 COMPLIANCE (CRITICAL - follow these exactly):
- D400: First line MUST end with a period (.)
- D401: First line MUST be in IMPERATIVE mood (e.g., "Calculate the sum" NOT "Calculates the sum")
- D403: First word MUST be properly capitalized (start with uppercase letter)
- D404: First word should NOT be "This"
- D402: First line should NOT be the function signature
- D200: If the docstring is short enough, keep it on one line
- D205: Put a blank line between the summary line and the description/Args section
- D300: Use triple double quotes (the inserter handles this)
- D405-D413: Section headers must be properly formatted:
  * Section names capitalized (Args, Returns, Raises, Yields)
  * Blank line before each section
  * No blank lines between section header and its content{variation_instruction}
"""
    else:
        # Fallback to metadata-based prompt if no source code
        args_info = []
        for arg in args_meta:
            arg_type = arg.get("annotation") or "infer from context"
            args_info.append(f"  - {arg['name']}: {arg_type}")
        
        args_str = "\n".join(args_info) if args_info else ""
        
        prompt = f"""Generate a Python docstring for the function: {name}

Parameters:
{args_str}

{"Returns: " + (returns or "has a return statement") if has_return else ""}
{"Raises: " + ", ".join(raises) if raises else ""}
{"Yields: " + yields if yields else ""}

{style_instruction}

Return ONLY the docstring content, no triple quotes."""
    return prompt


def _create_cache_key(func_meta: Dict, style: str) -> str:
    """Create a unique cache key based on function metadata and style."""
    # Extract relevant fields for caching
    cache_data = {
        "name": func_meta.get("name", ""),
        "args_meta": func_meta.get("args_meta", []),
        "has_return": func_meta.get("has_return", False),
        "returns": func_meta.get("returns"),
        "raises": func_meta.get("raises", []),
        "has_yields": func_meta.get("has_yields", False),
        "yields": func_meta.get("yields"),
        "style": style,
        "source_code": func_meta.get("source_code", ""),
    }
    # Create a hash of the cache data
    cache_str = json.dumps(cache_data, sort_keys=True)
    return hashlib.md5(cache_str.encode()).hexdigest()


def _post_process_docstring(content: str, func_meta: Dict, style: str) -> str:
    """Remove hallucinated sections from AI-generated docstrings.
    
    If the function metadata shows no raises/returns/yields, strip those sections
    from the generated docstring to prevent hallucinations.
    """
    
    # Determine what sections are actually valid based on metadata
    has_raises = bool(func_meta.get("raises", []))
    has_return = func_meta.get("has_return", False)
    has_yields = func_meta.get("has_yields", False)
    
    # Define invalid sections based on metadata
    invalid_sections = set()
    if not has_raises:
        invalid_sections.add("raises")
    if not has_return:
        invalid_sections.add("returns")
    if not has_yields:
        invalid_sections.add("yields")
    # Always remove Note/Example/Attributes sections (not applicable to functions)
    invalid_sections.add("note")
    invalid_sections.add("example")
    invalid_sections.add("see also")
    invalid_sections.add("attributes")  # D414: Functions don't have attributes
    
    # Use pre-compiled section patterns for different styles
    if style == "numpy":
        section_pattern = _NUMPY_SECTION_PATTERN
    elif style in ("rest", "restructuredtext"):
        section_pattern = _REST_SECTION_PATTERN
    else:
        section_pattern = _GOOGLE_SECTION_PATTERN
    
    lines = content.split('\n')
    result_lines = []
    current_section = None  # Track which section we're in
    skip_current_section = False
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Check if this line starts a new section
        section_match = section_pattern.match(stripped)
        
        if section_match:
            section_name = section_match.group(1).lower() if section_match.lastindex else section_match.group(0).lower()
            # Normalize section names
            section_name = section_name.replace(":", "").strip()
            if section_name in ("raise", "raised"):
                section_name = "raises"
            elif section_name in ("return", "rtype"):
                section_name = "returns"
            elif section_name in ("yield",):
                section_name = "yields"
            elif section_name in ("examples",):
                section_name = "example"
            elif section_name in ("notes",):
                section_name = "note"
            
            current_section = section_name
            skip_current_section = section_name in invalid_sections
            
            if skip_current_section:
                i += 1
                # For NumPy style, also skip the underline
                if style == "numpy" and i < len(lines) and lines[i].strip() and all(c == '-' for c in lines[i].strip()):
                    i += 1
                continue
        
        # For NumPy style, check if this is an underline following a section we're skipping
        if style == "numpy" and stripped and all(c == '-' for c in stripped) and skip_current_section:
            i += 1
            continue
        
        # If we're in a section that should be skipped, check if content belongs to it
        if skip_current_section:
            # Content lines are usually indented or empty
            # A new section starts when we see a non-indented, non-empty line that matches section pattern
            # Or for reST, a line starting with :
            is_content = stripped == "" or line.startswith("    ") or line.startswith("\t")
            
            if style in ("rest", "restructuredtext"):
                # reST: each :directive: is its own "section"
                if stripped.startswith(":"):
                    section_match = section_pattern.match(stripped)
                    if section_match:
                        section_name = section_match.group(1).lower()
                        if section_name in ("raise", "raises"):
                            section_name = "raises"
                        elif section_name in ("return", "returns", "rtype"):
                            section_name = "returns"
                        elif section_name in ("yield", "yields"):
                            section_name = "yields"
                        
                        current_section = section_name
                        skip_current_section = section_name in invalid_sections
                        if skip_current_section:
                            i += 1
                            continue
                        else:
                            result_lines.append(line)
                            i += 1
                            continue
            
            if is_content:
                i += 1
                continue
            else:
                # New non-indented content means new section or end of section
                skip_current_section = False
                current_section = None
        
        result_lines.append(line)
        i += 1
    
    # Clean up extra blank lines
    result = '\n'.join(result_lines)
    result = _MULTIPLE_NEWLINES_PATTERN.sub('\n\n', result)  # Max 2 newlines in a row
    
    # Additional cleanup for hallucinated content
    lines = result.split('\n')
    cleaned_lines = []
    
    # Get actual raises from metadata
    actual_raises = set(func_meta.get("raises", []))
    
    # Use pre-compiled pattern to detect exception names
    
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Skip standalone "None" lines
        if stripped == "None":
            i += 1
            continue
        
        # Skip hallucinated exception lines (exception name without proper Raises header)
        # Dynamically detect if a line looks like an exception name but isn't in actual raises
        if _EXCEPTION_PATTERN.match(stripped) and stripped not in actual_raises:
            # Check if this looks like a hallucinated raises entry
            # (appears after an Attributes section or at odd places)
            # Skip this line and any following indented description
            i += 1
            while i < len(lines) and (lines[i].strip() == "" or lines[i].startswith("    ")):
                if lines[i].strip() == "":
                    break  # Stop at blank line
                i += 1
            continue
        
        # Skip empty Attributes section (header followed by dashes then "None" or empty)
        if stripped == "Attributes":
            # Look ahead for NumPy style
            if i + 1 < len(lines) and lines[i + 1].strip() and all(c == '-' for c in lines[i + 1].strip()):
                # Check if next content is just "None" or empty
                j = i + 2
                while j < len(lines) and lines[j].strip() == "":
                    j += 1
                if j >= len(lines) or lines[j].strip() == "None" or not lines[j].startswith("    "):
                    # Skip the entire empty Attributes section
                    i = j + 1 if j < len(lines) and lines[j].strip() == "None" else j
                    continue
        
        cleaned_lines.append(line)
        i += 1
    
    result = '\n'.join(cleaned_lines)
    result = _MULTIPLE_NEWLINES_PATTERN.sub('\n\n', result)  # Clean up again
    
    # Final cleanup: Remove trailing Note sections (often disclaimers)
    lines = result.split('\n')
    final_lines = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Check for Note: or Note followed by explanation (common pattern for AI disclaimers)
        if stripped.startswith("Note:") or stripped.startswith("Note "):
            # Skip this and all remaining lines (it's usually at the end)
            break
        final_lines.append(line)
    
    result = '\n'.join(final_lines)
    result = _MULTIPLE_NEWLINES_PATTERN.sub('\n\n', result)
    
    # Fix D401 imperative mood violations
    result = _fix_imperative_mood(result)
    
    # Fix D400 (period), D403 (capitalize), D404 (no "This")
    result = _fix_pep257_first_line(result)
    
    return result.strip()


def _generate_with_groq(func_meta: Dict, style: str, skip_cache: bool = False, retry_count: int = 0) -> str:
    """Generate a docstring using Groq API with caching.
    
    Args:
        func_meta: Function metadata dictionary.
        style: Docstring style.
        skip_cache: If True, skip cache and generate fresh.
        retry_count: Internal counter for retry attempts on empty responses.
    """
    global _docstring_cache
    
    MAX_RETRIES = 2  # Maximum number of retry attempts for empty responses
    
    # Check cache first (unless skip_cache is True for regeneration)
    cache_key = _create_cache_key(func_meta, style)
    if not skip_cache and cache_key in _docstring_cache:
        return _docstring_cache[cache_key]
    
    try:
        client = _get_groq_client()
        # Use a random variation seed when regenerating or retrying to get different output
        variation_seed = random.randint(1, 100) if (skip_cache or retry_count > 0) else 0
        prompt = _build_groq_prompt(func_meta, style, variation_seed=variation_seed)
        message = HumanMessage(content=prompt)
        response = client.invoke([message])
        
        # Extract the content from the response
        content = response.content.strip()
        
        # Remove any accidental triple quotes if present
        if content.startswith('"""') and content.endswith('"""'):
            content = content[3:-3].strip()
        elif content.startswith("'''") and content.endswith("'''"):
            content = content[3:-3].strip()
        
        # Remove common AI preambles (case-insensitive comparison)
        preamble_patterns = [
            "Here's the generated docstring for the given function:",
            "Here's the generated docstring:",
            "Here's the docstring:",
            "Here is the generated docstring for the given function:",
            "Here is the generated docstring:",
            "Here is the docstring:",
            "Here's a docstring for the function:",
            "Here is a docstring for the function:",
            "Generated docstring:",
            "Short description of the function.",
        ]
        content_lower = content.lower()
        for preamble in preamble_patterns:
            if content_lower.startswith(preamble.lower()):
                content = content[len(preamble):].strip()
                break
        
        # Remove code blocks (```python ... ```) - AI sometimes includes these
        # Remove everything from ``` onwards (code blocks are garbage)
        if '```' in content:
            content = content.split('```')[0].strip()
        
        # Remove any trailing triple quotes that slipped through
        if '"""' in content:
            content = content.split('"""')[0].strip()
        if "'''" in content:
            content = content.split("'''")[0].strip()
        
        # Post-process to remove hallucinated sections
        content = _post_process_docstring(content, func_meta, style)
        
        # Check if the result is empty - retry with different variation or fall back to template
        if not content or not content.strip():
            if retry_count < MAX_RETRIES:
                print(f"Groq returned empty docstring. Retrying ({retry_count + 1}/{MAX_RETRIES})...")
                return _generate_with_groq(func_meta, style, skip_cache=True, retry_count=retry_count + 1)
            else:
                print("Groq returned empty docstring after all retries. Falling back to template generation.")
                return _fallback_generate(func_meta, style)
        
        # Store in cache
        _docstring_cache[cache_key] = content
        
        return content
    except Exception as e:
        # Log error and fall back to template-based generation
        print(f"Groq API error: {e}. Falling back to template generation.")
        return _fallback_generate(func_meta, style)


# ============================================================================
# FALLBACK TEMPLATE-BASED GENERATION (used when Groq API fails)
# ============================================================================

def _infer_type(annotation: Optional[str]) -> str:
    return annotation if annotation else "Any"


def _infer_param_desc(name: str) -> str:
    return f"{name} value."


def _infer_return_desc(func_name: str) -> str:
    return f"Result of {func_name}."


def _infer_attr_desc(name: str) -> str:
    return f"{name} attribute."


def _humanize_name(name: str) -> str:
    """Return a human-friendly, capitalized version of a function or attribute name."""
    if not name:
        return ""
    human = name.replace("_", " ")
    return human[:1].upper() + human[1:]


def _build_google_body(func_meta: Dict) -> str:
    name = func_meta.get("name", "<function>")
    args_meta = func_meta.get("args_meta", [])
    has_return = func_meta.get("has_return", False)
    returns = func_meta.get("returns")
    raises = func_meta.get("raises", [])
    has_yields = func_meta.get("has_yields", False)
    yields = func_meta.get("yields")
    attributes = func_meta.get("attributes", [])

    parts: List[str] = [f"Short description of `{name}`."]

    if args_meta:
        arg_lines = ["Args:"]
        for arg in args_meta:
            arg_lines.append(
                f"    {arg['name']} ({_infer_type(arg.get('annotation'))}): "
                f"{_infer_param_desc(arg['name'])}"
            )
        parts.append("\n".join(arg_lines))

    if has_return:
        parts.append(
            f"Returns:\n    {_infer_type(returns)}: {_infer_return_desc(name)}"
        )

    if has_yields:
        parts.append(
            f"Yields:\n    {_infer_type(yields)}: Yielded values."
        )

    if attributes:
        attr_lines = ["Attributes:"]
        for attr in attributes:
            attr_lines.append(
                f"    {attr} ({_infer_type(None)}): {_infer_attr_desc(attr)}"
            )
        parts.append("\n".join(attr_lines))

    if raises:
        raise_lines = ["Raises:"]
        for r in raises:
            raise_lines.append(f"    {r}: If an error occurs.")
        parts.append("\n".join(raise_lines))

    return "\n\n".join(parts)


def _build_numpy_body(func_meta: Dict) -> str:
    name = func_meta.get("name", "<function>")
    args_meta = func_meta.get("args_meta", [])
    has_return = func_meta.get("has_return", False)
    returns = func_meta.get("returns")
    raises = func_meta.get("raises", [])
    has_yields = func_meta.get("has_yields", False)
    yields = func_meta.get("yields")
    attributes = func_meta.get("attributes", [])

    parts: List[str] = [f"{_humanize_name(name)} summary."]

    if args_meta:
        parts.append("\nParameters\n----------")
        for arg in args_meta:
            parts.append(f"{arg['name']} : {_infer_type(arg.get('annotation'))}")
            parts.append(f"    {_infer_param_desc(arg['name'])}")

    if has_return:
        parts.append("\nReturns\n-------")
        parts.append(f"{_infer_type(returns)}")
        parts.append(f"    {_infer_return_desc(name)}")

    if has_yields:
        parts.append("\nYields\n------")
        parts.append(f"{_infer_type(yields)}")
        parts.append("    Yielded values.")

    if attributes:
        parts.append("\nAttributes\n----------")
        for attr in attributes:
            parts.append(f"{attr} : {_infer_type(None)}")
            parts.append(f"    {_infer_attr_desc(attr)}")

    if raises:
        parts.append("\nRaises\n------")
        for r in raises:
            parts.append(f"{r}")
            parts.append("    If an error occurs.")

    return "\n".join(parts)


def _build_rest_body(func_meta: Dict) -> str:
    name = func_meta.get("name", "<function>")
    args_meta = func_meta.get("args_meta", [])
    has_return = func_meta.get("has_return", False)
    returns = func_meta.get("returns")
    raises = func_meta.get("raises", [])
    has_yields = func_meta.get("has_yields", False)
    yields = func_meta.get("yields")
    attributes = func_meta.get("attributes", [])

    parts: List[str] = [f"{_humanize_name(name)} description.", ""]

    for arg in args_meta:
        parts.append(
            f":param {arg['name']}: {_infer_param_desc(arg['name'])}"
        )
        parts.append(
            f":type {arg['name']}: {_infer_type(arg.get('annotation'))}"
        )

    if has_return:
        parts.append(f":returns: {_infer_return_desc(name)}")
        parts.append(f":rtype: {_infer_type(returns)}")

    if has_yields:
        parts.append(":yields: Yielded values.")
        parts.append(f":ytype: {_infer_type(yields)}")

    for attr in attributes:
        parts.append(
            f":attribute {attr}: {_infer_attr_desc(attr)}"
        )

    for r in raises:
        parts.append(f":raises {r}: If an error occurs.")

    return "\n".join(parts)


def _fallback_generate(func_meta: Dict, style: str) -> str:
    """Fallback generation using a simpler Groq prompt when primary fails."""
    # Try a simpler, more direct Groq prompt
    try:
        client = _get_groq_client()
        name = func_meta.get("name", "function")
        source_code = func_meta.get("source_code", "")
        
        # Build a very simple prompt
        if source_code:
            simple_prompt = f"""Write a brief docstring for this Python function. Return ONLY the docstring text, no quotes.

```python
{source_code}
```

Style: {style}
Just write a one-line summary describing what this function does."""
        else:
            args_meta = func_meta.get("args_meta", [])
            args_list = ", ".join(arg.get("name", "") for arg in args_meta)
            simple_prompt = f"""Write a brief docstring for a function called '{name}' with parameters: {args_list or 'none'}

Style: {style}
Just write a one-line summary describing what this function likely does based on its name."""
        
        message = HumanMessage(content=simple_prompt)
        response = client.invoke([message])
        content = response.content.strip()
        
        # Clean up the response
        if content.startswith('"""') and content.endswith('"""'):
            content = content[3:-3].strip()
        elif content.startswith("'''") and content.endswith("'''"):
            content = content[3:-3].strip()
        if '```' in content:
            content = content.split('```')[0].strip()
        if '"""' in content:
            content = content.split('"""')[0].strip()
        
        if content and content.strip():
            return content
    except Exception as e:
        print(f"Fallback Groq call failed: {e}")
    
    # Last resort: template-based generation
    if style == "google":
        return _build_google_body(func_meta)
    if style == "numpy":
        return _build_numpy_body(func_meta)
    if style in ("rest", "restructuredtext"):
        return _build_rest_body(func_meta)
    return _build_google_body(func_meta)


# ============================================================================
# PUBLIC API
# ============================================================================

def generate_docstring(func_meta: Dict, style: str = "google", skip_cache: bool = False) -> str:
    """
    Generate a docstring using Groq AI.
    
    Args:
        func_meta: Function metadata dictionary.
        style: Docstring style ('google', 'numpy', 'rest', or 'none').
        skip_cache: If True, skip cache and generate a fresh docstring.
    
    Returns the docstring BODY only (no triple quotes).
    Falls back to template-based generation if Groq API fails.
    """
    if style == "none":
        return ""
    
    # Use Groq for generation
    return _generate_with_groq(func_meta, style, skip_cache=skip_cache)


def generate_module_docstring(file_path: str, file_content: str = "") -> str:
    """Generate a module-level docstring using Groq AI.
    
    Args:
        file_path: Path to the Python file.
        file_content: Optional file content. If not provided, reads from file_path.
    
    Returns:
        Module docstring body (without triple quotes).
    """
    import os
    
    if not file_content:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                file_content = f.read()
        except Exception:
            return ""
    
    # Extract useful info about the module
    file_name = os.path.basename(file_path)
    module_name = os.path.splitext(file_name)[0]
    
    # Get first ~50 lines for context (to understand what the module does)
    lines = file_content.split('\n')[:50]
    preview = '\n'.join(lines)
    
    try:
        client = _get_groq_client()
        
        prompt = f"""Generate a brief module-level docstring for this Python file.

File name: {file_name}
Module name: {module_name}

File content preview:
```python
{preview}
```

RULES:
- Write a concise one-line description of what this module does
- Use imperative mood (e.g., "Provide utilities for..." not "Provides utilities for...")
- First word must be capitalized
- First line MUST end with a period
- Do NOT start with "This module" or "This file"
- Do NOT include author info, dates, or copyright
- Return ONLY the docstring text, no triple quotes
- Keep it to 1-2 sentences maximum

Example good docstrings:
- "Provide core validation utilities for Python docstrings."
- "Define the main application entry point and UI components."
- "Implement database connection and query utilities."
"""
        
        message = HumanMessage(content=prompt)
        response = client.invoke([message])
        content = response.content.strip()
        
        # Clean up response
        if content.startswith('"""') and content.endswith('"""'):
            content = content[3:-3].strip()
        elif content.startswith("'''") and content.endswith("'''"):
            content = content[3:-3].strip()
        
        # Remove preambles
        if content.lower().startswith("here"):
            lines = content.split('\n', 1)
            if len(lines) > 1:
                content = lines[1].strip()
        
        # Apply PEP 257 fixes
        content = _fix_imperative_mood(content)
        content = _fix_pep257_first_line(content)
        
        return content.strip()
        
    except Exception as e:
        print(f"Module docstring generation error: {e}")
        # Fallback to simple template
        humanized = module_name.replace("_", " ").title()
        return f"{humanized} module."


def insert_module_docstring(file_path: str, docstring_body: str) -> bool:
    """Insert a module-level docstring at the beginning of a Python file.
    
    Args:
        file_path: Path to the Python file.
        docstring_body: The docstring content (without triple quotes).
    
    Returns:
        True if successful, False otherwise.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return False
    
    lines = content.split('\n')
    
    # D301: Use raw string if docstring contains backslashes
    quote_prefix = 'r' if '\\' in docstring_body else ''
    
    # Check if module already has a docstring
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue  # Skip empty lines and comments
        if stripped.startswith('"""') or stripped.startswith("'''") or stripped.startswith('r"""') or stripped.startswith("r'''"):
            # Already has a module docstring, replace it
            # Find the end of the docstring
            quote_type = '"""' if '"""' in stripped else "'''"
            if stripped.count(quote_type) >= 2 and len(stripped) > 6:
                # Single-line docstring
                lines[i] = f'{quote_prefix}"""{docstring_body}"""'
            else:
                # Multi-line docstring - find end
                end_idx = i + 1
                while end_idx < len(lines):
                    if quote_type in lines[end_idx]:
                        break
                    end_idx += 1
                # Replace the entire docstring
                lines = lines[:i] + [f'{quote_prefix}"""{docstring_body}"""'] + lines[end_idx + 1:]
            
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write('\n'.join(lines))
                return True
            except Exception:
                return False
        else:
            # No docstring exists, insert at this position
            new_docstring = f'{quote_prefix}"""{docstring_body}"""'
            lines.insert(i, new_docstring)
            
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write('\n'.join(lines))
                return True
            except Exception:
                return False
    
    # File is empty or only comments - add at the beginning
    new_content = f'{quote_prefix}"""{docstring_body}"""\n' + content
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True
    except Exception:
        return False
