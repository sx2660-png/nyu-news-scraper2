# nyu-news-scraper

这是一个最小的 Python 抓取器测试项目，用于从NYU news页面提取信息。

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
Error Handling考虑：
脚本通过 fetch() 的 try/except 捕获网络异常返回 None，上层据此打印 [WARN]/[FATAL] 并选择跳过或干净退出；解析阶段大量判空与多级回退（列表：<article>→h1/2/3；正文容器多候选），日期提取也有容错链（time@datetime→文本→URL→normalize_date_fuzzy），整体在网络失败或 HTML 结构变化时不会崩溃而是降级处理。

注意：示例代码包含一个解析 HTML 的函数（基于 BeautifulSoup），测试使用内嵌 HTML 来避免网络依赖。
