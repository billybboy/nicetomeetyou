from rest_framework import serializers

from news.models import News


class NewsListSerializer(serializers.ModelSerializer):
    """Compact payload for the AJAX-backed news list page."""

    tags = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        source="news_tag",
        slug_field="name",
    )
    detail_url = serializers.SerializerMethodField()
    excerpt = serializers.SerializerMethodField()

    class Meta:
        model = News
        fields = (
            "id",
            "title",
            "author",
            "caption",
            "image_url",
            "published_at",
            "detail_url",
            "excerpt",
            "tags",
        )

    def get_detail_url(self, obj: News) -> str:
        request = self.context.get("request")
        relative_url = f"/news/{obj.pk}/"
        if request is None:
            return relative_url
        return request.build_absolute_uri(relative_url)

    def get_excerpt(self, obj: News) -> str:
        return obj.content[:160].strip()


class NewsDetailSerializer(serializers.ModelSerializer):
    """Full payload for the AJAX-backed news detail page."""

    tags = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        source="news_tag",
        slug_field="name",
    )

    class Meta:
        model = News
        fields = (
            "id",
            "title",
            "author",
            "caption",
            "content",
            "source_url",
            "image_url",
            "published_at",
            "created_at",
            "updated_at",
            "tags",
        )
