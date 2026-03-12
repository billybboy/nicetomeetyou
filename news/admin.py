from django.contrib import admin

# Register your models here.
from .models import News, NewsTag


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "published_at")
    search_fields = ("title", "author", "content")
    list_filter = ("published_at",)
    filter_horizontal = ("news_tag",)


@admin.register(NewsTag)
class NewsTagAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
