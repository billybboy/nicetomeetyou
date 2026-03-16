import pytest
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator

from nba_news.asgi import application
from news.consumers import NEWS_UPDATES_GROUP


@pytest.mark.asyncio
async def test_news_updates_consumer_receives_group_message() -> None:
    communicator = WebsocketCommunicator(application, "/ws/news/")
    connected, _ = await communicator.connect()

    assert connected is True

    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        NEWS_UPDATES_GROUP,
        {
            "type": "news_created",
            "item": {"id": 1, "title": "Breaking News"},
        },
    )

    response = await communicator.receive_json_from()

    assert response == {
        "type": "news.created",
        "item": {"id": 1, "title": "Breaking News"},
    }

    await communicator.disconnect()
