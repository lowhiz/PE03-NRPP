"""
run_tests.py -- quick self-test for the back end (no GUI needed).
Run with:  python run_tests.py
Needs rules.prod and rules.ptbl in the same folder.
"""
import file_handler as fh
from parser_engine import PredictiveParser, tokenize_input

# (input, expected validity, expected error text or None)
CASES = [
    ("id + id * id",      True,  None),
    ("id",                True,  None),
    ("( id + id ) * id",  True,  None),
    ("id   +   id",       True,  None),
    ("id + id $",         True,  None),
    ("id + * id",         False, "Error: no rule for T with input '*'"),
    ("id id",             False, "Error: no rule for T' with input 'id'"),
    ("( id",              False, "Error: expected ')' but found '$'"),
    ("+ id",              False, "Error: no rule for E with input '+'"),
    ("id +",              False, "Error: no rule for T with input '$'"),
    ("id * * id",         False, "Error: no rule for F with input '*'"),
    ("id - id",           False, "Error: '-' is not a terminal of this grammar"),
]

parser = PredictiveParser(fh.load_productions("rules.prod"),
                          fh.load_parse_table("rules.ptbl"))
passed = 0
for text, want_valid, want_error in CASES:
    result = parser.parse(tokenize_input(text))
    last = result.steps[-1]
    ok = result.valid == want_valid and (want_error is None or last[2] == want_error)
    passed += ok
    print("%s  %-18s -> %-7s %d rows  %s" % (
        "PASS" if ok else "FAIL", text,
        "VALID" if result.valid else "INVALID", len(result.steps),
        "" if result.valid else last[2]))
print("\n%d of %d tests passed" % (passed, len(CASES)))
