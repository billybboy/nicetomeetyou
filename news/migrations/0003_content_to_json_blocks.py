from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("news", "0002_alter_news_author_alter_news_caption_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="news",
            old_name="content",
            new_name="content_text",
        ),
        migrations.AddField(
            model_name="news",
            name="content",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.RemoveField(
            model_name="news",
            name="content_text",
        ),
        migrations.RemoveField(
            model_name="news",
            name="caption",
        ),
    ]
