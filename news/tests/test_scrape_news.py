from bs4 import BeautifulSoup

from news.management.commands.scrape_news import (
    get_article_content,
    get_author,
    get_meta_content,
    get_published_at,
)


def test_optional_nodes_missing_return_safe_defaults() -> None:
    soup = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")

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

    assert get_article_content(soup, fallback="Fallback") == [{"type": "text", "value": "Fallback"}]


def test_article_content_uses_explicit_fallback_when_no_body_or_meta_exists() -> None:
    soup = BeautifulSoup(
        "<html><body><div id='story_body_content'></div></body></html>",
        "html.parser",
    )

    assert get_article_content(soup, fallback="Fallback") == [{"type": "text", "value": "Fallback"}]


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


def test_article_content_returns_ordered_blocks() -> None:
    soup = BeautifulSoup(
        """
        <html>
          <body>
            <div id="story_body_content">
              <p>First paragraph.</p>
              <p>
                <figure>
                  <img src="/image.jpg">
                  <figcaption>Image caption</figcaption>
                </figure>
              </p>
              <p>
                <div class="video-container">
                  <iframe src="https://www.youtube.com/embed/test"></iframe>
                </div>
              </p>
            </div>
          </body>
        </html>
        """,
        "html.parser",
    )

    assert get_article_content(soup, base_url="https://example.com/story/1") == [
        {"type": "text", "value": "First paragraph."},
        {"type": "image", "url": "https://example.com/image.jpg", "caption": "Image caption"},
        {"type": "video", "url": "https://www.youtube.com/embed/test"},
    ]


def test_article_content_ignores_title_sharebar_ads_and_keeps_real_blocks() -> None:
    soup = BeautifulSoup(
        """
        <div id="story_body_content">
          <h1 class="story_art_title">Article title</h1>
          <div class="shareBar" id="shareBar">
            <div class="shareBar__info--author">Author</div>
          </div>
          <span>
            <p>
              <figure class="photo_center photo-story">
                <img src="https://example.com/photo.jpg" />
                <figcaption>Photo caption</figcaption>
              </figure>
            </p>
            <p> </p>
            <p>First real paragraph.</p>
            <div class="only_web">
              <div class="inbox-ad" id="google_ad"></div>
            </div>
            <p>
              <div class="embedded-content">
                <blockquote class="twitter-tweet">
                  <a href="https://twitter.com/example/status/1">twitter loading...</a>
                </blockquote>
              </div>
            </p>
            <p>Second real paragraph.</p>
            <div id="story_end"></div>
          </span>
        </div>
        """,
        "html.parser",
    )

    assert get_article_content(soup, base_url="https://example.com/story/1") == [
        {
            "type": "image",
            "url": "https://example.com/photo.jpg",
            "caption": "Photo caption",
        },
        {"type": "text", "value": "First real paragraph."},
        {"type": "tweet", "url": "https://twitter.com/example/status/1"},
        {"type": "text", "value": "Second real paragraph."},
    ]
