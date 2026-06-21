from django.db import models
from django.conf import settings
from django.urls import reverse
from core.images import optimize_uploaded_image
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
        optimize_uploaded_image(
            self.featured_image,
            max_size=(1400, 900),
            target_kb=380
        )

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


class BlogView(models.Model):
    blog = models.ForeignKey(
        Blog,
        on_delete=models.CASCADE,
        related_name="view_logs"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )

    session_key = models.CharField(
        max_length=40,
        blank=True,
        db_index=True
    )

    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True
    )

    user_agent_hash = models.CharField(
        max_length=64,
        blank=True,
        db_index=True
    )

    visitor_key = models.CharField(
        max_length=96,
        blank=True,
        db_index=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "blog",
                    "user",
                ]
            ),
            models.Index(
                fields=[
                    "blog",
                    "session_key",
                ]
            ),
            models.Index(
                fields=[
                    "blog",
                    "visitor_key",
                ]
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "blog",
                    "visitor_key",
                ],
                name="unique_blog_visitor_view"
            )
        ]

    def __str__(self):
        return f"{self.blog_id} view"
