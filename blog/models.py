from django.db import models
from django.conf import settings
from django.urls import reverse
from core.seo import unique_slug


class BlogCategory(models.Model):
    name = models.CharField(max_length=100)

    slug = models.SlugField(
        unique=True,
        blank=True
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(
                self,
                self.name,
                fallback="blog-category"
            )

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse(
            "category_blogs",
            kwargs={"slug": self.slug}
        )

    def __str__(self):
        return self.name


class Blog(models.Model):
    title = models.CharField(
        max_length=255
    )

    slug = models.SlugField(
        unique=True,
        blank=True
    )

    category = models.ForeignKey(
        BlogCategory,
        on_delete=models.CASCADE
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    featured_image = models.ImageField(
        upload_to="blogs/"
    )

    excerpt = models.TextField(
        blank=True
    )

    content = models.TextField()

    views = models.PositiveIntegerField(
        default=0
    )

    is_published = models.BooleanField(
        default=True
    )

    seo_title = models.CharField(
        max_length=255,
        blank=True
    )

    seo_description = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(
                self,
                self.title,
                fallback="blog"
            )

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse(

            "blog_detail",

            kwargs={"slug": self.slug}

        )

    def __str__(self):
        return self.title


class BlogComment(models.Model):
    blog = models.ForeignKey(
        Blog,
        on_delete=models.CASCADE,
        related_name="comments"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    comment = models.TextField()

    is_approved = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )
