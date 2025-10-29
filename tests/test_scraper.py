from scraper.scraper import parse_article_titles


def test_parse_article_titles_empty():
    assert parse_article_titles("") == []


def test_parse_article_titles_basic():
    html = """
    <html>
      <body>
        <h1>Headline One</h1>
        <div>
          <h2>Subheadline A</h2>
          <p>Some text</p>
        </div>
      </body>
    </html>
    """
    titles = parse_article_titles(html)
    assert "Headline One" in titles
    assert "Subheadline A" in titles
    assert len(titles) == 2
