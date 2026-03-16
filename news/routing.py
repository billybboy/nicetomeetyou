from django.urls import path

from news.consumers import NewsUpdatesConsumer


websocket_urlpatterns = [
    path("ws/news/", NewsUpdatesConsumer.as_asgi()),
]
