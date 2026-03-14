from bs4 import BeautifulSoup

from news.management.commands.scrape_news import (
    get_article_content,
    get_author,
    get_caption,
    get_meta_content,
    get_published_at,
)


def test_optional_nodes_missing_return_safe_defaults() -> None:
    soup = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")

    assert get_caption(soup) == ""
    assert get_author(soup) == ""
    assert get_meta_content(soup, "meta[property='og:url']") == ""
    assert get_published_at(soup) is None


def test_article_content_skips_figure_and_uses_explicit_fallback() -> None:
    soup = BeautifulSoup(
        """
        <html>
          <body>
            <div id="story_body_content">
              <p><figure><figcaption>Caption only</figcaption></figure></p>
              <p> </p>
            </div>
          </body>
        </html>
        """,
        "html.parser",
    )

    assert get_article_content(soup, fallback="Fallback") == "Fallback"


def test_article_content_uses_explicit_fallback_when_no_body_or_meta_exists() -> None:
    soup = BeautifulSoup(
        "<html><body><div id='story_body_content'></div></body></html>",
        "html.parser",
    )

    assert get_article_content(soup, fallback="Fallback") == "Fallback"


def test_get_meta_content_returns_normalized_content() -> None:
    soup = BeautifulSoup(
        """
        <html>
          <head>
            <meta property="og:image" content=" https://example.com/test.jpg ">
          </head>
        </html>
        """,
        "html.parser",
    )

    assert get_meta_content(soup, "meta[property='og:image']") == "https://example.com/test.jpg"
