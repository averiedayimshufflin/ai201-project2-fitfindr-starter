"""
Individual FitFindr tools.

These functions are intentionally usable on their own so they can be tested
before the planning loop wires them together.
"""

from __future__ import annotations

import os
import re
from typing import Any

from utils.data_loader import load_listings


GROQ_MODEL = "llama-3.3-70b-versatile"


def _load_environment() -> None:
    """Load .env when python-dotenv is installed."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    load_dotenv()


def _get_groq_client() -> Any:
    """Create a Groq client using GROQ_API_KEY from the environment or .env."""
    _load_environment()
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing. Add it to .env before calling LLM tools.")

    try:
        from groq import Groq
    except ImportError as exc:
        raise RuntimeError("The groq package is not installed. Run pip install -r requirements.txt.") from exc

    return Groq(api_key=api_key)


def _call_groq(prompt: str, temperature: float = 0.7) -> str:
    """Call Groq and return the model response as a string."""
    client = _get_groq_client()

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful fashion styling assistant for second-hand shopping.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=temperature,
    )

    return response.choices[0].message.content.strip()


def _normalize_words(text: str) -> list[str]:
    """Return searchable words while ignoring tiny filler terms."""
    stop_words = {"a", "an", "and", "for", "in", "of", "the", "under", "with"}
    return [
        word
        for word in re.findall(r"[a-z0-9']+", text.lower())
        if len(word) > 1 and word not in stop_words
    ]


def _listing_search_text(listing: dict) -> str:
    fields = [
        listing.get("title", ""),
        listing.get("description", ""),
        listing.get("category", ""),
        " ".join(listing.get("style_tags", [])),
        " ".join(listing.get("colors", [])),
        listing.get("brand") or "",
        listing.get("platform", ""),
    ]
    return " ".join(str(field) for field in fields).lower()


def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Item description such as "black leather jacket".
        size: Optional requested size such as "M", "8", or None.
        max_price: Optional highest price the user will pay.

    Returns:
        A list of matching listing dictionaries sorted by relevance. Each
        returned item includes an added match_reason string.

    Failure mode:
        Returns an empty list when no listings match. It does not raise for
        normal "nothing found" searches.
    """
    query_words = _normalize_words(description or "")
    if not query_words:
        return []

    matches = []
    requested_size = str(size).strip().lower() if size is not None else None

    for listing in load_listings():
        price = float(listing.get("price", 0))
        if max_price is not None and price > float(max_price):
            continue

        listing_size = str(listing.get("size", "")).lower()
        if requested_size and requested_size not in listing_size:
            continue

        searchable_text = _listing_search_text(listing)
        matched_words = [word for word in query_words if word in searchable_text]
        if not matched_words:
            continue

        result = listing.copy()
        result["match_score"] = len(matched_words)
        result["match_reason"] = (
            f"Matched {', '.join(matched_words)}"
            f" and fits the price/size filters."
        )
        matches.append(result)

    matches.sort(key=lambda item: (-item["match_score"], item["price"]))
    return matches


def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1-2 complete outfits.

    Args:
        new_item: The listing selected from search_listings.
        wardrobe: A wardrobe dict with an "items" list.

    Returns:
        A concise outfit suggestion string.

    Failure mode:
        If wardrobe["items"] is empty, returns a clear error message string
        instead of crashing or calling the LLM with no wardrobe context.
    """
    wardrobe_items = wardrobe.get("items", []) if isinstance(wardrobe, dict) else []
    if not wardrobe_items:
        return (
            "I found a listing, but I could not create an outfit from your wardrobe. "
            "Try adding more wardrobe basics, shoes, or accessories."
        )

    item_details = f"""
New thrifted item:
- Title: {new_item.get("title", "Unknown item")}
- Category: {new_item.get("category", "Unknown category")}
- Brand: {new_item.get("brand") or "Unknown brand"}
- Colors: {", ".join(new_item.get("colors", [])) or "Unknown colors"}
- Style tags: {", ".join(new_item.get("style_tags", [])) or "No tags"}
- Condition: {new_item.get("condition", "Unknown condition")}
- Price: ${new_item.get("price", "Unknown price")}
- Platform: {new_item.get("platform", "Unknown platform")}
""".strip()

    wardrobe_text = "\n".join(
        (
            f"- {item.get('name', 'Unnamed item')}: "
            f"{item.get('category', 'unknown category')}, "
            f"{', '.join(item.get('colors', [])) or 'unknown color'}, "
            f"style tags: {', '.join(item.get('style_tags', [])) or 'none listed'}"
        )
        for item in wardrobe_items
    )

    prompt = f"""
Use the selected second-hand item and the user's wardrobe to suggest 1-2 complete outfits.

{item_details}

User wardrobe:
{wardrobe_text}

Return a concise recommendation with:
- outfit_text
- items_used
- occasion
- style_notes
- missing_piece, if any

Use named pieces from the wardrobe when possible. Keep the advice practical.
""".strip()
    return _call_groq(prompt, temperature=0.75)


def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable fit card for the thrifted find.

    Args:
        outfit: The outfit recommendation from suggest_outfit.
        new_item: The selected listing from search_listings.

    Returns:
        A short fit card string.

    Failure mode:
        If outfit is empty, returns an error message string rather than calling
        the LLM or crashing.
    """
    if not outfit or not outfit.strip():
        return (
            "I found an item and outfit, but could not create the fit card "
            "because the outfit details were missing."
        )

    title = new_item.get("title", "this thrifted find")
    price = new_item.get("price", "unknown price")
    platform = new_item.get("platform", "the resale platform")
    brand = new_item.get("brand") or "unknown brand"
    condition = new_item.get("condition", "unknown condition")

    prompt = f"""
Create a short, shareable fit card for an OOTD post.

Item summary:
- Title: {title}
- Brand: {brand}
- Price: ${price}
- Platform: {platform}
- Condition: {condition}

Outfit summary:
{outfit}

Requirements:
- Write 2-4 sentences.
- Mention the item title, price, condition, and platform naturally.
- Include styling notes from the outfit.
- Sound casual and authentic, not like a product description.
- Vary wording across calls.
""".strip()
    return _call_groq(prompt, temperature=1.05)
