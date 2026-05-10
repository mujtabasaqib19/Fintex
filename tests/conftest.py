"""
pytest configuration for the Fintex test suite.
Adds the project root to sys.path so all tests can import src/ and config/.
"""
import sys, os

# Ensure project root is on the path regardless of where pytest is invoked from
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
