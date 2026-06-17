# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
Searches second-hand listings that match the user’s item description, size, and maximum price.

**Input parameters:**

* `description` (`str`): The item the user wants, such as `"black leather jacket"`.
* `size` (`str`): The requested size, such as `"M"` or `"8"`.
* `max_price` (`float`): The highest price the user will pay.

**What it returns:**
A list of matching listing dictionaries. Each listing includes:

* `id`
* `title`
* `description`
* `size`
* `price`
* `condition`
* `brand`
* `color`
* `category`
* `image_url`
* `listing_url`
* `match_reason`

**What happens if it fails or returns nothing:**
If no listings match, the agent stops and tells the user:

> No listings found for that item, size, and budget. Try increasing your max price, using a broader description, or checking nearby sizes.

It should not call `suggest_outfit` or `create_fit_card`.

---

### Tool 2: suggest_outfit

**What it does:**
Suggests an outfit using the selected second-hand item and the user’s wardrobe.

**Input parameters:**

* `new_item` (`dict`): The listing selected from `search_listings`.
* `wardrobe` (`dict`): The user’s saved clothing items, grouped by category.

**What it returns:**
An outfit dictionary with:

* `outfit_text`
* `items_used`
* `occasion`
* `style_notes`
* `missing_piece`

**What happens if it fails or returns nothing:**
If the wardrobe is empty or no outfit can be suggested, the agent stops and tells the user:

> I found a listing, but I could not create an outfit from your wardrobe. Try adding more wardrobe basics, shoes, or accessories.

It should not call `create_fit_card`.
---

### Tool 3: create_fit_card

**What it does:**
The tool creates a final fit card that summarizes the selected item and the suggested outfit.

**Input parameters:**

<!-- List each parameter, its type, and what it represents -->

* `outfit` (str): The outfit recommendation from `suggest_outfit`.
* `new_item` (dict): The selected listing from `search_listings`.

**What it returns:**

<!-- Describe the return value -->

A fit card dictionary containing the item summary, outfit summary, price, condition, styling notes, and listing URL.

**What happens if it fails or returns nothing:**

<!-- What should the agent do if the outfit data is incomplete? -->

If the outfit data is incomplete, the agent should stop and tell the user that it found an item and outfit, but could not create the fit card because some details were missing. It should return the selected item and outfit suggestion, but no final fit card.

---

### Additional Tools (if any)

You’re right to question that. Since the agent needs the user’s wardrobe, an additional tool **is** useful.

### Additional Tools (if any)

### Tool 4: load_wardrobe

**What it does:**
The tool loads the user’s saved wardrobe so the agent can suggest an outfit using clothing the user already owns.

**Input parameters:**

<!-- List each parameter, its type, and what it represents -->

* `user_id` (str): The unique ID for the current user.

**What it returns:**

<!-- Describe the return value -->

A wardrobe dictionary grouped by clothing category, such as tops, bottoms, shoes, and accessories. Each wardrobe item includes its name, color, category, and style tags.

**What happens if it fails or returns nothing:**

<!-- What should the agent do if no wardrobe is found? -->

If no wardrobe is found, the agent should still show the selected listing, but it should not call `suggest_outfit` or `create_fit_card`. It should tell the user to add wardrobe items or ask for a generic outfit suggestion.


---

## Planning Loop

**How does your agent decide which tool to call next?**
The agent follows this order:

1. Check that `description`, `size`, and `max_price` exist.
2. Call `search_listings`.

   * If no listings are found, stop.
   * Otherwise, save the first listing as `selected_item`.
3. Call `load_wardrobe`.

   * If the wardrobe is empty, stop.
4. Call `suggest_outfit`.

   * If no outfit is suggested, stop.
5. Call `create_fit_card`.

   * Return the final fit card when complete.


---

## State Management

**How does information from one tool get passed to the next?**
The agent stores information in a session dictionary. Each tool reads from and updates this session.

The session tracks:

* `description`
* `size`
* `max_price`
* `search_results`
* `selected_item`
* `wardrobe`
* `outfit_suggestion`
* `fit_card`
* `error`

After `search_listings`, the first result is saved as `selected_item`. Then `selected_item` and `wardrobe` are passed into `suggest_outfit`. Finally, `outfit_suggestion` and `selected_item` are passed into `create_fit_card`.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool            | Failure mode                          | Agent response                                                                                                                                                       |
| --------------- | ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| search_listings | No results match the query            | Tell the user no listings were found and suggest increasing the max price, broadening the description, or checking nearby sizes. Stop before calling the next tools. |
| suggest_outfit  | Wardrobe is empty                     | Tell the user the item was found, but no outfit can be created without wardrobe items. Suggest adding wardrobe items or asking for generic styling.                  |
| create_fit_card | Outfit input is missing or incomplete | Tell the user the item and outfit were found, but the fit card could not be created because details are missing. Return the item and outfit without a final card.    |


---

## Architecture


User input
(description, size, max_price, wardrobe)
    |
    v
Planning Loop
    |
    |-- call search_listings(description, size, max_price)
    |       |
    |       |-- no results --> Error: "No listings found" --> return session
    |       |
    |       v
    |   State: selected_item = first listing
    |
    |-- call suggest_outfit(selected_item, wardrobe)
    |       |
    |       |-- wardrobe empty or no outfit --> Error: "No outfit could be suggested" --> return session
    |       |
    |       v
    |   State: outfit_suggestion = outfit result
    |
    |-- call create_fit_card(outfit_suggestion, selected_item)
            |
            |-- missing outfit data --> Error: "Fit card could not be created" --> return session
            |
            v
        State: fit_card = final card

Final output
Return session with selected_item, outfit_suggestion, and fit_card


---

## AI Tool Plan

**Milestone 3 — Individual tool implementations:**

I will use ChatGPT or Claude to help implement each tool one at a time.

For `search_listings`, I will give the AI tool the Tool 1 spec, including the input parameters, return fields, and failure behavior. I expect it to create a function that filters listings by description, size, and max price. I will verify it by testing one successful search and one search with no matches.

For `suggest_outfit`, I will give the AI tool the Tool 2 spec and the state management section. I expect it to create a function that uses `selected_item` and `wardrobe` to return an outfit suggestion. I will verify it by testing with a full wardrobe and an empty wardrobe.

For `create_fit_card`, I will give the AI tool the Tool 3 spec. I expect it to create a function that turns the selected item and outfit suggestion into a final fit card. I will verify that the output includes the item summary, outfit summary, price, condition, styling notes, and listing URL.

**Milestone 4 — Planning loop and state management:**

I will use ChatGPT or Claude to help implement the planning loop.

I will give the AI tool the Planning Loop section, State Management section, Error Handling table, and Architecture diagram. I expect it to create a `run_agent()` function that calls the tools in order, stores results in the session, and stops early when an error happens.

I will verify the output by checking that:

* `search_listings` runs before `suggest_outfit`
* `suggest_outfit` only runs if a listing was found
* `create_fit_card` only runs if an outfit was created
* each tool result is saved in the session
* error cases return early with a clear message


---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
FitFindr first calls search_listings using the user’s requested item and filters. For this query, it would search for a vintage graphic tee with a maximum price of $30. If the user provided a size, color, brand, platform, or condition, those filters would also be passed into the tool.

Example tool call:
search_listings("vintage graphic tee", max_price=30.0)
**Step 2:**
If matching listings are found, FitFindr reviews the returned listings and selects the strongest match based on relevance to the user’s request. For example, it might choose a listing like "Faded Band Tee — $22, Depop, Good condition.

FitFindr then calls suggest_outfit using the selected listing as the new item and the user’s wardrobe as input. This tool recommends how to style the new item with clothing the user already owns, such as baggy jeans and chunky sneakers.

Example tool call:
suggest_outfit(new_item=<selected listing>, wardrobe=<user wardrobe>)

**Step 3:**
After receiving the outfit suggestion, FitFindr calls create_fit_card to turn the outfit into a short, shareable fit description or caption.

Example tool call:
create_fit_card(outfit=<outfit suggestion>, new_item=<selected listing>)
**Final output to user:**
FitFindr returns the best listing, explains how to style it with the user’s wardrobe, and includes a fit card. For example, it might say: "I found a faded band tee for $22 on Depop in good condition. Pair it with your wide-leg jeans and chunky sneakers for a relaxed 90s-inspired look. Fit card: thrifted this faded band tee off Depop for $22 and honestly it was made for my wide-legs."

Error path:
If search_listings does not return any matching listings, FitFindr should not continue to suggest_outfit or create_fit_card. Instead, it should tell the user that no results matched their request and suggest broadening the search, such as increasing the budget, removing a size filter, or using a more general keyword.