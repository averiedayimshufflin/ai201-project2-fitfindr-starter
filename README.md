# FitFindr

FitFindr is a small planning-loop agent for secondhand shopping. It searches a mock resale dataset, chooses the strongest matching item, suggests an outfit using the user's wardrobe, and turns that result into a short shareable fit card.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```text
GROQ_API_KEY=your_key_here
```

Run the tests:

```bash
python -m pytest tests/
```

Run the Gradio app:

```bash
python app.py
```

Then open the URL printed in the terminal, usually `http://127.0.0.1:7860`.

## Tool Inventory

### `search_listings(description: str, size: str | None = None, max_price: float | None = None) -> list[dict]`

Purpose: searches the mock secondhand listings loaded by `utils.data_loader.load_listings()`.

Inputs:
- `description`: item keywords, such as `"vintage graphic tee"`.
- `size`: optional size filter, such as `"M"`, `"XXS"`, or `None`.
- `max_price`: optional price ceiling, such as `30.0` or `None`.

Output: a list of matching listing dictionaries sorted by relevance. Each result includes the original listing fields plus `match_score` and `match_reason`.

Failure behavior: returns `[]` when nothing matches. It does not raise an exception for normal no-result searches.

### `suggest_outfit(new_item: dict, wardrobe: dict) -> str`

Purpose: asks Groq `llama-3.3-70b-versatile` to style the selected listing.

Inputs:
- `new_item`: the selected listing dictionary from `search_listings`.
- `wardrobe`: a wardrobe dictionary with an `items` list.

Output: a non-empty outfit suggestion string. With a populated wardrobe, the prompt asks the LLM to use named pieces from the user's closet. With an empty wardrobe, the tool returns general styling advice using common basics instead of crashing.

Failure behavior: handles `{"items": []}` by returning useful general styling advice.

### `create_fit_card(outfit: str, new_item: dict) -> str`

Purpose: asks Groq to turn the selected item and outfit suggestion into a short shareable fit card.

Inputs:
- `outfit`: the outfit recommendation string from `suggest_outfit`.
- `new_item`: the selected listing dictionary from `search_listings`.

Output: a 2-4 sentence fit-card string mentioning the item, price, condition, platform, and styling vibe.

Failure behavior: if `outfit` is empty or whitespace, returns a descriptive error string instead of calling the LLM or raising an exception.

## Planning Loop

The planning loop lives in `run_agent(query: str, wardrobe: dict)` in `agent.py`. It does not call all three tools blindly. It makes a decision after each step based on the state returned by the previous tool.

1. Create a fresh `session` dictionary with the original query, wardrobe, tool outputs, and `error`.
2. Parse the query with a deterministic regex parser:
   - Extracts `max_price` from phrases like `"under $30"`.
   - Extracts `size` from phrases like `"size M"`.
   - Removes those filter phrases to produce the item `description`.
3. Call `search_listings(description, size, max_price)`.
4. If search returns `[]`, store an actionable error and stop. The agent does not call `suggest_outfit` or `create_fit_card`.
5. If results exist, store the first result as `session["selected_item"]`.
6. If the wardrobe is empty, store an actionable wardrobe error and stop before creating a fit card.
7. Call `suggest_outfit(selected_item, wardrobe)` and store the result in `session["outfit_suggestion"]`.
8. If the outfit result is missing or unusable, store an error and stop.
9. Call `create_fit_card(outfit_suggestion, selected_item)` and store the result in `session["fit_card"]`.
10. Return the final session.

The key decision point is step 4: no search results means the rest of the pipeline is skipped. This keeps the agent from styling an item that was never found.

## State Management

The session dictionary is the single source of truth for one user interaction. It stores:

- `query`: the original user query.
- `parsed`: a dictionary containing `description`, `size`, and `max_price`.
- `description`, `size`, `max_price`: top-level copies of the parsed search values for easy inspection.
- `search_results`: all matching listings returned by `search_listings`.
- `selected_item`: the first listing from `search_results`.
- `wardrobe`: the wardrobe passed into the agent.
- `outfit_suggestion`: the exact string returned by `suggest_outfit`.
- `fit_card`: the exact string returned by `create_fit_card`, or `None` if the agent stopped early.
- `error`: `None` on success, otherwise the message explaining why the loop stopped.

I verified state flow with an instrumented run. `session["selected_item"]` was the same dictionary object passed into `suggest_outfit` and `create_fit_card`, and `session["outfit_suggestion"]` was the same string passed into `create_fit_card`.

## Error Handling

| Tool | Failure mode | Agent or tool response | Tested example |
| --- | --- | --- | --- |
| `search_listings` | No listings match the description, size, and budget | Returns `[]`. The full agent stops and tells the user to increase price, broaden the description, or check nearby sizes. | `search_listings("designer ballgown", size="XXS", max_price=5)` returned `[]`. |
| `suggest_outfit` | Wardrobe is empty | Direct tool call returns general styling advice. In the full planning loop, the agent stops before fit-card creation and asks the user to add wardrobe basics, shoes, or accessories. | `suggest_outfit(results[0], get_empty_wardrobe())` returned general outfit ideas. |
| `create_fit_card` | Outfit string is empty | Returns a descriptive error string instead of raising an exception. | `create_fit_card("", results[0])` returned `"I found an item and outfit, but could not create the fit card because the outfit details were missing."` |

I saved a triggered failure screenshot for the demo at `demo_artifacts/failure_search_no_results.png`.

## Complete Interaction Walkthrough

User query:

```text
vintage graphic tee under $30
```

Step 1: parse query.

```python
{"description": "vintage graphic tee", "size": None, "max_price": 30.0}
```

Step 2: call search.

```python
search_listings("vintage graphic tee", size=None, max_price=30.0)
```

The search returns matching listings. The top result is saved as `session["selected_item"]`, for example `"Y2K Baby Tee - Butterfly Print"`.

Step 3: call outfit suggestion.

```python
suggest_outfit(session["selected_item"], session["wardrobe"])
```

The returned outfit string is saved as `session["outfit_suggestion"]`.

Step 4: call fit-card creation.

```python
create_fit_card(session["outfit_suggestion"], session["selected_item"])
```

The returned caption is saved as `session["fit_card"]`.

Final successful session has `error == None` and populated values for `selected_item`, `outfit_suggestion`, and `fit_card`.

## App Verification

I ran the app with:

```bash
python app.py
```

The live Gradio server was reachable at `http://127.0.0.1:7860`. I submitted `vintage graphic tee under $30` with the example wardrobe through the Gradio endpoint and confirmed:

- Top listing panel populated.
- Outfit idea panel populated.
- Fit card panel populated.

The top listing was `"Y2K Baby Tee - Butterfly Print"`.

## AI Usage

### Instance 1: Individual tool implementation

Input I gave the AI tool: the Tool 1, Tool 2, and Tool 3 spec blocks from `planning.md`, one tool at a time. Each block included what the tool does, input parameters, return value, and failure behavior.

What it produced: first drafts for `search_listings`, `suggest_outfit`, and `create_fit_card`.

What I changed before using it:
- Removed an invalid Markdown code fence that had been placed in `tools.py`.
- Ensured `search_listings` used `load_listings()` instead of reading the JSON file directly.
- Changed the Groq model to `llama-3.3-70b-versatile`.
- Added explicit failure handling for empty search results and empty fit-card input.
- Increased fit-card temperature so repeated captions vary.

### Instance 2: Planning loop implementation

Input I gave the AI tool: the Planning Loop section, State Management section, Error Handling table, and Architecture diagram from `planning.md`.

What it produced: a branch-based `run_agent()` structure that initialized session state, searched listings first, selected the top item, then passed state into outfit and fit-card tools.

What I changed before using it:
- Added a deterministic regex parser instead of an LLM parser so query extraction is transparent and testable.
- Added early returns so `suggest_outfit` is not called when `search_listings` returns `[]`.
- Added tests that monkeypatch tools and prove state is passed forward exactly.
- Added Gradio `handle_query()` mapping so the session fields populate the three output panels.

### Instance 3: Failure-mode testing

Input I gave the AI tool: the milestone instructions for deliberately triggering failures, including the exact terminal commands for no-results search, empty wardrobe, and empty fit-card input.

What it produced: a checklist of failure cases to run and suggested assertions for pytest.

What I changed before using it:
- Updated `suggest_outfit` so the direct empty-wardrobe tool call returns general styling advice, matching the milestone requirement.
- Kept the planning loop stricter: the full agent still stops on an empty wardrobe before creating a fit card.
- Added and reran tests to confirm the changed behavior.

## Spec Reflection

One way `planning.md` helped during implementation: it forced the agent loop to be written as a sequence of decisions instead of just a sequence of function calls. The no-results branch was already specified, so it was clear that `run_agent()` needed to stop before outfit generation when search failed.

One divergence from the original spec: the spec described some outputs as dictionaries, but the starter function signatures and app panels expected strings for `suggest_outfit` and `create_fit_card`. I kept the actual code aligned with the provided stubs and UI, then made the strings structured enough for a user to read clearly.
