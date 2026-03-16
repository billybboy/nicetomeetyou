import json

from channels.generic.websocket import AsyncWebsocketConsumer


NEWS_UPDATES_GROUP = "news_updates"


class NewsUpdatesConsumer(AsyncWebsocketConsumer):
    """Push newly scraped news items to connected list-page clients."""

    async def connect(self) -> None:
        await self.channel_layer.group_add(NEWS_UPDATES_GROUP, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code: int) -> None:
        await self.channel_layer.group_discard(NEWS_UPDATES_GROUP, self.channel_name)

    async def news_created(self, event: dict) -> None:
        await self.send(
            text_data=json.dumps(
                {
                    "type": "news.created",
                    "item": event["item"],
                },
                ensure_ascii=False,
            )
        )
