from app import handle_query


def test_handle_query_empty_input():
    listing_text, outfit, fit_card = handle_query("", "Example wardrobe")

    assert "Please enter" in listing_text
    assert outfit == ""
    assert fit_card == ""


def test_handle_query_error_session(monkeypatch):
    def fake_run_agent(query, wardrobe):
        return {"error": "No listings found.", "selected_item": None}

    monkeypatch.setattr("app.run_agent", fake_run_agent)

    listing_text, outfit, fit_card = handle_query("designer ballgown under $5", "Example wardrobe")

    assert listing_text == "No listings found."
    assert outfit == ""
    assert fit_card == ""


def test_handle_query_success_session(monkeypatch):
    def fake_run_agent(query, wardrobe):
        return {
            "error": None,
            "selected_item": {
                "title": "Vintage Graphic Tee",
                "brand": None,
                "price": 24.0,
                "size": "L",
                "condition": "good",
                "platform": "depop",
                "colors": ["black"],
                "style_tags": ["vintage", "graphic tee"],
                "description": "Soft faded graphic tee.",
                "match_reason": "Matched vintage, graphic, tee and fits the price/size filters.",
            },
            "outfit_suggestion": "Wear it with jeans.",
            "fit_card": "Fit card text.",
        }

    monkeypatch.setattr("app.run_agent", fake_run_agent)

    listing_text, outfit, fit_card = handle_query("vintage graphic tee", "Example wardrobe")

    assert "Vintage Graphic Tee" in listing_text
    assert "Why this matched" in listing_text
    assert outfit == "Wear it with jeans."
    assert fit_card == "Fit card text."
