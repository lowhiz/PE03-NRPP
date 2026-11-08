"""
parser_engine.py  --  PART 1 of 2 : LOUIS (back end, parsing side)

Responsibilities
    * Split the user's input into tokens
    * Check that the productions and the parse table agree with each other
    * Run the non-recursive predictive parsing algorithm (stack + table)
    * Return every step as (stack, input buffer, action) rows

No GUI code and no file code lives here.
"""

from file_handler import EPSILON, END_MARKER

MAX_STEPS = 10000        # safety stop (e.g. a left-recursive grammar)


class ParserSetupError(Exception):
    """Raised when the productions and the parse table do not agree."""


class ParseResult:
    def __init__(self, valid, steps):
        self.valid = valid
        self.steps = steps        # list of (stack_text, input_text, action)


def tokenize_input(text):
    """Split on any whitespace and add the end marker '$' if it is missing."""
    tokens = text.replace("\u2019", "'").split()
    if not tokens or tokens[-1] != END_MARKER:
        tokens.append(END_MARKER)
    return tokens


class PredictiveParser:
    def __init__(self, productions, table):
        self.table = table
        self.by_number = {p.number: p for p in productions}
        self.nonterminals = {p.lhs for p in productions} | set(table.nonterminals)
        self.start_symbol = productions[0].lhs     # LHS of production 1
        self._check_consistency(productions)
        known = self.nonterminals | set(table.terminals)
        self.rhs = {p.number: self._resolve_rhs(p.rhs, known) for p in productions}

    # ---------------- set-up checks ----------------
    def _check_consistency(self, productions):
        for p in productions:
            if p.lhs not in self.table.nonterminals:
                raise ParserSetupError(
                    "Non-terminal '%s' has no row in the parse table." % p.lhs)
        for nt in self.table.nonterminals:
            if nt not in {p.lhs for p in productions}:
                raise ParserSetupError(
                    "Non-terminal '%s' in the parse table has no production."
                    % nt)
        for (nt, term), number in self.table.cells.items():
            if number not in self.by_number:
                raise ParserSetupError(
                    "Parse table cell (%s, %s) refers to production %d, which "
                    "does not exist." % (nt, term, number))
            if self.by_number[number].lhs != nt:
                raise ParserSetupError(
                    "Parse table cell (%s, %s) uses production %d, which "
                    "belongs to '%s'." % (nt, term, number,
                                          self.by_number[number].lhs))

    @staticmethod
    def _resolve_rhs(rhs, known):
        """Turn a right-hand side into a list of symbols.
        'e' becomes [] and glued text such as '(E)' is split into '(', 'E', ')'."""
        symbols = []
        for token in rhs:
            if token == EPSILON:
                continue
            if token in known:
                symbols.append(token)
                continue
            pieces, i, ok = [], 0, True
            ordered = sorted(known, key=len, reverse=True)
            while i < len(token) and ok:
                for s in ordered:
                    if token.startswith(s, i):
                        pieces.append(s)
                        i += len(s)
                        break
                else:
                    ok = False
            symbols.extend(pieces if ok else [token])
        return symbols

    # ---------------- the algorithm ----------------
    def parse(self, tokens):
        stack = [END_MARKER, self.start_symbol]    # top of stack = end of list
        pos = 0
        steps = []

        for _ in range(MAX_STEPS):
            top, look = stack[-1], tokens[pos]
            stack_text = " ".join(reversed(stack))
            input_text = " ".join(tokens[pos:])

            if top == END_MARKER and look == END_MARKER:
                if pos != len(tokens) - 1:
                    return self._fail(steps, stack_text, input_text,
                                      "Error: extra input after the end marker")
                steps.append(("", "", "Match $"))
                return ParseResult(True, steps)

            if top not in self.nonterminals:                  # terminal on top
                if top == look:
                    steps.append((stack_text, input_text, "Match " + top))
                    stack.pop()
                    pos += 1
                else:
                    return self._fail(
                        steps, stack_text, input_text,
                        "Error: expected '%s' but found '%s'" % (top, look))
            else:                                             # non-terminal
                if look not in self.table.terminals:
                    return self._fail(
                        steps, stack_text, input_text,
                        "Error: '%s' is not a terminal of this grammar" % look)
                number = self.table.lookup(top, look)
                if number is None:
                    return self._fail(
                        steps, stack_text, input_text,
                        "Error: no rule for %s with input '%s'" % (top, look))
                rhs = self.rhs[number]
                steps.append((stack_text, input_text, "Output %s > %s" %
                              (top, " ".join(rhs) if rhs else EPSILON)))
                stack.pop()
                stack.extend(reversed(rhs))

        return self._fail(steps, " ".join(reversed(stack)),
                          " ".join(tokens[pos:]),
                          "Error: step limit reached (is the grammar left-recursive?)")

    @staticmethod
    def _fail(steps, stack_text, input_text, message):
        steps.append((stack_text, input_text, message))
        return ParseResult(False, steps)
