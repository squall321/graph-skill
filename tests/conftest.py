import sys
from pathlib import Path

# allow `import graph_skill` from source without an install
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
