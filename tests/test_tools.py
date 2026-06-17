from utils.data_loader import get_example_wardrobe
from tools import create_fit_card, search_listings, suggest_outfit


def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)

    assert isinstance(results, list)
    assert len(results) > 0
    assert all("match_reason" in item for item in results)


def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)

    assert results == []


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)

    assert all(item["price"] <= 10 for item in results)


def test_search_size_filter():
    results = search_listings("track jacket", size="M", max_price=100)

    assert results
    assert all("m" in item["size"].lower() for item in results)


def test_suggest_outfit_calls_llm(monkeypatch):
    calls = []

    def fake_call_groq(prompt, temperature=0.7):
        calls.append({"prompt": prompt, "temperature": temperature})
        return "outfit_text: Wear it with baggy jeans and chunky sneakers."

    monkeypatch.setattr("tools._call_groq", fake_call_groq)
    new_item = search_listings("vintage graphic tee", max_price=50)[0]

    result = suggest_outfit(new_item, get_example_wardrobe())

    assert "baggy jeans" in result
    assert len(calls) == 1
    assert "User wardrobe:" in calls[0]["prompt"]


def test_suggest_outfit_empty_wardrobe_returns_general_advice(monkeypatch):
    calls = []

    def fake_call_groq(prompt, temperature=0.7):
        calls.append({"prompt": prompt, "temperature": temperature})
        return "Try it with straight-leg jeans, simple sneakers, and a cropped jacket."

    monkeypatch.setattr("tools._call_groq", fake_call_groq)
    new_item = search_listings("vintage graphic tee", max_price=50)[0]

    result = suggest_outfit(new_item, {"items": []})

    assert "straight-leg jeans" in result
    assert len(calls) == 1
    assert "wardrobe is empty" in calls[0]["prompt"]


def test_create_fit_card_calls_llm(monkeypatch):
    calls = []

    def fake_call_groq(prompt, temperature=0.7):
        calls.append({"prompt": prompt, "temperature": temperature})
        return "Fit card: thrifted graphic tee with jeans and sneakers."

    monkeypatch.setattr("tools._call_groq", fake_call_groq)
    new_item = search_listings("vintage graphic tee", max_price=50)[0]

    result = create_fit_card("Pair it with baggy jeans and chunky sneakers.", new_item)

    assert "Fit card:" in result
    assert len(calls) == 1
    assert calls[0]["temperature"] >= 0.95
    assert new_item["title"] in calls[0]["prompt"]


def test_create_fit_card_empty_outfit_returns_error():
    new_item = search_listings("vintage graphic tee", max_price=50)[0]

    result = create_fit_card("", new_item)

    assert "could not create the fit card" in result
