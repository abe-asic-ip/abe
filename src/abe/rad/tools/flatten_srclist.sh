#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/tools/flatten_srclist.sh

# Recursively flatten a SystemVerilog filelist (srclist.f) into a list of .sv/.svh files.
#
# This script processes SystemVerilog filelist files, recursively resolving
# nested file references and outputting only the actual source files (.sv/.svh).
# It filters out compiler directives like include directories and defines.
#
# Usage: flatten_srclist.sh <filelist.f>
#
# The script handles:
# - Comments: # and // are stripped
# - Nested filelists: -f <file> or lines ending in .f
# - Include directories: +incdir+<path> or -I <path> (filtered out)
# - Defines: +define+<name> or -D <name> (filtered out)
# - Source files: .sv and .svh files (output to stdout)

set -e


# Recursively process a filelist file
# Args:
#   $1: Path to the filelist file to process
# Outputs:
#   Source file paths (one per line) to stdout
flatten() {
    local filelist="$1"
    while IFS= read -r line || [[ -n "$line" ]]; do
        # Remove comments (both # and // style)
        line="${line%%#*}"
        line="${line%%//*}"
        # Trim leading/trailing whitespace
        line="$(echo "$line" | awk '{$1=$1;print}')"
        # Skip empty lines
        [[ -z "$line" ]] && continue

        if [[ "$line" =~ ^-f[[:space:]]*(.*) ]]; then
            # Nested filelist: -f <file>
            flatten "${BASH_REMATCH[1]}"
        elif [[ "$line" =~ \.f$ ]]; then
            # Plain filelist line (ends with .f)
            flatten "$line"
        elif [[ "$line" =~ ^\+incdir\+ ]] || [[ "$line" =~ ^-I[[:space:]]* ]] || [[ "$line" =~ ^\+define\+ ]] || [[ "$line" =~ ^-D[[:space:]]* ]]; then
            # Skip compiler directives (include dirs and defines)
            continue
        elif [[ "$line" =~ \.svh?$ ]]; then
            # Output SystemVerilog source files (.sv or .svh)
            echo "$line"
        fi
    done < "$filelist"
}

# Main script entry point
if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <filelist.f>" >&2
    exit 1
fi

flatten "$1"
