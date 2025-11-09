from scraper.scraper import extract_articles_from_listing, BASE_URL


def test_extract_articles_empty():
    # 空 HTML 应该返回空列表
    assert extract_articles_from_listing("") == []


def test_parse_article_titles_basic():
    html = """
    <html>
      <body>
        <article>
          <h2><a href="/news/2025/10/28/sample-story-1/">Headline One</a></h2>
          <time datetime="2025-10-28T12:34:00-05:00">Oct. 28, 2025</time>
        </article>
        <div>
          <h2><a href="/news/2025/10/27/sample-story-2/">Subheadline A</a></h2>
          <p>Some text</p>
        </div>
      </body>
    </html>
    """
    items = extract_articles_from_listing(html, limit=5)

    titles = [it["title"] for it in items]
    assert "Headline One" in titles
    assert "Subheadline A" in titles
    assert len(titles) == 2

    urls = {it["url"] for it in items}
    assert urls == {
        f"{BASE_URL}/news/2025/10/28/sample-story-1/",
        f"{BASE_URL}/news/2025/10/27/sample-story-2/",
         }
