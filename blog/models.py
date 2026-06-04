from django.db import models


class BlogCategory(models.Model):
    name = models.CharField(max_length=100)

    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Blog(models.Model):
    category = models.ForeignKey(
        BlogCategory,
        on_delete=models.CASCADE
    )

    title = models.CharField(max_length=255)

    slug = models.SlugField(unique=True)

    image = models.ImageField(
        upload_to='blogs/'
    )

    content = models.TextField()

    meta_title = models.CharField(
        max_length=255,
        blank=True
    )

    meta_description = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.title
