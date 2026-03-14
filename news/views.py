from django.views.generic import TemplateView
from rest_framework import generics

from news.models import News
from news.serializers import NewsDetailSerializer, NewsListSerializer


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
    """Return news items for the list page."""

    queryset = News.objects.prefetch_related("news_tag").all()
    serializer_class = NewsListSerializer


class NewsDetailApiView(generics.RetrieveAPIView):
    """Return a single news item for the detail page."""

    queryset = News.objects.prefetch_related("news_tag").all()
    serializer_class = NewsDetailSerializer
