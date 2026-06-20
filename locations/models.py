from django.db import models
from core.seo import unique_slug


class State(models.Model):

    name = models.CharField(max_length=100)

    slug = models.SlugField(
        unique=True,
        blank=True
    )

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(
                self,
                self.name,
                fallback="state"
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class City(models.Model):

    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        related_name='cities'
    )

    name = models.CharField(max_length=100)

    slug = models.SlugField(
        unique=True,
        blank=True
    )

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(
                self,
                f"{self.name} {getattr(self.state, 'name', '')}",
                fallback="city"
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
