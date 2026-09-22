#!/usr/bin/env python3
"""G3f probe. G3e's probe, run on G3f's stimuli, before the registration is sealed.

It answers the one question that decides whether this gate is worth running at all: can these
judges do this task? G3c's anti-vacuity rule declares a judge vacuous from its calibration block
if it cannot order stimuli twelve errors apart with accuracy 0.9 on some scale, or carries under
one bit about quality. Checking summaries against a passage is harder than checking arithmetic,
so a judge failing that here is a real possibility and not a formality. Knowing it before the
registration is written is what sizes the gate honestly.

Importing g3f_judge installs the two seams, so what follows is G3e's probe verbatim on new text.

    python g3f_probe.py --config g3f_config.json --models gemma31b gemma12b qwen3_27b --out probe
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
for _cand in ("G3e", "g3e"):
    if (_HERE.parent / _cand / "g3e_probe.py").exists():
        sys.path.insert(0, str(_HERE.parent / _cand))
        break

import g3f_judge  # noqa: E402,F401  (installs make_worksheet and SyntheticJudge._z)
import g3e_probe as P  # noqa: E402

if __name__ == "__main__":
    sys.exit(P.main())
