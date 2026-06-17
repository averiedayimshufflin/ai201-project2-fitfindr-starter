"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import search_listings, suggest_outfit, create_fit_card


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "description": None,         # parsed item description
        "size": None,                # parsed size filter
        "max_price": None,           # parsed price ceiling
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def _parse_query(query: str) -> dict:
    """
    Extract search parameters from a natural-language query.

    Milestone 4 only needs lightweight parsing, so this stays deterministic:
    regex extracts max price and size, then those phrases are removed from the
    remaining text to create the listing search description.
    """
    cleaned = query.strip()

    price_match = re.search(
        r"(?:under|below|less than|max(?:imum)?|budget(?: of)?|up to)\s*\$?(\d+(?:\.\d{1,2})?)",
        cleaned,
        flags=re.IGNORECASE,
    )
    max_price = float(price_match.group(1)) if price_match else None

    size_match = re.search(
        r"(?:in\s+)?(?:size|sz)\s+([a-z0-9./-]+)",
        cleaned,
        flags=re.IGNORECASE,
    )
    size = size_match.group(1).upper() if size_match else None

    description = re.sub(
        r"(?:under|below|less than|max(?:imum)?|budget(?: of)?|up to)\s*\$?\d+(?:\.\d{1,2})?",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    description = re.sub(
        r"(?:in\s+)?(?:size|sz)\s+[a-z0-9./-]+",
        " ",
        description,
        flags=re.IGNORECASE,
    )
    description = re.split(
        r"\b(?:i mostly wear|what's out there|how would i style|how do i style)\b",
        description,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    description = re.sub(
        r"\b(?:i'm|im|i am|looking for|searching for|find me|show me|want|need|a|an)\b",
        " ",
        description,
        flags=re.IGNORECASE,
    )
    description = re.sub(r"[^a-zA-Z0-9' -]+", " ", description)
    description = re.sub(r"\s+", " ", description).strip()

    return {
        "description": description or query.strip(),
        "size": size,
        "max_price": max_price,
    }


def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.

    TODO — implement this function using the planning loop you designed in planning.md:

        Step 1: Initialize the session with _new_session().

        Step 2: Parse the user's query to extract a description, size, and
                max_price. You can use regex, string splitting, or ask the LLM
                to parse it — document your choice in planning.md.
                Store the result in session["parsed"].

        Step 3: Call search_listings() with the parsed parameters.
                Store results in session["search_results"].
                If no results: set session["error"] to a helpful message and
                return the session early. Do NOT proceed to suggest_outfit
                with empty input.

        Step 4: Select the item to use (e.g., the top result).
                Store it in session["selected_item"].

        Step 5: Call suggest_outfit() with the selected item and wardrobe.
                Store the result in session["outfit_suggestion"].

        Step 6: Call create_fit_card() with the outfit suggestion and selected item.
                Store the result in session["fit_card"].

        Step 7: Return the session.

    Before writing code, complete the Planning Loop and State Management sections
    of planning.md — your implementation should match what you described there.
    """
    session = _new_session(query, wardrobe)
    parsed = _parse_query(query)
    session["parsed"] = parsed
    session["description"] = parsed["description"]
    session["size"] = parsed["size"]
    session["max_price"] = parsed["max_price"]

    results = search_listings(
        description=parsed["description"],
        size=parsed["size"],
        max_price=parsed["max_price"],
    )
    session["search_results"] = results

    if not results:
        session["error"] = (
            "No listings found for that item, size, and budget. Try increasing "
            "your max price, using a broader description, or checking nearby sizes."
        )
        return session

    selected_item = results[0]
    session["selected_item"] = selected_item

    wardrobe_items = wardrobe.get("items", []) if isinstance(wardrobe, dict) else []
    if not wardrobe_items:
        session["error"] = (
            "I found a listing, but I could not create an outfit from your wardrobe. "
            "Try adding more wardrobe basics, shoes, or accessories."
        )
        return session

    outfit = suggest_outfit(selected_item, wardrobe)
    session["outfit_suggestion"] = outfit

    if not outfit or "could not create an outfit" in outfit.lower():
        session["error"] = (
            "I found a listing, but I could not create an outfit from your wardrobe. "
            "Try adding more wardrobe basics, shoes, or accessories."
        )
        return session

    fit_card = create_fit_card(outfit, selected_item)
    session["fit_card"] = fit_card

    if not fit_card or "could not create the fit card" in fit_card.lower():
        session["error"] = (
            "I found an item and outfit, but could not create the fit card because "
            "some details were missing."
        )
        session["fit_card"] = None

    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
    print(f"Fit card: {session2['fit_card']}")
