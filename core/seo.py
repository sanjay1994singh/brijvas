import re

from django.conf import settings
from django.utils.html import strip_tags
from django.utils.text import Truncator, slugify


DEVANAGARI_MAP = {
    "अ": "a", "आ": "aa", "इ": "i", "ई": "ee", "उ": "u", "ऊ": "oo",
    "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au", "ऋ": "ri",
    "ा": "aa", "ि": "i", "ी": "ee", "ु": "u", "ू": "oo", "े": "e",
    "ै": "ai", "ो": "o", "ौ": "au", "ृ": "ri", "ं": "n", "ँ": "n",
    "ः": "h", "्": "",
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ng",
    "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "ny",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
    "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
    "य": "y", "र": "r", "ल": "l", "व": "v", "श": "sh",
    "ष": "sh", "स": "s", "ह": "h", "ळ": "l",
    "ड़": "d", "ढ़": "dh", "ऑ": "o", "ॉ": "o",
}

COMMON_HINGLISH_REPLACEMENTS = {
    "वृंदावन": "vrindavan",
    "वृन्दावन": "vrindavan",
    "मथुरा": "mathura",
    "बरसाना": "barsana",
    "गोवर्धन": "govardhan",
    "राधा": "radha",
    "कृष्ण": "krishna",
    "बांके बिहारी": "banke bihari",
    "बाँके बिहारी": "banke bihari",
    "में": "mein",
}


def romanize_hindi(value):
    text = str(value or "")
    for hindi, hinglish in COMMON_HINGLISH_REPLACEMENTS.items():
        text = text.replace(hindi, hinglish)
    return "".join(DEVANAGARI_MAP.get(char, char) for char in text)


def seo_slugify(value, fallback="item", max_length=90):
    text = romanize_hindi(value)
    text = re.sub(r"[^\w\s-]", " ", text, flags=re.UNICODE)
    slug = slugify(text)[:max_length].strip("-")
    return slug or fallback


def unique_slug(instance, value, slug_field="slug", fallback="item", max_length=90):
    model = instance.__class__
    base_slug = seo_slugify(value, fallback=fallback, max_length=max_length)
    slug = base_slug
    counter = 2

    queryset = model._default_manager.filter(**{slug_field: slug})
    if instance.pk:
        queryset = queryset.exclude(pk=instance.pk)

    while queryset.exists():
        suffix = f"-{counter}"
        slug = f"{base_slug[:max_length - len(suffix)]}{suffix}"
        queryset = model._default_manager.filter(**{slug_field: slug})
        if instance.pk:
            queryset = queryset.exclude(pk=instance.pk)
        counter += 1

    return slug


def clean_excerpt(value, words=28):
    text = strip_tags(value or "")
    text = re.sub(r"\s+", " ", text).strip()
    return Truncator(text).words(words, truncate="...")


def site_base_url(request=None):
    configured = getattr(settings, "SITE_URL", "").strip().rstrip("/")
    if configured:
        return configured
    if request:
        return f"{request.scheme}://{request.get_host()}"
    return ""


def absolute_url(path_or_url, request=None):
    if not path_or_url:
        return ""
    value = str(path_or_url)
    if value.startswith(("http://", "https://")):
        return value
    return f"{site_base_url(request)}{value}"
