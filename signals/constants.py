SIGNAL_COLS = [
    "smirk",
    "risk_reversal",
    "put_call_spread",
    "term_slope",
    "vrp",
    "implied_skew",
]

# Oriented signal = raw * sign; long top oriented names, short bottom.
# Matches sign audit in config.yaml / instructions.md.
SIGNAL_ORIENTATION = {
    "smirk": -1.0,           # high → short
    "risk_reversal": 1.0,    # high → long
    "put_call_spread": 1.0,  # high → long
    "term_slope": 1.0,       # empirical; oriented by raw level
    "vrp": 1.0,              # empirical
    "implied_skew": -1.0,    # more negative → long (CDG)
}

DEFAULT_FORWARD_HORIZONS = (5, 21, 63)
