# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/tools/dv_make_bench.py

"""Generate a DV testbench scaffold from template.

This module provides functionality to create new design verification testbenches
by instantiating templates with proper naming conventions and project structure.

The generator:
- Creates a complete testbench directory structure
- Applies consistent naming conventions (snake_case, PascalCase, UPPER_CASE)
- Inserts copyright headers with author and year
- Removes template-specific pylint directives
- Runs static analysis on generated files

Usage:
    dv-make-bench <module_name> <author> [--year YEAR] [--force]

Example:
    dv-make-bench rad_my_module "John Doe" --year 2025

This will create: src/abe/rad/rad_my_module/dv/
"""

from __future__ import annotations

import argparse
import subprocess
from datetime import datetime
from pathlib import Path

from abe.utils import to_pascal_case, to_snake_case


def make_bench(  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
    module_name: str,
    target_dir: Path,
    author: str = "Full Name",
    year: int | None = None,
    force: bool = False,
) -> None:
    """Generate DV testbench from template.

    Copies the template directory and performs text substitutions to customize
    the bench for the specified module. Substitutions are applied in a specific
    order to ensure correctness (longer strings before shorter ones).

    The substitution process converts:
    - Module names: rad_template -> rad_<module>
    - Author information and copyright year
    - Class names: Template -> <Module>
    - Variable/function names: template -> <module>
    - Constants: RAD_TEMPLATE -> RAD_<MODULE>

    Args:
        module_name: Name of the module (e.g., 'rad_async_fifo' or 'RadAsyncFifo').
            Will be converted to appropriate case as needed.
        target_dir: Target directory for the bench
            (e.g., 'src/abe/rad/rad_async_fifo/dv').
        author: Author name for copyright headers (default: 'Full Name').
        year: Year for copyright headers. If None, uses current year.
        force: If True, overwrite existing directory; if False, fail if exists.

    Raises:
        FileNotFoundError: If template directory cannot be found.
        FileExistsError: If target directory exists and force is False.
    """
    if year is None:
        year = datetime.now().year

    # Get template directory
    script_dir = Path(__file__).parent
    template_dir = script_dir.parent / "rad_template" / "dv"

    if not template_dir.exists():
        raise FileNotFoundError(f"Template directory not found: {template_dir}")

    # Check if target directory exists
    target_dir = Path(target_dir)
    if target_dir.exists() and any(target_dir.iterdir()):
        if not force:
            raise FileExistsError(
                f"Target directory already exists and is not empty: {target_dir}\n"
                f"Use --force to overwrite"
            )
        print(f"Warning: Overwriting existing directory: {target_dir}")

    # Create target directory
    target_dir.mkdir(parents=True, exist_ok=True)

    # Generate substitution mappings
    snake_name = to_snake_case(module_name)
    pascal_name = to_pascal_case(module_name)
    upper_name = snake_name.upper()

    # Define substitutions - order matters for correct replacement
    # Use a list of tuples to ensure we process in the right order
    substitutions = [
        ("rad_template", snake_name),  # Full module path
        ("Author Name", author),  # Author name
        ("author-name", author.lower().replace(" ", "")),  # LinkedIn URL slug
        ("Year", str(year)),  # Copyright year
        ("RAD_TEMPLATE", upper_name),  # Uppercase constant names
        ("Template", pascal_name),  # Class names
        ("template", snake_name),  # Variable names, functions
    ]

    print(f"Creating bench for module: {module_name}")
    print(f"  Snake case: {snake_name}")
    print(f"  Pascal case: {pascal_name}")
    print(f"  Target: {target_dir}")
    print()

    # Process each template file
    for template_file in template_dir.iterdir():
        if template_file.is_file():
            # Generate output filename
            output_name = template_file.name
            for old, new in substitutions:
                output_name = output_name.replace(old, new)

            output_file = target_dir / output_name

            # Read template content
            content = template_file.read_text()

            # Apply substitutions in order
            for old, new in substitutions:
                content = content.replace(old, new)

            # Remove pylint disable lines (keep errors visible in generated files)
            lines = content.splitlines(keepends=True)
            lines = [
                line
                for line in lines
                if "# pylint: disable=fixme" not in line
                and "# pylint: disable=duplicate-code" not in line
            ]
            content = "".join(lines)

            # Write output file
            output_file.write_text(content)
            print(f"  Created: {output_file.name}")

    print(f"\nBench created successfully in {target_dir}")

    # Run static analysis tools on generated files
    print("\nRunning static analysis tools...")
    py_srcs_pattern = f"{target_dir}/*.py"
    cmd = ["make", f"PY_SRCS={py_srcs_pattern}", "py-static-fix"]

    try:
        result = subprocess.run(
            cmd,
            cwd=script_dir.parent.parent.parent.parent,  # repo root
            capture_output=True,
            text=True,
            check=False,
        )

        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)

        if result.returncode == 0:
            print("✓ Static analysis passed")
        else:
            print(f"⚠ Static analysis found issues (exit code {result.returncode})")
            print("  This is intended - fix the FIXME items")
    except (FileNotFoundError, OSError) as e:
        print(f"⚠ Failed to run static analysis: {e}")
        print("  You can run it manually with:")
        print(f"  make PY_SRCS='{py_srcs_pattern}' py-static-fix")


def main() -> None:
    """Command-line interface entry point for testbench generation.

    Parses command-line arguments and invokes the make_bench function
    to generate a new testbench from the template.
    """
    parser = argparse.ArgumentParser(
        description="Generate a DV testbench from template"
    )
    parser.add_argument(
        "module_name",
        help="Module name (e.g., 'rad_async_fifo' or 'RadAsyncFifo')",
    )
    parser.add_argument(
        "author",
        help="Author name for copyright headers",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Year for copyright headers (default: current year)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing directory if it exists",
    )

    args = parser.parse_args()

    # Determine script and repo root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent.parent.parent  # Go up to repo root

    # Construct target directory: src/abe/rad/<module_name>/dv
    snake_name = to_snake_case(args.module_name)
    target_dir = repo_root / "src" / "abe" / "rad" / snake_name / "dv"

    make_bench(
        module_name=args.module_name,
        target_dir=target_dir,
        author=args.author,
        year=args.year,
        force=args.force,
    )


if __name__ == "__main__":
    main()
