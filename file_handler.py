"""
file_handler.py  --  PART 1 of 2 : LOUIS (back end, file side)

Responsibilities
    * Read and validate the productions file (.prod)
    * Read and validate the parse table file (.ptbl)
    * Check that the two files share the same base name
    * Build the output file name and write the solution (.prsd) as CSV

This module knows nothing about the GUI and nothing about the parsing
algorithm.  It only turns files into Python data (and data into files).
"""

import csv
import os
import re
from collections import namedtuple

EPSILON = "e"        # the empty symbol used in the .prod file
END_MARKER = "$"     # input right end marker

# One production.  rhs is a list of symbols, e.g. ["T", "E'"] or ["e"].
Production = namedtuple("Production", ["number", "lhs", "rhs"])


class FileFormatError(Exception):
    """Raised when a .prod / .ptbl file cannot be read or is malformed."""


class ParseTable:
    """Parse table: terminals (columns), non-terminals (rows), cell values."""

    def __init__(self, terminals, nonterminals, cells):
        self.terminals = terminals            # list, includes "$"
        self.nonterminals = nonterminals      # list, in file order
        self.cells = cells                    # {(nonterminal, terminal): int}

    def lookup(self, nonterminal, terminal):
        """Return the production number in the cell, or None if blank."""
        return self.cells.get((nonterminal, terminal))


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------
def normalize_text(text):
    """Strip spaces and turn curly apostrophes (E’) into plain ones (E')."""
    return (text.replace("\u2019", "'")
                .replace("\u2018", "'")
                .replace("\u2032", "'")
                .strip())


def _read_rows(path):
    """Read a CSV file; return [(line_number, row), ...] without blank rows."""
    try:
        with open(path, newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.reader(handle))
    except (OSError, UnicodeDecodeError, csv.Error) as err:
        raise FileFormatError(
            "Cannot read '%s': %s" % (os.path.basename(path), err))
    return [(i, row) for i, row in enumerate(rows, start=1)
            if any(cell.strip() for cell in row)]


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------
def load_productions(path):
    """Read a .prod file -> list of Production sorted by production number."""
    rows = _read_rows(path)
    if not rows:
        raise FileFormatError("The productions file is empty.")

    productions, seen = [], set()
    for line_no, row in rows:
        if len(row) < 3:
            raise FileFormatError(
                "Line %d: expected 3 columns (number, non-terminal, "
                "production)." % line_no)
        try:
            number = int(row[0].strip())
        except ValueError:
            raise FileFormatError(
                "Line %d: '%s' is not a valid production number."
                % (line_no, row[0].strip()))
        if number in seen:
            raise FileFormatError(
                "Line %d: production number %d is repeated." % (line_no, number))
        seen.add(number)

        lhs = normalize_text(row[1])
        if not lhs or " " in lhs:
            raise FileFormatError(
                "Line %d: the non-terminal column must contain exactly one "
                "symbol." % line_no)

        cells = row[2:]
        while cells and not cells[-1].strip():   # drop trailing empty cells
            cells.pop()
        rhs = normalize_text(",".join(cells)).split()
        if not rhs:
            raise FileFormatError(
                "Line %d: empty production (use 'e' for the empty symbol)."
                % line_no)
        productions.append(Production(number, lhs, rhs))

    productions.sort(key=lambda p: p.number)
    return productions


def load_parse_table(path):
    """Read a .ptbl file -> ParseTable."""
    rows = _read_rows(path)
    if len(rows) < 2:
        raise FileFormatError(
            "The parse table needs a header row and at least one "
            "non-terminal row.")

    _, header = rows[0]
    terminals = [normalize_text(c) for c in header[1:]]
    while terminals and terminals[-1] == "":
        terminals.pop()
    if not terminals:
        raise FileFormatError("The parse table header has no terminal labels.")
    if "" in terminals:
        raise FileFormatError("The parse table header has a blank column label.")
    if len(set(terminals)) != len(terminals):
        raise FileFormatError("The parse table header has a repeated terminal.")
    if END_MARKER not in terminals:
        raise FileFormatError(
            "The parse table header must include the end marker '$'.")

    nonterminals, cells = [], {}
    for line_no, row in rows[1:]:
        nt = normalize_text(row[0])
        if not nt:
            raise FileFormatError("Line %d: missing non-terminal name." % line_no)
        if nt in nonterminals:
            raise FileFormatError(
                "Line %d: non-terminal '%s' appears twice." % (line_no, nt))
        nonterminals.append(nt)

        for col, cell in enumerate(row[1:]):
            cell = cell.strip()
            if not cell:
                continue                      # blank cell = no rule
            if col >= len(terminals):
                raise FileFormatError(
                    "Line %d: entry '%s' is beyond the last column label."
                    % (line_no, cell))
            try:
                cells[(nt, terminals[col])] = int(cell)
            except ValueError:
                raise FileFormatError(
                    "Line %d: '%s' is not a production number." % (line_no, cell))
    return ParseTable(terminals, nonterminals, cells)


# --------------------------------------------------------------------------
# file names and output
# --------------------------------------------------------------------------
def base_name(path):
    """File name without folder and extension ('C:/x/rules.prod' -> 'rules')."""
    return os.path.splitext(os.path.basename(path))[0]


def names_match(path_a, path_b):
    """True if both files have the same base name (case-insensitive)."""
    return base_name(path_a).lower() == base_name(path_b).lower()


def sanitize_output_name(name):
    """Clean the user's output name: no .prsd, no illegal file characters."""
    name = name.strip()
    if name.lower().endswith(".prsd"):
        name = name[:-5]
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip()


def build_output_path(outname, prod_path):
    """outname_prodname.prsd, saved in the same folder as the input file."""
    file_name = "%s_%s.prsd" % (sanitize_output_name(outname), base_name(prod_path))
    return os.path.join(os.path.dirname(os.path.abspath(prod_path)), file_name)


def write_solution(path, steps):
    """Write the parsing steps as CSV: stack, input buffer, action."""
    try:
        with open(path, "w", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerows(steps)
    except OSError as err:
        raise FileFormatError("Cannot write '%s': %s" % (os.path.basename(path), err))
