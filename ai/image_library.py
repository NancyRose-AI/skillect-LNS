from typing import Optional, Dict, Any


# =========================================================
# APPROVED IMAGE LIBRARY
# =========================================================
#
# Only manually approved images should be added here.
# Do NOT let the LLM invent image URLs.
#
# Later we can replace these with:
# - S3 URLs
# - CloudFront URLs
# - Approved company CDN URLs
# =========================================================

APPROVED_IMAGES = {
    "AWS Cloud Engineering": [],
    "Azure Cloud Engineering": [],
    "DevOps": [],
    "Python": [],
    "Cloud Engineering": [],
}


# =========================================================
# GET APPROVED IMAGES
# =========================================================

def get_approved_images(
    topic: Optional[str],
) -> list[str]:

    if not topic:
        return []

    return APPROVED_IMAGES.get(
        topic,
        [],
    )


# =========================================================
# GET IMAGE CONTENT
# =========================================================

def get_image_content(
    topic: Optional[str],
    previously_sent: Optional[list[str]] = None,
) -> Dict[str, Any]:

    if not topic:

        return {
            "ready": False,
            "reason": "topic_missing",
            "topic": None,
            "image_url": None,
        }

    images = get_approved_images(topic)

    if not images:

        return {
            "ready": False,
            "reason": "approved_image_not_found",
            "topic": topic,
            "image_url": None,
        }

    previously_sent = previously_sent or []

    # Find an approved image that has not
    # already been sent to this lead.
    for image_url in images:

        if image_url not in previously_sent:

            return {
                "ready": True,
                "reason": "approved_image_found",
                "topic": topic,
                "image_url": image_url,
            }

    return {
        "ready": False,
        "reason": "no_unused_approved_image",
        "topic": topic,
        "image_url": None,
    }