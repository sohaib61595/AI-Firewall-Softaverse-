# backend package
import sys
from backend.core import utils

sys.modules.setdefault("backend.utils", utils)
