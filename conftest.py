# conftest.py
import os
import sys

# 把项目根目录加到 sys.path 的最前面
# 这样 tests 里面就能 import scraper 包
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
