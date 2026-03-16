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
        content=[
            {"type": "text", "value": "Paragraph one."},
            {"type": "text", "value": "Paragraph two."},
        ],
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
    assert payload["count"] == 1
    assert payload["next"] is None
    assert payload["previous"] is None
    assert len(payload["results"]) == 1
    assert payload["results"][0]["title"] == news_item.title
    assert "excerpt" not in payload["results"][0]
    assert payload["results"][0]["tags"] == ["NBA"]


@pytest.mark.django_db
def test_news_list_api_paginates_20_items_per_page(client, news_item: News) -> None:
    for index in range(2, 22):
        News.objects.create(
            title=f"Headline {index}",
            author="Reporter",
            content=[{"type": "text", "value": f"Paragraph {index}."}],
            source_url=f"https://example.com/news/{index}",
            image_url="https://example.com/image.jpg",
            published_at=timezone.now(),
        )

    response = client.get(reverse("news:list-api"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 21
    assert len(payload["results"]) == 20
    assert payload["next"] is not None
    assert payload["previous"] is None


@pytest.mark.django_db
def test_news_list_api_uses_cache_aside(client, news_item: News) -> None:
    first_response = client.get(reverse("news:list-api"))

    assert first_response.status_code == 200
    news_item.delete()

    second_response = client.get(reverse("news:list-api"))

    assert second_response.status_code == 200
    payload = second_response.json()
    assert payload["count"] == 1
    assert payload["results"][0]["title"] == "Test headline"


@pytest.mark.django_db
def test_news_detail_api_returns_full_news(client, news_item: News) -> None:
    response = client.get(reverse("news:detail-api", args=[news_item.pk]))

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == news_item.title
    assert payload["content"] == news_item.content
    assert payload["tags"] == ["NBA"]


@pytest.mark.django_db
def test_news_detail_api_uses_cache_aside(client, news_item: News) -> None:
    news_id = news_item.pk
    first_response = client.get(reverse("news:detail-api", args=[news_id]))

    assert first_response.status_code == 200
    news_item.delete()

    second_response = client.get(reverse("news:detail-api", args=[news_id]))

    assert second_response.status_code == 200
    payload = second_response.json()
    assert payload["title"] == "Test headline"
