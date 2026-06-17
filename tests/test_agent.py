from agent import run_agent


def test_run_agent_passes_state_between_tools(monkeypatch):
    selected = {"id": "lst_test", "title": "Test Tee", "price": 20}
    calls = []

    def fake_search_listings(description, size, max_price):
        calls.append(("search", description, size, max_price))
        return [selected]

    def fake_suggest_outfit(new_item, wardrobe):
        calls.append(("suggest", new_item, wardrobe))
        return "Wear Test Tee with baggy jeans."

    def fake_create_fit_card(outfit, new_item):
        calls.append(("fit_card", outfit, new_item))
        return "Fit card for Test Tee."

    monkeypatch.setattr("agent.search_listings", fake_search_listings)
    monkeypatch.setattr("agent.suggest_outfit", fake_suggest_outfit)
    monkeypatch.setattr("agent.create_fit_card", fake_create_fit_card)

    wardrobe = {"items": [{"name": "Baggy jeans"}]}
    session = run_agent("looking for a vintage graphic tee under $30", wardrobe)

    assert session["error"] is None
    assert session["selected_item"] is selected
    assert session["outfit_suggestion"] == "Wear Test Tee with baggy jeans."
    assert session["fit_card"] == "Fit card for Test Tee."
    assert calls == [
        ("search", "vintage graphic tee", None, 30.0),
        ("suggest", selected, wardrobe),
        ("fit_card", "Wear Test Tee with baggy jeans.", selected),
    ]


def test_run_agent_no_results_stops_before_llm_tools(monkeypatch):
    calls = []

    def fake_search_listings(description, size, max_price):
        calls.append(("search", description, size, max_price))
        return []

    def fake_suggest_outfit(new_item, wardrobe):
        calls.append(("suggest", new_item, wardrobe))
        return "This should not run."

    def fake_create_fit_card(outfit, new_item):
        calls.append(("fit_card", outfit, new_item))
        return "This should not run."

    monkeypatch.setattr("agent.search_listings", fake_search_listings)
    monkeypatch.setattr("agent.suggest_outfit", fake_suggest_outfit)
    monkeypatch.setattr("agent.create_fit_card", fake_create_fit_card)

    session = run_agent("designer ballgown size XXS under $5", {"items": [{"name": "Jeans"}]})

    assert "No listings found" in session["error"]
    assert session["search_results"] == []
    assert session["selected_item"] is None
    assert session["outfit_suggestion"] is None
    assert session["fit_card"] is None
    assert calls == [("search", "designer ballgown", "XXS", 5.0)]


def test_run_agent_empty_wardrobe_stops_before_outfit(monkeypatch):
    selected = {"id": "lst_test", "title": "Test Tee", "price": 20}
    calls = []

    def fake_search_listings(description, size, max_price):
        calls.append(("search", description, size, max_price))
        return [selected]

    def fake_suggest_outfit(new_item, wardrobe):
        calls.append(("suggest", new_item, wardrobe))
        return "This should not run."

    monkeypatch.setattr("agent.search_listings", fake_search_listings)
    monkeypatch.setattr("agent.suggest_outfit", fake_suggest_outfit)

    session = run_agent("vintage graphic tee under $30", {"items": []})

    assert "could not create an outfit" in session["error"]
    assert session["selected_item"] is selected
    assert session["fit_card"] is None
    assert calls == [("search", "vintage graphic tee", None, 30.0)]
