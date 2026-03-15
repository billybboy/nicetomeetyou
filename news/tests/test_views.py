import pytest
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

from news.models import News, NewsTag


@pytest.fixture
def news_item(db) -> News:
    cache.clear()
    news = News.objects.create(
        title="Test headline",
        author="Reporter",
        content="Paragraph one.\n\nParagraph two.",
        caption="Test caption",
        source_url="https://example.com/news/1",
        image_url="https://example.com/image.jpg",
        published_at=timezone.now(),
    )
    tag = NewsTag.objects.create(name="NBA")
    news.news_tag.add(tag)
    return news


@pytest.mark.django_db
def test_news_list_page_renders(client) -> None:
    response = client.get(reverse("news:list-page"))

    assert response.status_code == 200
    assert "NBA新聞列表" in response.content.decode()


@pytest.mark.django_db
def test_news_detail_page_renders(client, news_item: News) -> None:
    response = client.get(reverse("news:detail-page", args=[news_item.pk]))

    assert response.status_code == 200
    assert "正在載入新聞詳情" in response.content.decode()


@pytest.mark.django_db
def test_news_list_api_returns_serialized_news(client, news_item: News) -> None:
    response = client.get(reverse("news:list-api"))

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["title"] == news_item.title
    assert payload[0]["tags"] == ["NBA"]


@pytest.mark.django_db
def test_news_list_api_uses_cache_aside(client, news_item: News) -> None:
    first_response = client.get(reverse("news:list-api"))

    assert first_response.status_code == 200
    news_item.delete()

    second_response = client.get(reverse("news:list-api"))

    assert second_response.status_code == 200
    payload = second_response.json()
    assert len(payload) == 1
    assert payload[0]["title"] == "Test headline"


@pytest.mark.django_db
def test_news_detail_api_returns_full_news(client, news_item: News) -> None:
    response = client.get(reverse("news:detail-api", args=[news_item.pk]))

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == news_item.title
    assert payload["content"] == news_item.content
    assert payload["tags"] == ["NBA"]
