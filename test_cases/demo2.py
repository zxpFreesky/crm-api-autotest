import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


def test_demo():
    assert 1 + 1 == 2


if __name__ == "__main__":
    pytest.main([__file__, '-v', '-s'])
