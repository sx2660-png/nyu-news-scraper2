#!/usr/bin/env python3
"""
scraper/scraper.py

- 抓取 NYU University News 列表页
- 解析前 5 篇文章的标题/URL/日期
- 逐篇抓正文，统计字数，生成 summary
- 写 articles.json 和 report.md

只用:
- requests-拉页面
- beautifulsoup4-解析HTML
- Python 标准库
"""
# --- Standard library imports ---
from urllib.parse import urljoin # 确保这个 import 在文件顶部
from datetime import datetime
from pathlib import Path
import json
import re
import sys
from typing import Dict, List, Optional, Tuple


# --- Third-party imports ---
import requests
from bs4 import BeautifulSoup

#站点根和列表页在这里
BASE_URL = "https://nyunews.com"
LISTING_URL = "https://nyunews.com/category/news/university-news/"

#伪装成User-agent，避免被403
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        " AppleWebKit/537.36 (KHTML, like Gecko)"
        " Chrome/125.0 Safari/537.36"
    )
}


def fetch(url: str) -> Optional[str]:
    """GET 请求网页，返回 HTML 文本。失败时返回 None。"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        print(f"[ERROR] Failed to fetch {url}: {e}", file=sys.stderr)
        return None




def extract_articles_from_listing(html: str, limit: int = 5) -> List[Dict[str, str]]:
    """
    Parse the University News listing page and return up to `limit` articles.

    For each article we try to return:
    {
        "title": "...",
        "url": "https://nyunews.com/....",
        "date_raw": "2025-10-28"  # may be "" if not found here
    }

    Strategy:
    1) First try classic <article> blocks (WordPress-style).
    2) If that yields nothing, fallback to scanning <h1>/<h2>/<h3> with <a>
       whose href contains '/news/' (to avoid pulling Opinion/Editorial/etc).
    3) Deduplicate by URL to avoid repeated promos on the page.
    """

    soup = BeautifulSoup(html, "html.parser")
    results: List[Dict[str, str]] = []
    seen_urls = set()

    # --- Strategy 1: <article> blocks (old theme / classic WP) ---
    for art in soup.find_all("article"):
        title_tag = art.find("h2") or art.find("h3") or art.find("h1")
        if not title_tag:
            continue

        link_tag = title_tag.find("a", href=True)
        if not link_tag:
            continue

        raw_url = link_tag["href"].strip()
        full_url = urljoin(BASE_URL, raw_url)

        # optional basic filter: must look like a news article
        if "/news/" not in full_url:
            continue

        if full_url in seen_urls:
            continue

        # try to grab a date next to the article card
        date_raw = ""
        time_tag = art.find("time")
        if time_tag:
            # if there is datetime="2025-10-28T..." use that first
            dt_attr = time_tag.get("datetime")
            if dt_attr:
                if "T" in dt_attr:
                    date_raw = dt_attr.split("T", 1)[0].strip()
                else:
                    date_raw = dt_attr.strip()
                    # if no time(backup)
            if not date_raw:
                date_raw = time_tag.get_text(strip=True)

        results.append(
            {
                "title": title_tag.get_text(strip=True),
                "url": full_url,
                "date_raw": date_raw,
            }
        )
        seen_urls.add(full_url)

        if len(results) >= limit:
            return results  # we can just return early

    # --- Strategy 2: fallback for current WSN layout ---
    # The category page lists headlines in <h2>/<h3> with <a>, and repeats stories.
    if len(results) < limit:
        for heading in soup.find_all(["h1", "h2", "h3"]):
            link_tag = heading.find("a", href=True)
            if not link_tag:
                continue

            raw_url = link_tag["href"].strip()
            full_url = urljoin(BASE_URL, raw_url)

            # only keep actual News articles (skip /opinion/, /editorial/, etc.)
            if "/news/" not in full_url:
                continue

            if full_url in seen_urls:
                continue

            title_text = heading.get_text(strip=True)
            if not title_text:
                continue

            results.append(
                {
                    "title": title_text,
                    "url": full_url,
                    "date_raw": "",  # we'll fill date later from the article page
                }
            )
            seen_urls.add(full_url)

            if len(results) >= limit:
                break

    return results



def normalize_date_fuzzy(date_str: str) -> Optional[str]:
    """把各种日期格式转成 YYYY-MM-DD，如果失败返回 None。"""
    if not date_str:
        return None

    cleaned = (
        date_str.replace("Sept.", "Sep.")
        .replace("Sept", "Sep")
        .replace("  ", " ")
        .strip()
    )

    fmts = [
        "%b. %d, %Y",   # "Oct. 27, 2025"
        "%b %d, %Y",    # "Oct 27, 2025"
        "%B %d, %Y",    # "October 27, 2025"
        "%Y-%m-%d",     # already ISO
    ]

    for fmt in fmts:
        try:
            dt = datetime.strptime(cleaned, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None
        
 # --- time search backup ---

def date_from_url(url: str) -> Optional[str]:
    """
    从 URL 中提取 /YYYY/MM/DD/ 这部分，
    转成 YYYY-MM-DD。
    """
    m = re.search(r"/(\d{4})/(\d{1,2})/(\d{1,2})/", url)
    if not m:
        return None
    year, month, day = m.groups()
    return f"{year}-{int(month):02d}-{int(day):02d}"


def extract_body_text_and_date(html: str) -> Tuple[str, Optional[str]]:
    """
    从文章详情页 HTML 里提取正文文本和日期。
    返回 (body_text, iso_date)
    """
    soup = BeautifulSoup(html, "html.parser")

    # 优先拿机器可读的发布时间
    iso_date: Optional[str] = None
    # 1) <meta property="article:published_time" ...>
    meta_time = soup.find("meta", attrs={"property": "article:published_time"}) or \
               soup.find("meta", attrs={"name": "article:published_time"})
    if meta_time and meta_time.get("content"):
        iso_date = meta_time["content"].strip()

   # 2) <time datetime="..."> 或其文本
    if not iso_date:
       time_tag = soup.find("time")
       if time_tag:
           dt_attr = time_tag.get("datetime")
           if dt_attr:
               iso_date = dt_attr.strip()  # 保留完整 datetime（包含时间/时区）
           else:
              iso_date = normalize_date_fuzzy(time_tag.get_text(strip=True))

   # 3) JSON-LD 里的 datePublished/dateCreated
    if not iso_date:
       for script in soup.find_all("script", type="application/ld+json"):
           try:
               data = json.loads(script.string or "")
           except Exception:
               continue
           def pick_date(obj):
               return obj.get("datePublished") or obj.get("dateCreated") if isinstance(obj, dict) else None
           candidate = None
           if isinstance(data, list):
               for item in data:
                   candidate = pick_date(item)
                   if candidate:
                       break
           else:
               candidate = pick_date(data)
           if candidate:
               iso_date = str(candidate).strip()
               break

    # 找正文容器（兜底策略多重尝试）
    candidate_selectors = [
        ("div", "entry-content"),
        ("div", "post-content"),
        ("div", "single-body"),
        ("article", "post"),
        ("article", None),
    ]

    content_container = None
    for tag_name, class_name in candidate_selectors:
        if class_name:
            nodes = soup.find_all(tag_name, class_=class_name)
        else:
            nodes = soup.find_all(tag_name)

        for node in nodes:
            if node.find("p"):
                content_container = node
                break
        if content_container:
            break

    # 最后兜底 body
    if not content_container:
        content_container = soup.body or soup

    paragraphs = []
    for p in content_container.find_all("p"):
        text = p.get_text(" ", strip=True)
        if len(text.split()) < 3:
            # 如果非常短就不计入
            continue
        paragraphs.append(text)

    body_text = "\n\n".join(paragraphs).strip()
    return body_text, iso_date


def summarize(text: str, max_words: int = 50) -> Tuple[int, str]:
    """
    返回 (词数, 前 max_words 个词组成的摘要+"...")
    """
    words = text.split()
    wc = len(words)
    summary_words = words[:max_words]
    summary = " ".join(summary_words)
    if wc > max_words:
        summary += "..."
    return wc, summary


def build_output(articles_meta: List[Dict[str, str]]) -> List[Dict[str, object]]:
    """
    给定列表页解析出来的文章元信息，逐篇抓正文并整理成最终结构。
    """
    results = []

    for art in articles_meta:
        print(f"[INFO] Fetching article: {art['url']}")
        article_html = fetch(art["url"])
        if not article_html:
            print(
                f"[WARN] Skip article (failed to fetch body): {art['url']}",
                file=sys.stderr,
            )
            continue

        body_text, page_date = extract_body_text_and_date(article_html)
        word_count, summary = summarize(body_text)
        #日期部分
        final_date = (
            normalize_date_fuzzy(page_date or "") 
            or normalize_date_fuzzy(art.get("date_raw", ""))
            or date_from_url(art["url"])
            or ""
        )
        # 保险：如果仍是 datetime（极少数情况），裁成日期
        if "T" in final_date:
             final_date = final_date.split("T", 1)[0]

        results.append(
            {
                "title": art["title"],
                "url": art["url"],
                "date": final_date,
                "word_count": word_count,
                "summary": summary,
            }
        )

    return results


def write_json(data: List[Dict[str, object]], path: Path) -> None:
    """写出 articles.json。"""
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_markdown(data: List[Dict[str, object]], path: Path) -> None:
    """写出 report.md。"""
    lines = ["# NYU News Report", ""]

    for item in data:
        title = item["title"]
        date = item["date"]
        url = item["url"]
        summary = item["summary"]

        lines.append(f"## {title} ({date})")
        lines.append(f"**URL:** {url}")
        lines.append(f"**Summary:** {summary}")
        lines.append("")
        lines.append("---")
        lines.append("")

    with path.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> None:
    """命令行主入口：抓 -> 解析 -> 写文件。"""
    listing_html = fetch(LISTING_URL)
    if not listing_html:
        print("[FATAL] Could not fetch listing page.", file=sys.stderr)
        sys.exit(1)

    articles_meta = extract_articles_from_listing(listing_html, limit=5)
    if not articles_meta:
        print("[FATAL] No articles found on listing page.", file=sys.stderr)
        sys.exit(1)

    final_data = build_output(articles_meta)

    out_json = Path("articles.json")
    out_md = Path("report.md")

    write_json(final_data, out_json)
    write_markdown(final_data, out_md)

    print(f"[DONE] Wrote {out_json.resolve()}")
    print(f"[DONE] Wrote {out_md.resolve()}")


if __name__ == "__main__":
    main()
