import json
import logging
from urllib import error, request

from django.conf import settings


logger = logging.getLogger(__name__)


def _strip_response_text(text):
    cleaned = (text or "").strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("html"):
            cleaned = cleaned[4:]

    return cleaned.strip()


def generate_property_description(property_obj):
    api_key = getattr(settings, "OPENAI_API_KEY", "")
    model = getattr(settings, "OPENAI_MODEL", "")
    api_url = getattr(settings, "OPENAI_CHAT_COMPLETIONS_URL", "")

    if not api_key or not model or not api_url:
        return ""

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You write original, helpful, SEO-friendly real estate "
                    "descriptions for Brij Vas. Return clean HTML only. "
                    "Do not invent amenities, approvals, exact landmarks, "
                    "loan promises, legal status, or verification claims."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Create a property description using these details:\n"
                    f"Title: {property_obj.title}\n"
                    f"Purpose: {property_obj.get_purpose_display()}\n"
                    f"Property type: {property_obj.property_type.name}\n"
                    f"City: {property_obj.city.name}\n"
                    f"State: {property_obj.state.name}\n"
                    f"Price: Rs. {property_obj.price}\n"
                    f"Area: {property_obj.display_area_sqft} sqft / "
                    f"{property_obj.display_area_gaj} gaj\n\n"
                    "Requirements:\n"
                    "- 2 short paragraphs and 1 bullet list.\n"
                    "- Include keywords naturally for Google search.\n"
                    "- Mention Brij Vas once.\n"
                    "- Keep it under 180 words.\n"
                    "- Return only HTML with p, ul, li, strong tags."
                ),
            },
        ],
        "temperature": 0.7,
        "max_tokens": 420,
    }

    data = json.dumps(payload).encode("utf-8")
    http_request = request.Request(
        api_url,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(http_request, timeout=12) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (OSError, error.HTTPError, json.JSONDecodeError) as exc:
        logger.warning("AI property description failed: %s", exc)
        return ""

    choices = body.get("choices") or []
    if not choices:
        return ""

    message = choices[0].get("message") or {}
    return _strip_response_text(message.get("content", ""))
