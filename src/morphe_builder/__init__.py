import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # module -> src -> root
os.chdir(ROOT)
