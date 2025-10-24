"""AST utilities for modifying service.py."""

import ast
import re
from pathlib import Path


class ServiceModificationError(Exception):
    """Raised when service.py modification fails."""


def parse_service_file(service_path: Path) -> ast.Module:
    """Parse service.py into an AST.

    Args:
        service_path: Path to service.py file

    Returns:
        Parsed AST module

    Raises:
        ServiceModificationError: If file cannot be parsed
    """
    try:
        with open(service_path, encoding="utf-8") as f:
            source = f.read()
        return ast.parse(source)
    except Exception as e:
        raise ServiceModificationError(f"Failed to parse service.py: {e}") from e


def find_import_section_end(tree: ast.Module) -> int:
    """Find the line number where imports end.

    Looks for the last import statement and returns its line number.

    Args:
        tree: AST module

    Returns:
        Line number after last import (0-indexed in AST terms)
    """
    last_import_line = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if hasattr(node, "lineno"):
                last_import_line = max(last_import_line, node.lineno)
    return last_import_line


def has_import(tree: ast.Module, module: str, names: list[str]) -> bool:
    """Check if specific import already exists.

    Args:
        tree: AST module
        module: Module name (e.g., 'myapp.agents.researcher')
        names: Names to import (e.g., ['ResearcherAgent'])

    Returns:
        True if import exists
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == module:
                imported_names = {alias.name for alias in node.names}
                if all(name in imported_names for name in names):
                    return True
    return False


def add_import(source: str, module: str, names: list[str], comment: str | None = None) -> str:
    """Add an import statement to service.py source.

    Finds the appropriate location (after existing imports from same package)
    and inserts the new import.

    Args:
        source: Current source code
        module: Module to import from (e.g., 'myapp.agents.researcher')
        names: Names to import (e.g., ['ResearcherAgent'])
        comment: Optional comment line to add before import block

    Returns:
        Modified source code
    """
    tree = ast.parse(source)

    # Check if import already exists
    if has_import(tree, module, names):
        return source

    lines = source.split("\n")

    # Find the package prefix (e.g., 'myapp')
    package_prefix = module.split(".")[0]
    resource_type = module.split(".")[1] if len(module.split(".")) > 1 else None

    # Find where to insert based on resource type
    insert_line = None
    last_matching_import = None

    for i, line in enumerate(lines):
        # Look for import section comments
        if resource_type == "agents" and "# Agents" in line:
            insert_line = i + 1
            # Skip to end of agents section
            j = i + 1
            while j < len(lines) and (lines[j].strip().startswith("from") or not lines[j].strip()):
                if lines[j].strip().startswith("from"):
                    last_matching_import = j
                j += 1
            if last_matching_import:
                insert_line = last_matching_import + 1
            break
        elif resource_type == "workflows" and "# Workflows" in line:
            insert_line = i + 1
            j = i + 1
            while j < len(lines) and (lines[j].strip().startswith("from") or not lines[j].strip()):
                if lines[j].strip().startswith("from"):
                    last_matching_import = j
                j += 1
            if last_matching_import:
                insert_line = last_matching_import + 1
            break
        elif resource_type == "functions" and "# Functions" in line:
            insert_line = i + 1
            j = i + 1
            while j < len(lines) and (lines[j].strip().startswith("from") or not lines[j].strip()):
                if lines[j].strip().startswith("from"):
                    last_matching_import = j
                j += 1
            if last_matching_import:
                insert_line = last_matching_import + 1
            break

    # If no matching section found, insert after settings import
    if insert_line is None:
        for i, line in enumerate(lines):
            if f"from {package_prefix}.common.settings import settings" in line:
                insert_line = i + 1
                # Add the section comment
                if resource_type == "agents":
                    lines.insert(insert_line, "\n# Agents")
                    insert_line += 2
                elif resource_type == "workflows":
                    lines.insert(insert_line, "\n# Workflows")
                    insert_line += 2
                elif resource_type == "functions":
                    lines.insert(insert_line, "\n# Functions")
                    insert_line += 2
                break

    # Insert the import
    if insert_line is not None:
        import_line = f"from {module} import {', '.join(names)}"
        lines.insert(insert_line, import_line)

    return "\n".join(lines)


def find_list_argument(call_node: ast.Call, arg_name: str) -> ast.List | None:
    """Find a list argument in a function call.

    Args:
        call_node: AST Call node
        arg_name: Name of the keyword argument

    Returns:
        AST List node if found
    """
    for keyword in call_node.keywords:
        if keyword.arg == arg_name and isinstance(keyword.value, ast.List):
            return keyword.value
    return None


def add_to_list_in_source(source: str, list_name: str, item: str) -> str:
    """Add an item to a list argument in start_service call.

    Args:
        source: Current source code
        list_name: Name of list argument ('workflows' or 'functions')
        item: Item to add (e.g., 'ResearcherAgent')

    Returns:
        Modified source code
    """
    tree = ast.parse(source)

    # Find the start_service call
    start_service_call = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == "start_service":
                    start_service_call = node
                    break

    if not start_service_call:
        raise ServiceModificationError("Could not find start_service call")

    # Find the list argument
    list_arg = find_list_argument(start_service_call, list_name)
    if list_arg is None:
        raise ServiceModificationError(f"Could not find {list_name}= argument")

    # Check if item already exists
    for elem in list_arg.elts:
        if isinstance(elem, ast.Name) and elem.id == item:
            return source  # Already exists

    # Find the list in source and add item
    lines = source.split("\n")

    # Find the list by looking for "list_name=["
    list_start_line = None
    in_start_service = False
    for i, line in enumerate(lines):
        if "start_service(" in line:
            in_start_service = True
        if in_start_service and f"{list_name}=" in line:
            list_start_line = i
            break

    if list_start_line is None:
        raise ServiceModificationError(f"Could not find {list_name}= in source")

    # Find the closing bracket of this list
    bracket_count = 0
    found_opening = False
    list_end_line = None

    for i in range(list_start_line, len(lines)):
        line = lines[i]
        for char in line:
            if char == "[":
                bracket_count += 1
                found_opening = True
            elif char == "]":
                bracket_count -= 1
                if found_opening and bracket_count == 0:
                    list_end_line = i
                    break
        if list_end_line is not None:
            break

    if list_end_line is None:
        raise ServiceModificationError(f"Could not find closing bracket for {list_name}")

    # Check if it's a single-line list (opening and closing on same line)
    if list_start_line == list_end_line:
        # Single-line list like "workflows=[        ]," - need to expand to multi-line
        line = lines[list_start_line]
        indent_match = re.match(r"^(\s*)", line)
        base_indent = indent_match.group(1) if indent_match else ""
        item_indent = base_indent + "    "

        # Replace the single line with multi-line format
        list_name_part = line[: line.index("[")]
        lines[list_start_line] = f"{list_name_part}["
        lines.insert(list_start_line + 1, f"{item_indent}{item},")
        lines.insert(list_start_line + 2, f"{base_indent}],")
    else:
        # Multi-line list - determine indentation from existing items or default
        item_indent = None
        for i in range(list_start_line + 1, list_end_line):
            line = lines[i]
            if line.strip() and not line.strip().startswith("#"):
                # Found an existing item, use its indentation
                indent_match = re.match(r"^(\s*)", line)
                if indent_match:
                    item_indent = indent_match.group(1)
                break

        # If no existing items, determine indent from the opening bracket line
        if item_indent is None:
            indent_match = re.match(r"^(\s*)", lines[list_start_line])
            base_indent = indent_match.group(1) if indent_match else ""
            item_indent = base_indent + "    "

        # Insert before closing bracket
        lines.insert(list_end_line, f"{item_indent}{item},")

    return "\n".join(lines)


def write_service_file(source: str, service_path: Path) -> None:
    """Write modified source back to service.py.

    Args:
        source: Modified source code
        service_path: Path to service.py file

    Raises:
        ServiceModificationError: If file cannot be written
    """
    try:
        with open(service_path, "w", encoding="utf-8") as f:
            f.write(source)
    except Exception as e:
        raise ServiceModificationError(f"Failed to write service.py: {e}") from e


def update_service_file(
    service_path: Path,
    resource_type: str,
    module_name: str,
    import_name: str,
    module_prefix: str | None = None,
) -> None:
    """Update service.py with new resource.

    Adds import and registers resource in appropriate list.

    Args:
        service_path: Path to service.py file
        resource_type: Type of resource ('agent', 'workflow', or 'function')
        module_name: Module name (e.g., 'researcher' for agents/researcher.py)
        import_name: Name to import and register (e.g., 'ResearcherAgent' or 'research')
        module_prefix: Optional module prefix override for import path

    Raises:
        ServiceModificationError: If modification fails
        ValueError: If resource_type is invalid
    """
    if resource_type not in ["agent", "workflow", "function"]:
        raise ValueError(f"Invalid resource_type: {resource_type}")

    # Read current source
    with open(service_path, encoding="utf-8") as f:
        source = f.read()

    # Extract project name from first import
    tree = ast.parse(source)
    project_name = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if ".common.settings" in node.module:
                project_name = node.module.split(".")[0]
                break

    if not project_name:
        raise ServiceModificationError("Could not determine project name from imports")

    # Build import module path
    if resource_type == "agent":
        default_prefix = f"{project_name}.agents"
        list_name = "workflows"  # Agents are registered as workflows
    elif resource_type == "workflow":
        default_prefix = f"{project_name}.workflows"
        list_name = "workflows"
    else:  # function
        default_prefix = f"{project_name}.functions"
        list_name = "functions"

    import_prefix = module_prefix if module_prefix is not None else default_prefix
    import_module = f"{import_prefix}.{module_name}"

    # Add import
    source = add_import(source, import_module, [import_name])

    # Add to list
    source = add_to_list_in_source(source, list_name, import_name)

    # Write back
    write_service_file(source, service_path)
