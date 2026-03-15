import json

from django.core.cache import cache
from django.views.generic import TemplateView
from rest_framework import status
from rest_framework.response import Response
from rest_framework import generics

from news.models import News
from news.serializers import NewsDetailSerializer, NewsListSerializer

NEWS_LIST_CACHE_KEY = "news:list"
NEWS_LIST_CACHE_TIMEOUT = 60


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

    def list(self, request, *args, **kwargs):
        cached_payload = cache.get(NEWS_LIST_CACHE_KEY)
        if cached_payload is not None:
            return Response(json.loads(cached_payload), status=status.HTTP_200_OK)

        response = super().list(request, *args, **kwargs)
        cache.set(
            NEWS_LIST_CACHE_KEY,
            json.dumps(response.data, ensure_ascii=False),
            timeout=NEWS_LIST_CACHE_TIMEOUT,
        )
        return response


class NewsDetailApiView(generics.RetrieveAPIView):
    """Return a single news item for the detail page."""

    queryset = News.objects.prefetch_related("news_tag").all()
    serializer_class = NewsDetailSerializer
