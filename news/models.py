from django.db import models


class News(models.Model):
    title = models.CharField(max_length=500)
    author = models.CharField(max_length=500, blank=True)
    content = models.TextField()
    caption = models.CharField(max_length=500, blank=True)
    source_url = models.URLField(unique=True)
    image_url = models.URLField(blank=True)
    news_tag = models.ManyToManyField("NewsTag", related_name="news_items", blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        verbose_name_plural = "News"


class NewsTag(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
