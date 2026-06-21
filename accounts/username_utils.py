import re

from django.contrib.auth.validators import UnicodeUsernameValidator
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError


User = get_user_model()
username_validator = UnicodeUsernameValidator()


def normalize_username_seed(username):
    seed = (username or "").strip().lower()
    seed = re.sub(r"[^a-z0-9_]+", "_", seed)
    seed = re.sub(r"_+", "_", seed).strip("_")
    return seed or "brijvas_user"


def username_exists(username):
    return User.objects.filter(username__iexact=username).exists()


def validate_username(username):
    try:
        username_validator(username)
    except ValidationError:
        return False

    return True


def suggest_usernames(username, limit=3):
    seed = normalize_username_seed(username)
    suggestions = []
    number = 2

    while len(suggestions) < limit and number < 1000:
        candidate = f"{seed}{number}"

        if not username_exists(candidate):
            suggestions.append(candidate)

        number += 1

    return suggestions
