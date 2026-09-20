# SPDX-FileCopyrightText: 2026 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: src/abe/rad/tools/parse_srclist.awk

# Extract one category of items from a srclist.f, one item per line.
#
# Usage: awk -v mode=<files|incdirs|defines> -f parse_srclist.awk <srclist.f>
#
#   mode=files    everything that is not a comment, incdir or define
#                 (source files, plus any other line such as "-f <filelist>")
#   mode=incdirs  directories from "+incdir+<path>" or "-I <path>"
#   mode=defines  NAME[=VAL] from "+define+NAME[=VAL]" or "-D NAME[=VAL]"
#
# Comment lines start with "#" or "//". Blank lines and carriage returns are
# ignored. This lives in a script (not inline in mk/00-vars.mk) because GNU Make
# 3.81, which macOS ships as /usr/bin/make, cannot parse regexes containing
# parentheses inside a multi-line $(shell ...) call.

function trim(s) {
    gsub(/^[ \t]+|[ \t]+$/, "", s)
    return s
}

BEGIN {
    if (mode != "files" && mode != "incdirs" && mode != "defines") {
        print "parse_srclist.awk: set -v mode=files|incdirs|defines" > "/dev/stderr"
        exit 2
    }
}

{ gsub(/\r/, "") }

/^[ \t]*($|#|\/\/)/ { next }

/^[ \t]*\+incdir\+/ {
    if (mode == "incdirs") {
        sub(/^[ \t]*\+incdir\+/, "")
        print trim($0)
    }
    next
}

/^[ \t]*-I[ \t]*/ {
    if (mode == "incdirs") {
        sub(/^[ \t]*-I[ \t]*/, "")
        print trim($0)
    }
    next
}

/^[ \t]*\+define\+/ {
    if (mode == "defines") {
        sub(/^[ \t]*\+define\+/, "")
        print trim($0)
    }
    next
}

/^[ \t]*-D[ \t]*/ {
    if (mode == "defines") {
        sub(/^[ \t]*-D[ \t]*/, "")
        print trim($0)
    }
    next
}

{ if (mode == "files") print $0 }
