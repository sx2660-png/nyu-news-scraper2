# nyu-news-scraper

这是一个最小的 Python 抓取器项目骨架，用于从新闻页面提取信息（示例项目）。

基本文件：

- `scraper/` - 包含爬虫和解析逻辑。
- `tests/` - 包含 pytest 测试。
- `requirements.txt` - 列出运行所需依赖。

如何生成并运行工作区（macOS / zsh）：

```bash
# 1. 进入项目目录
cd /Users/senzu/Documents/nyu-news-scraper

# 2. 创建并激活虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行单元测试
pytest -q
```

注意：示例代码包含一个解析 HTML 的函数（基于 BeautifulSoup），测试使用内嵌 HTML 来避免网络依赖。
