from django.urls import path

from news.views import (
    NewsDetailApiView,
    NewsDetailPageView,
    NewsListApiView,
    NewsListPageView,
)


app_name = "news"


urlpatterns = [
    path("", NewsListPageView.as_view(), name="list-page"),
    path("news/<int:pk>/", NewsDetailPageView.as_view(), name="detail-page"),
    path("api/news/", NewsListApiView.as_view(), name="list-api"),
    path("api/news/<int:pk>/", NewsDetailApiView.as_view(), name="detail-api"),
]
