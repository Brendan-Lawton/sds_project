# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions

import json
from datetime import date
from typing import Any, Text, Dict, List, Optional

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher

from actions.services.menu_service import MenuService, MenuFetchError, MenuParseError, MenuDTO


CANTEENS: Dict[str, str] = {
    # Name-based
    "hardenbergstrasse": "1004",
    "hardenberg": "1004",
    "marchstrasse": "1010",
    "march": "1010",
    "vegan": "2456",
    "veggie": "2456",
    # Index-based
    "1": "1004",
    "one": "1004",
    "first": "1004",
    "canteen 1": "1004",
    "mensa 1": "1004",
    "2": "1010",
    "two": "1010",
    "second": "1010",
    "canteen 2": "1010",
    "mensa 2": "1010",
    "3": "2456",
    "three": "2456",
    "third": "2456",
    "canteen 3": "2456",
    "mensa 3": "2456",
}

CANTEEN_NAMES: Dict[str, str] = {
    "1004": "Hardenbergstrasse",
    "1010": "Marchstrasse",
    "2456": "Vegan Mensa",
}


def resolve_canteen(canteen_input: Optional[str]) -> Optional[str]:
    """Resolve canteen name/alias to canteen ID."""
    if not canteen_input:
        return None
    canteen_lower = canteen_input.lower().strip()
    if canteen_lower in CANTEENS:
        return CANTEENS[canteen_lower]
    if canteen_lower in CANTEEN_NAMES:
        return canteen_lower
    return None


PRICE_CATEGORY_INDEX = {
    "student": 0,
    "worker": 1,
    "guest": 2,
}


def parse_price(price_str: Optional[str], category: str = "student") -> Optional[float]:
    """Extract price from price string like '€ 1,95/2,15/2,35' based on category.

    The price string contains 3 values separated by '/':
    index 0 = student, index 1 = worker, index 2 = guest.
    """
    if not price_str:
        return None
    try:
        price_str = price_str.replace("€", "").strip()
        parts = price_str.split("/")
        idx = PRICE_CATEGORY_INDEX.get(category, 0)
        if idx >= len(parts):
            idx = 0
        price_part = parts[idx].strip()
        return float(price_part.replace(",", "."))
    except (ValueError, IndexError):
        return None


# Dietary classification codes
# Meat additives: 2 = Pork, 14 = Contains partially finely minced meat
# Seafood allergens: 22 = Crustaceans, 24 = Fish, 34 = Mollusks
MEAT_ADDITIVE_CODES = {"2", "14"}
SEAFOOD_ALLERGEN_CODES = {"22", "24", "34"}
EGG_ALLERGEN_CODE = "23"
DAIRY_ALLERGEN_CODE = "30"
NUT_ALLERGEN_CODES = {"25", "26", "26a", "26b", "26c", "26d", "26e", "26f", "26g", "26h"}


def is_vegetarian(item) -> bool:
    """Check if item is vegetarian (no meat/seafood)."""
    all_codes = set(item.allergen_codes + item.additive_codes)
    has_meat = bool(all_codes & MEAT_ADDITIVE_CODES)
    has_seafood = bool(all_codes & SEAFOOD_ALLERGEN_CODES)
    return not has_meat and not has_seafood


def is_vegan(item) -> bool:
    """Check if item is vegan (vegetarian + no eggs/dairy)."""
    if not is_vegetarian(item):
        return False
    all_codes = set(item.allergen_codes + item.additive_codes)
    has_eggs = EGG_ALLERGEN_CODE in all_codes
    has_dairy = DAIRY_ALLERGEN_CODE in all_codes
    return not has_eggs and not has_dairy


def is_nut_free(item) -> bool:
    """Check if item is nut-free (no peanuts or tree nuts)."""
    all_codes = set(item.allergen_codes + item.additive_codes)
    return not bool(all_codes & NUT_ALLERGEN_CODES)


def format_category_items(category_name: str, menu: MenuDTO) -> str:
    """Format items from a specific category."""
    category = next((c for c in menu.categories if c.name.lower() == category_name.lower()), None)
    if not category or not category.items:
        return f"No items found in category '{category_name}'."

    lines = [f"**{category.name}**\n"]
    for item in category.items:
        price_str = f" - {item.price}" if item.price else ""
        lines.append(f"• {item.name}{price_str}")
        if item.allergens:
            lines.append(f"  Allergens: {', '.join(item.allergens)}")
        if item.additives:
            lines.append(f"  Additives: {', '.join(item.additives)}")

    return "\n".join(lines)


def serialize_menu(menu: MenuDTO) -> str:
    """Serialize menu to JSON string for storage in slot."""
    return json.dumps({
        "date": menu.date,
        "canteen_id": menu.canteen_id,
        "categories": [
            {
                "name": cat.name,
                "items": [
                    {
                        "name": item.name,
                        "price": item.price,
                        "allergens": item.allergens,
                        "additives": item.additives,
                        "allergen_codes": item.allergen_codes,
                        "additive_codes": item.additive_codes,
                    }
                    for item in cat.items
                ]
            }
            for cat in menu.categories
        ]
    })


def deserialize_menu(menu_json: str) -> Optional[MenuDTO]:
    """Deserialize menu from JSON string."""
    if not menu_json:
        return None
    try:
        from actions.services.menu_service import MenuItem, MenuCategory
        data = json.loads(menu_json)
        categories = [
            MenuCategory(
                name=cat["name"],
                items=[
                    MenuItem(
                        name=item["name"],
                        price=item["price"],
                        allergens=item["allergens"],
                        additives=item["additives"],
                        allergen_codes=item.get("allergen_codes", []),
                        additive_codes=item.get("additive_codes", []),
                    )
                    for item in cat["items"]
                ]
            )
            for cat in data["categories"]
        ]
        return MenuDTO(
            date=data["date"],
            canteen_id=data["canteen_id"],
            categories=categories,
        )
    except (json.JSONDecodeError, KeyError):
        return None


class ActionCheckMenu(Action):

    def name(self) -> Text:
        return "action_check_menu"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        canteen_slot = tracker.get_slot("canteen")
        date_slot = tracker.get_slot("menu_date")

        canteen_id = resolve_canteen(canteen_slot)
        if not canteen_id:
            dispatcher.utter_message(
                text="Which canteen would you like to check? "
                "Available options: Hardenbergstrasse, Marchstrasse, or Vegan."
            )
            return [SlotSet("awaiting_canteen", True)]

        menu_date = date_slot if date_slot else date.today().isoformat()
        canteen_name = CANTEEN_NAMES.get(canteen_id, canteen_id)

        service = MenuService()
        try:
            menu = service.get_menu(canteen_id, menu_date)
            if not menu.categories or all(not cat.items for cat in menu.categories):
                dispatcher.utter_message(
                    text=f"No menu available for {canteen_name} on {menu_date}."
                )
                return [SlotSet("awaiting_canteen", False)]

            category_names = [cat.name for cat in menu.categories if cat.items]
            categories_list = ", ".join(category_names)

            dispatcher.utter_message(
                text=f"Menu for {canteen_name} on {menu_date} has the following categories:\n"
                f"{categories_list}\n\n"
                "Which category would you like to see?\n"
                "Alternatively, you can say suggest a meal for a specific price (e.g., \"meal for 5 euros\") or ask for dietary options (e.g., \"vegan options\")."
            )

            return [
                SlotSet("awaiting_canteen", False),
                SlotSet("awaiting_category", True),
                SlotSet("available_categories", category_names),
                SlotSet("cached_menu", serialize_menu(menu)),
            ]

        except MenuFetchError as e:
            dispatcher.utter_message(text=f"Sorry, I couldn't fetch the menu: {str(e)}")
        except MenuParseError as e:
            dispatcher.utter_message(text=f"Sorry, I couldn't read the menu: {str(e)}")

        return [SlotSet("awaiting_canteen", False)]


class ActionShowCategory(Action):

    def name(self) -> Text:
        return "action_show_category"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        category_entity = next(tracker.get_latest_entity_values("category"), None)
        user_message = tracker.latest_message.get("text", "").lower()
        available_categories = tracker.get_slot("available_categories") or []
        cached_menu_json = tracker.get_slot("cached_menu")

        selected_category = category_entity
        if not selected_category:
            for cat in available_categories:
                if cat.lower() in user_message:
                    selected_category = cat
                    break

        if not selected_category:
            categories_list = ", ".join(available_categories) if available_categories else "None available"
            dispatcher.utter_message(
                text=f"I didn't recognize that category. "
                f"Available categories are: {categories_list}"
            )
            return []

        menu = deserialize_menu(cached_menu_json)
        if not menu:
            dispatcher.utter_message(
                text="Sorry, I lost the menu data. Please ask for the menu again."
            )
            return [
                SlotSet("awaiting_category", False),
                SlotSet("cached_menu", None),
                SlotSet("available_categories", None),
            ]

        formatted = format_category_items(selected_category, menu)
        dispatcher.utter_message(text=formatted)

        dispatcher.utter_message(
            text="Would you like to see another category? "
            f"Available: {', '.join(available_categories)}"
        )

        return [SlotSet("menu_category", selected_category)]


class ActionSetCanteen(Action):

    def name(self) -> Text:
        return "action_set_canteen"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        canteen_entity = next(tracker.get_latest_entity_values("canteen"), None)
        user_message = tracker.latest_message.get("text", "").lower()

        canteen_value = canteen_entity
        if not canteen_value:
            for name in CANTEENS:
                if name in user_message:
                    canteen_value = name
                    break

        if canteen_value:
            canteen_id = resolve_canteen(canteen_value)
            if canteen_id:
                canteen_name = CANTEEN_NAMES.get(canteen_id, canteen_value)
                dispatcher.utter_message(text=f"Got it, checking {canteen_name}.")
                return [
                    SlotSet("canteen", canteen_value),
                    SlotSet("awaiting_canteen", False),
                ]

        dispatcher.utter_message(
            text="I didn't recognize that canteen. "
            "Please choose from: Hardenbergstrasse, Marchstrasse, or Vegan."
        )
        return []


class ActionSetMenuDate(Action):

    def name(self) -> Text:
        return "action_set_menu_date"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        date_entity = next(tracker.get_latest_entity_values("date"), None)

        if date_entity:
            dispatcher.utter_message(text=f"Setting menu date to {date_entity}.")
            return [SlotSet("menu_date", date_entity)]

        dispatcher.utter_message(
            text="Please provide a date in YYYY-MM-DD format (e.g., 2026-01-22)."
        )
        return []


class ActionResetMenuSlots(Action):

    def name(self) -> Text:
        return "action_reset_menu_slots"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        return [
            SlotSet("canteen", None),
            SlotSet("menu_date", None),
            SlotSet("menu_category", None),
            SlotSet("awaiting_canteen", False),
            SlotSet("awaiting_category", False),
            SlotSet("available_categories", None),
            SlotSet("cached_menu", None),
            SlotSet("dietary_restriction", None),
            SlotSet("budget", None),
            SlotSet("price_category", "student"),
        ]


class ActionFilterDietary(Action):

    def name(self) -> Text:
        return "action_filter_dietary"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        dietary_restriction = tracker.get_slot("dietary_restriction")
        cached_menu_json = tracker.get_slot("cached_menu")
        price_category = tracker.get_slot("price_category") or "student"

        if not dietary_restriction:
            # Try to extract from message
            message = tracker.latest_message.get("text", "").lower()
            if "vegan" in message:
                dietary_restriction = "vegan"
            elif "vegetarian" in message:
                dietary_restriction = "vegetarian"
            elif "nut-free" in message or "nut free" in message or "no nuts" in message:
                dietary_restriction = "nut-free"

        if not dietary_restriction:
            dispatcher.utter_message(
                text="What dietary restriction would you like to filter by? "
                "Options: vegan, vegetarian, or nut-free."
            )
            return []

        if not cached_menu_json:
            dispatcher.utter_message(
                text="Please select a canteen first so I can filter the menu."
            )
            return [SlotSet("dietary_restriction", dietary_restriction)]

        menu = deserialize_menu(cached_menu_json)
        if not menu:
            dispatcher.utter_message(
                text="Sorry, I lost the menu data. Please ask for the menu again."
            )
            return [SlotSet("dietary_restriction", dietary_restriction)]

        # Select filter function based on restriction
        filter_funcs = {
            "vegan": is_vegan,
            "vegetarian": is_vegetarian,
            "nut-free": is_nut_free,
        }
        filter_func = filter_funcs.get(dietary_restriction.lower())
        if not filter_func:
            dispatcher.utter_message(
                text=f"I don't recognize '{dietary_restriction}'. "
                "Please choose from: vegan, vegetarian, or nut-free."
            )
            return []

        # Filter items across all categories
        canteen_name = CANTEEN_NAMES.get(menu.canteen_id, menu.canteen_id)
        lines = [f"**{dietary_restriction.capitalize()} options at {canteen_name}:**\n"]
        found_items = False

        for category in menu.categories:
            matching_items = [item for item in category.items if filter_func(item)]
            if matching_items:
                found_items = True
                lines.append(f"\n**{category.name}**")
                for item in matching_items:
                    price = parse_price(item.price, price_category)
                    price_str = f" - {price}€" if price else ""
                    lines.append(f"• {item.name}{price_str}")

        if not found_items:
            dispatcher.utter_message(
                text=f"Sorry, I couldn't find any {dietary_restriction} options in the current menu."
            )
        else:
            dispatcher.utter_message(text="\n".join(lines))

        return [SlotSet("dietary_restriction", dietary_restriction)]


class ActionFilterByPrice(Action):

    def name(self) -> Text:
        return "action_filter_by_price"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        budget_slot = tracker.get_slot("budget")
        cached_menu_json = tracker.get_slot("cached_menu")
        price_category = tracker.get_slot("price_category") or "student"

        # Convert budget to float
        budget = None
        if budget_slot is not None:
            try:
                budget = float(str(budget_slot).replace(",", "."))
            except ValueError:
                pass

        # Try to extract budget from message if not in slot
        if budget is None:
            message = tracker.latest_message.get("text", "")
            import re
            # Match patterns like "3 euros", "3.50", "3,50", "€3"
            match = re.search(r'(\d+[.,]?\d*)\s*(?:euros?|€)?', message)
            if match:
                try:
                    budget = float(match.group(1).replace(",", "."))
                except ValueError:
                    pass

        if budget is None:
            dispatcher.utter_message(
                text="What's your budget? Please provide an amount in euros."
            )
            return []

        if not cached_menu_json:
            dispatcher.utter_message(
                text="Please select a canteen first so I can filter by price."
            )
            return [SlotSet("budget", budget)]

        menu = deserialize_menu(cached_menu_json)
        if not menu:
            dispatcher.utter_message(
                text="Sorry, I lost the menu data. Please ask for the menu again."
            )
            return [SlotSet("budget", budget)]

        canteen_name = CANTEEN_NAMES.get(menu.canteen_id, menu.canteen_id)
        lines = [f"**Items under €{budget:.2f} at {canteen_name} ({price_category} price):**\n"]
        found_items = False

        for category in menu.categories:
            affordable_items = []
            for item in category.items:
                price = parse_price(item.price, price_category)
                if price is not None and price <= budget:
                    affordable_items.append((item, price))

            if affordable_items:
                found_items = True
                lines.append(f"\n**{category.name}**")
                # Sort by price ascending
                affordable_items.sort(key=lambda x: x[1])
                for item, price in affordable_items:
                    lines.append(f"• {item.name} - €{price:.2f}")

        if not found_items:
            dispatcher.utter_message(
                text=f"Sorry, I couldn't find any items under €{budget:.2f}."
            )
        else:
            dispatcher.utter_message(text="\n".join(lines))

        return [SlotSet("budget", budget)]


class ActionSuggestBudgetMeal(Action):

    def name(self) -> Text:
        return "action_suggest_budget_meal"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        budget_slot = tracker.get_slot("budget")
        cached_menu_json = tracker.get_slot("cached_menu")
        price_category = tracker.get_slot("price_category") or "student"

        # Convert budget to float
        budget = None
        if budget_slot is not None:
            try:
                budget = float(str(budget_slot).replace(",", "."))
            except ValueError:
                pass

        # Try to extract budget from message if not in slot
        if budget is None:
            message = tracker.latest_message.get("text", "")
            import re
            match = re.search(r'(\d+[.,]?\d*)\s*(?:euros?|€)?', message)
            if match:
                try:
                    budget = float(match.group(1).replace(",", "."))
                except ValueError:
                    pass

        if budget is None:
            dispatcher.utter_message(
                text="What's your budget for a meal? Please provide an amount in euros."
            )
            return []

        if not cached_menu_json:
            dispatcher.utter_message(
                text="Please select a canteen first so I can suggest a meal."
            )
            return [SlotSet("budget", budget)]

        menu = deserialize_menu(cached_menu_json)
        if not menu:
            dispatcher.utter_message(
                text="Sorry, I lost the menu data. Please ask for the menu again."
            )
            return [SlotSet("budget", budget)]

        # Get main dishes and sides
        mains_category = next((c for c in menu.categories if c.name.lower() == "main dishes"), None)
        sides_category = next((c for c in menu.categories if c.name.lower() == "desserts"), None)

        mains_with_price = []
        if mains_category:
            for item in mains_category.items:
                price = parse_price(item.price, price_category)
                if price is not None:
                    mains_with_price.append((item, price))

        sides_with_price = []
        if sides_category:
            for item in sides_category.items:
                price = parse_price(item.price, price_category)
                if price is not None:
                    sides_with_price.append((item, price))

        # Sort mains by price descending (maximize value)
        mains_with_price.sort(key=lambda x: x[1], reverse=True)
        # Sort sides by price ascending (cheapest first)
        sides_with_price.sort(key=lambda x: x[1])

        canteen_name = CANTEEN_NAMES.get(menu.canteen_id, menu.canteen_id)
        best_combo = None
        best_main_only = None

        # Find best main + side combo within budget
        for main, main_price in mains_with_price:
            if main_price <= budget:
                remaining = budget - main_price
                # Find cheapest side that fits
                for side, side_price in sides_with_price:
                    if side_price <= remaining:
                        best_combo = (main, main_price, side, side_price)
                        break
                if best_combo:
                    break
                # Track best main-only option
                if best_main_only is None:
                    best_main_only = (main, main_price)

        if best_combo:
            main, main_price, side, side_price = best_combo
            total = main_price + side_price
            dispatcher.utter_message(
                text=f"**Best meal combo for €{budget:.2f} at {canteen_name}:**\n\n"
                f"🍽️ Main: {main.name} - €{main_price:.2f}\n"
                f"🥗 Side: {side.name} - €{side_price:.2f}\n"
                f"💰 Total: €{total:.2f}"
            )
        elif best_main_only:
            main, main_price = best_main_only
            dispatcher.utter_message(
                text=f"**Best option for €{budget:.2f} at {canteen_name}:**\n\n"
                f"🍽️ {main.name} - €{main_price:.2f}\n\n"
                f"(No sides fit within the remaining budget)"
            )
        else:
            # Suggest cheapest option
            all_items = []
            for cat in menu.categories:
                for item in cat.items:
                    price = parse_price(item.price, price_category)
                    if price is not None:
                        all_items.append((item, price, cat.name))

            if all_items:
                all_items.sort(key=lambda x: x[1])
                cheapest, cheapest_price, cat_name = all_items[0]
                dispatcher.utter_message(
                    text=f"Sorry, nothing fits your €{budget:.2f} budget.\n\n"
                    f"The cheapest option is:\n"
                    f"• {cheapest.name} ({cat_name}) - €{cheapest_price:.2f}"
                )
            else:
                dispatcher.utter_message(
                    text=f"Sorry, I couldn't find any priced items in the menu."
                )

        return [SlotSet("budget", budget)]


class ActionSetPriceCategory(Action):

    def name(self) -> Text:
        return "action_set_price_category"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        category = next(tracker.get_latest_entity_values("price_category"), None)

        if not category:
            message = tracker.latest_message.get("text", "").lower()
            for key in PRICE_CATEGORY_INDEX:
                if key in message:
                    category = key
                    break

        if not category or category not in PRICE_CATEGORY_INDEX:
            dispatcher.utter_message(
                text="Please choose a price category: student, worker, or guest."
            )
            return []

        dispatcher.utter_message(
            text=f"Price category set to {category}. Prices will now show {category} rates."
        )
        return [SlotSet("price_category", category)]
