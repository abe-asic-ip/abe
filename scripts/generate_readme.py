#!/usr/bin/env python3
"""
SPDX-FileCopyrightText: 2025 Hugh Walsh

SPDX-License-Identifier: MIT

Generate README.md from docs/index.md by:
1. Adding the "Read the full documentation" link
2. Prefixing all relative .md links with "docs/"
"""

import re
from pathlib import Path


def generate_readme() -> None:
    """Generate README.md from docs/index.md."""
    # Read the source file
    index_path = Path(__file__).parent.parent / "docs" / "index.md"
    readme_path = Path(__file__).parent.parent / "README.md"

    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find the insertion point (after "The goal is simple..." paragraph)
    # Look for the pattern: line with "professional engineers" followed by blank line
    insertion_pattern = (
        r"(for professional engineers, students, researchers, and enthusiasts\.)\n"
    )
    docs_link = (
        "\n\n📚 **[Read the full documentation](https://abe-asic-ip.github.io/abe/)**\n"
    )

    content = re.sub(insertion_pattern, r"\1" + docs_link, content, count=1)

    # Replace relative .md links with docs/ prefix
    # Match markdown links like [text](filename.md) or [text](filename.md#anchor)
    # but not absolute URLs (http/https) or already prefixed with docs/
    def replace_md_link(match: re.Match[str]) -> str:
        full_match = match.group(0)
        link_text = match.group(1)
        link_target = match.group(2)

        # Don't modify if it's already a docs/ link or an absolute URL
        if link_target.startswith("docs/") or link_target.startswith("http"):
            return full_match

        # Don't modify if it's just an anchor (starts with #)
        if link_target.startswith("#"):
            return full_match

        # Add docs/ prefix to .md files
        if ".md" in link_target:
            return f"[{link_text}](docs/{link_target})"

        return full_match

    # Pattern to match markdown links: [text](target)
    content = re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", replace_md_link, content)

    # Write the output
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated {readme_path} from {index_path}")


if __name__ == "__main__":
    generate_readme()
