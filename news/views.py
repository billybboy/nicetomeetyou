import json

from django.core.cache import cache
from django.views.generic import TemplateView
from rest_framework import generics, pagination, status
from rest_framework.response import Response

from news.models import News
from news.serializers import NewsDetailSerializer, NewsListSerializer

NEWS_LIST_CACHE_KEY = "news:list"
NEWS_LIST_CACHE_TIMEOUT = 60
NEWS_LIST_PAGE_SIZE = 20
NEWS_LIST_CACHE_VERSION_KEY = "news:list:version"


def get_news_list_cache_version() -> int:
    """Return the current cache version for paginated news-list payloads."""

    version = cache.get(NEWS_LIST_CACHE_VERSION_KEY)
    if version is None:
        cache.set(NEWS_LIST_CACHE_VERSION_KEY, 1, timeout=None)
        return 1
    return int(version)


def serialize_news_list_item(news: News, request=None) -> dict:
    """Serialize one news item into the list-page payload shape."""

    serializer = NewsListSerializer(
        news,
        context={"request": request} if request is not None else {},
    )
    return serializer.data


class NewsListPageView(TemplateView):
    """Shell page for the AJAX-driven news list."""

    template_name = "news/news_list.html"


class NewsDetailPageView(TemplateView):
    """Shell page for the AJAX-driven news detail view."""

    template_name = "news/news_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["news_id"] = self.kwargs["pk"]
        return context


class NewsListApiView(generics.ListAPIView):
    """Return news items for the list page using cache-aside reads."""

    queryset = News.objects.prefetch_related("news_tag").all()
    serializer_class = NewsListSerializer
    pagination_class = pagination.PageNumberPagination

    def paginate_queryset(self, queryset):
        if self.paginator is not None:
            self.paginator.page_size = NEWS_LIST_PAGE_SIZE
        return super().paginate_queryset(queryset)

    def list(self, request, *args, **kwargs):
        page_number = request.query_params.get("page", "1")
        cache_version = get_news_list_cache_version()
        cache_key = f"{NEWS_LIST_CACHE_KEY}:v{cache_version}:page:{page_number}"
        cached_payload = cache.get(cache_key)
        if cached_payload is not None:
            return Response(json.loads(cached_payload), status=status.HTTP_200_OK)

        response = super().list(request, *args, **kwargs)
        cache.set(
            cache_key,
            json.dumps(response.data, ensure_ascii=False),
            timeout=NEWS_LIST_CACHE_TIMEOUT,
        )
        return response


class NewsDetailApiView(generics.RetrieveAPIView):
    """Return a single news item for the detail page."""

    queryset = News.objects.prefetch_related("news_tag").all()
    serializer_class = NewsDetailSerializer
