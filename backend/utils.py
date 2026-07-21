"""
utils.py
========
Shared text preprocessing utilities used by both train_model.py and model.py.
The preprocess function MUST live here (not in __main__) so that joblib can
deserialize the sklearn pipeline correctly when the server loads the pickle.
"""

import re


def preprocess(text: str) -> str:
    """Lowercase, collapse whitespace."""
    text = text.lower()
    return re.sub(r"\s+", " ", text).strip()

