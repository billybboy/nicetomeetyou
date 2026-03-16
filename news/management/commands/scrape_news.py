"""Management command for scraping UDN NBA news into Django models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from time import sleep
from urllib.parse import urljoin

import requests
from asgiref.sync import async_to_sync
from bs4 import BeautifulSoup, Tag
from channels.layers import get_channel_layer
from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_datetime

from news.consumers import NEWS_UPDATES_GROUP
from news.models import News, NewsTag
from news.views import (
    NEWS_DETAIL_CACHE_KEY,
    NEWS_LIST_CACHE_VERSION_KEY,
    serialize_news_list_item,
)

BASE_URL = "http://tw-nba.udn.com/nba/index"
DEFAULT_TIMEOUT = 15
DEFAULT_INTERVAL = 0
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
)


@dataclass
class NewsItem:
    """Structured representation of one news card from the list page."""

    title: str
    url: str


def normalize_text(value: str | None) -> str:
    """Collapse whitespace so scraped text is easier to compare and store."""

    if not value:
        return ""
    return " ".join(value.split())


def fetch_html(url: str, timeout: int) -> str:
    """Fetch a page with the headers needed for the target site."""

    response = requests.get(
        url,
        timeout=timeout,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        },
    )
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    return response.text


def normalize_url(value: str | None, base_url: str) -> str:
    """Return an absolute URL for scraped assets and links."""

    normalized = normalize_text(value)
    if not normalized:
        return ""
    return urljoin(base_url, normalized)


def extract_items(container: Tag) -> list[NewsItem]:
    """Convert list-page entries into normalized `NewsItem` records."""

    items: list[NewsItem] = []

    for anchor in container.select("a[href]"):
        title = normalize_text(anchor.get("title"))
        if not title:
            continue

        items.append(
            NewsItem(
                title=title,
                url=anchor["href"],
            )
        )

    return items


def scrape_news_list_page(html: str) -> list[NewsItem]:
    """Scrape news_list section."""

    soup = BeautifulSoup(html, "html.parser")
    node = soup.select_one("div[id*='news_list_body']")
    if isinstance(node, Tag):
        return extract_items(node)
    return []


def get_author(soup: BeautifulSoup) -> str:
    """Return the first non-empty text match from a selector sequence."""

    node = soup.select_one(".shareBar__info--author")
    if not isinstance(node, Tag):
        return ""
    time_node = node.select_one("span")
    if isinstance(time_node, Tag):
        time_node.extract()
    text = normalize_text(node.get_text(" ", strip=True).lstrip("/").strip())
    if text:
        return text
    return ""


def get_figure_blocks(node: Tag, base_url: str) -> list[dict]:
    """Extract ordered image blocks from a figure-bearing node."""

    blocks: list[dict] = []
    for figure in node.find_all("figure"):
        if not isinstance(figure, Tag):
            continue

        image = figure.find("img")
        if not isinstance(image, Tag):
            continue

        image_url = normalize_url(
            image.get("src") or image.get("data-src") or image.get("data-original"),
            base_url,
        )
        if not image_url:
            continue

        caption = ""
        figcaption = figure.find("figcaption")
        if isinstance(figcaption, Tag):
            caption = normalize_text(figcaption.get_text(" ", strip=True))

        blocks.append(
            {
                "type": "image",
                "url": image_url,
                "caption": caption,
            }
        )
    return blocks


def get_video_block(node: Tag, base_url: str) -> dict | None:
    """Extract a video block from iframe-based embeds."""

    iframe = node.find("iframe")
    if not isinstance(iframe, Tag):
        return None

    video_url = normalize_url(iframe.get("src"), base_url)
    if not video_url:
        return None

    return {
        "type": "video",
        "url": video_url,
    }


def get_tweet_block(node: Tag, base_url: str) -> dict | None:
    """Extract a tweet block from embedded tweet markup."""

    tweet_url = ""

    blockquote = node.find("blockquote")
    if isinstance(blockquote, Tag) and "twitter" in " ".join(
        blockquote.get("class", [])
    ):
        anchor = blockquote.find("a", href=True)
        if isinstance(anchor, Tag):
            tweet_url = normalize_url(anchor.get("href"), base_url)

    if not tweet_url:
        anchor = node.find("a", href=True)
        if isinstance(anchor, Tag):
            href = normalize_url(anchor.get("href"), base_url)
            if "twitter.com" in href or "x.com" in href:
                tweet_url = href

    if not tweet_url:
        return None

    return {
        "type": "tweet",
        "url": tweet_url,
    }


def get_text_block(node: Tag) -> dict | None:
    """Extract a normalized text block from a content node."""

    text = normalize_text(node.get_text(" ", strip=True))
    if not text or len(text) <= 1:
        return None

    return {
        "type": "text",
        "value": text,
    }


def is_utility_node(node: Tag) -> bool:
    """Return whether a node is metadata, ads, or non-content utility markup."""

    classes = set(node.get("class", []))
    if classes.intersection({"shareBar", "only_web", "only_mobile", "inbox-ad", "inline-ad"}):
        return True

    node_id = node.get("id", "")
    if node_id in {"shareBar", "story_end", "google_ad", "underlay-checkpoint"}:
        return True

    if node.name in {"h1", "script", "style"}:
        return True

    return False


def get_body_nodes(container: Tag) -> list[Tag]:
    """Return the ordered body nodes from the article content wrapper."""

    content_root = container.select_one(":scope > span")
    if not isinstance(content_root, Tag):
        content_root = container

    body_nodes: list[Tag] = []
    for node in content_root.children:
        if not isinstance(node, Tag):
            continue
        if is_utility_node(node):
            continue
        body_nodes.append(node)
    return body_nodes


def get_article_content(
    soup: BeautifulSoup, fallback: str = "", base_url: str = BASE_URL
) -> list[dict]:
    """Extract the detail page body as an ordered list of structured blocks."""

    container = soup.select_one("#story_body_content")
    if not isinstance(container, Tag):
        return [{"type": "text", "value": fallback}] if fallback else []

    blocks: list[dict] = []
    for node in get_body_nodes(container):

        if node.find("figure") and not node.find("img"):
            continue

        image_blocks = get_figure_blocks(node, base_url)
        if image_blocks:
            blocks.extend(image_blocks)
            continue

        tweet_block = get_tweet_block(node, base_url)
        if tweet_block is not None:
            blocks.append(tweet_block)
            continue

        video_block = get_video_block(node, base_url)
        if video_block is not None:
            blocks.append(video_block)
            continue

        text_block = get_text_block(node)
        if text_block is not None:
            if text_block["value"] == "twitter loading...":
                continue
            blocks.append(text_block)

    if blocks:
        return blocks

    return [{"type": "text", "value": fallback}] if fallback else []


def parse_published_at(value: str) -> datetime | None:
    """Parse the publication datetime from the formats used by the site."""

    normalized = normalize_text(value)
    if not normalized:
        return None
    return parse_datetime(normalized)


def get_meta_content(soup: BeautifulSoup, selector: str) -> str:
    """Return normalized `content` from the first matching meta node."""

    node = soup.select_one(selector)
    if not isinstance(node, Tag):
        return ""

    value = normalize_text(node.get("content"))
    if value:
        return value
    return ""


def get_published_at(soup: BeautifulSoup) -> datetime | None:
    """Read the first publish timestamp exposed by the detail page."""

    value = get_meta_content(soup, "meta[property='article:published_time']")

    published_at = parse_published_at(value)
    if published_at is not None:
        return published_at

    return None


def get_article_tags(soup: BeautifulSoup) -> list[str]:
    """Extract and deduplicate article tags from the detail page."""

    tags: list[str] = []
    nodes = soup.select("a[href*='/search/tag/']")
    for node in nodes:
        if not isinstance(node, Tag):
            continue
        tag_name = normalize_text(node.get_text(" ", strip=True))
        if tag_name:
            tags.append(tag_name)

    unique_tags: list[str] = []
    seen: set[str] = set()
    for tag_name in tags:
        if tag_name in seen:
            continue
        seen.add(tag_name)
        unique_tags.append(tag_name)
    return unique_tags


def scrape_article_detail(
    item: NewsItem, timeout: int
) -> tuple[dict[str, object], list[str]]:
    """Fetch one article page and map it into `News` fields plus tag names."""

    html = fetch_html(item.url, timeout=timeout)
    soup = BeautifulSoup(html, "html.parser")

    detail = {
        "title": item.title,
        "author": get_author(soup),
        "content": get_article_content(soup, fallback=item.title, base_url=item.url),
        "source_url": get_meta_content(soup, "meta[property='og:url']") or item.url,
        "image_url": get_meta_content(soup, "meta[property='og:image']"),
        "published_at": get_published_at(soup),
    }
    return detail, get_article_tags(soup)


def broadcast_news_created(news: News) -> None:
    """Push a newly created news item to websocket subscribers."""

    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    async_to_sync(channel_layer.group_send)(
        NEWS_UPDATES_GROUP,
        {
            "type": "news_created",
            "item": serialize_news_list_item(news),
        },
    )


class Command(BaseCommand):
    """Persist scraped UDN NBA news list entries into `News` and `NewsTag`."""

    help = "Scrape NBA news from udn news_list_body and store it in the database."

    def add_arguments(self, parser) -> None:
        """Register command-line options for the scraper."""

        parser.add_argument(
            "--url",
            default=BASE_URL,
            help="Index page URL to scrape.",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=DEFAULT_TIMEOUT,
            help=f"HTTP timeout in seconds. Default: {DEFAULT_TIMEOUT}.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Limit the number of scraped items. 0 means no limit.",
        )
        parser.add_argument(
            "--interval",
            type=int,
            default=DEFAULT_INTERVAL,
            help="Repeat the scrape every N seconds. 0 means run once.",
        )

    def scrape_once(
        self, *, url: str, timeout: int, limit: int
    ) -> tuple[int, int, int]:
        """Scrape the list page once, hydrate detail pages, and upsert database rows."""

        try:
            html = fetch_html(url, timeout=timeout)
            items = scrape_news_list_page(html)
        except requests.RequestException as exc:
            raise CommandError(f"Failed to fetch index page: {exc}") from exc
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        if limit > 0:
            items = items[:limit]

        created_count = 0
        updated_count = 0
        error_count = 0
        changed = False

        for item in items:
            try:
                detail, tag_names = scrape_article_detail(item, timeout=timeout)
            except requests.RequestException as exc:
                error_count += 1
                self.stderr.write(f"Skipping {item.url}: {exc}")
                continue

            with transaction.atomic():
                news, created = News.objects.update_or_create(
                    source_url=detail["source_url"],
                    defaults=detail,
                )
                news.news_tag.clear()
                for tag_name in tag_names:
                    tag, _ = NewsTag.objects.get_or_create(name=tag_name)
                    news.news_tag.add(tag)
                if created:
                    transaction.on_commit(
                        lambda news_id=news.pk: broadcast_news_created(
                            News.objects.prefetch_related("news_tag").get(pk=news_id)
                        )
                    )
                transaction.on_commit(
                    lambda news_id=news.pk: cache.delete(
                        f"{NEWS_DETAIL_CACHE_KEY}:{news_id}"
                    )
                )

            if created:
                created_count += 1
                changed = True
                self.stdout.write(f"Created: {news.title}")
            else:
                updated_count += 1
                changed = True
                self.stdout.write(f"Updated: {news.title}")

        if changed:
            try:
                cache.incr(NEWS_LIST_CACHE_VERSION_KEY)
            except ValueError:
                cache.set(NEWS_LIST_CACHE_VERSION_KEY, 2, timeout=None)

        return created_count, updated_count, error_count

    def handle(self, *args, **options) -> None:
        """Run the scraper once or repeatedly with a sleep interval."""

        url = options["url"]
        timeout = options["timeout"]
        limit = options["limit"]
        interval = options["interval"]

        while True:
            created_count, updated_count, error_count = self.scrape_once(
                url=url,
                timeout=timeout,
                limit=limit,
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Scrape complete. created={created_count} updated={updated_count} errors={error_count}"
                )
            )

            if interval <= 0:
                break

            self.stdout.write(
                f"Sleeping for {interval} seconds before the next scrape cycle."
            )
            sleep(interval)
