import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import RegionalManager

if __name__ == "__main__":
    RegionalManager("関東").execute()