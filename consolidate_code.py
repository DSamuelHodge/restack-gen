#!/usr/bin/env python3
"""
Consolidate all Python files from restack_gen into a single markdown file.
"""
import os
from pathlib import Path
from typing import List, Tuple


def collect_python_files(directory: Path) -> List[Tuple[Path, str]]:
    """
    Recursively collect all Python files from the directory.
    
    Args:
        directory: Root directory to search
        
    Returns:
        List of tuples containing (file_path, relative_path_string)
    """
    python_files = []
    
    for root, dirs, files in os.walk(directory):
        # Skip __pycache__ directories
        dirs[:] = [d for d in dirs if d != '__pycache__']
        
        for file in sorted(files):
            if file.endswith('.py'):
                file_path = Path(root) / file
                relative_path = file_path.relative_to(directory.parent)
                python_files.append((file_path, str(relative_path)))
    
    return sorted(python_files, key=lambda x: x[1])


def create_markdown_file(python_files: List[Tuple[Path, str]], output_file: Path) -> None:
    """
    Create a markdown file containing all Python source code.
    
    Args:
        python_files: List of tuples containing (file_path, relative_path)
        output_file: Path to output markdown file
    """
    with open(output_file, 'w', encoding='utf-8') as md_file:
        # Write header
        md_file.write("# Restack Generator - Source Code Documentation\n\n")
        md_file.write(f"This document contains all Python source files from the `restack_gen` package.\n\n")
        md_file.write(f"**Total files:** {len(python_files)}\n\n")
        md_file.write("---\n\n")
        
        # Write table of contents
        md_file.write("## Table of Contents\n\n")
        for idx, (_, relative_path) in enumerate(python_files, 1):
            anchor = relative_path.replace('\\', '-').replace('/', '-').replace('.', '-')
            md_file.write(f"{idx}. [{relative_path}](#{anchor})\n")
        md_file.write("\n---\n\n")
        
        # Write each file's content
        for file_path, relative_path in python_files:
            anchor = relative_path.replace('\\', '-').replace('/', '-').replace('.', '-')
            
            # Write file header
            md_file.write(f"## {relative_path}\n\n")
            md_file.write(f"<a id=\"{anchor}\"></a>\n\n")
            md_file.write(f"**File:** `{relative_path}`\n\n")
            
            # Read and write file content
            try:
                with open(file_path, 'r', encoding='utf-8') as py_file:
                    content = py_file.read()
                    
                md_file.write("```python\n")
                md_file.write(content)
                if not content.endswith('\n'):
                    md_file.write('\n')
                md_file.write("```\n\n")
                md_file.write("---\n\n")
                
            except Exception as e:
                md_file.write(f"*Error reading file: {e}*\n\n")
                md_file.write("---\n\n")


def main():
    """Main function to consolidate Python files into markdown."""
    # Define paths
    project_root = Path(__file__).parent
    restack_gen_dir = project_root / "restack_gen"
    output_file = project_root / "restack_gen_source_code.md"
    
    print(f"📁 Scanning directory: {restack_gen_dir}")
    
    # Collect Python files
    python_files = collect_python_files(restack_gen_dir)
    
    print(f"✅ Found {len(python_files)} Python files")
    
    # Create markdown file
    print(f"📝 Creating markdown file: {output_file}")
    create_markdown_file(python_files, output_file)
    
    print(f"✅ Successfully created {output_file}")
    print(f"📊 File size: {output_file.stat().st_size / 1024:.2f} KB")


if __name__ == "__main__":
    main()
