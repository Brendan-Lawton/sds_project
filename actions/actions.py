# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions

from datetime import date
from typing import Any, Text, Dict, List, Optional

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher

from actions.services.menu_service import MenuService, MenuFetchError, MenuParseError


CANTEENS: Dict[str, str] = {
    "hardenbergstrasse": "1004",
    "hardenberg": "1004",
    "marchstrasse": "1010",
    "march": "1010",
    "vegan": "2456",
    "veggie": "2456",
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


def format_menu(menu) -> str:
    """Format the menu DTO into a readable message."""
    lines = [f"Menu for {CANTEEN_NAMES.get(menu.canteen_id, menu.canteen_id)} on {menu.date}:\n"]

    for category in menu.categories:
        if not category.items:
            continue
        lines.append(f"\n**{category.name}**")
        for item in category.items:
            price_str = f" - {item.price}" if item.price else ""
            lines.append(f"• {item.name}{price_str}")
            if item.allergens:
                lines.append(f"  Allergens: {', '.join(item.allergens)}")
            if item.additives:
                lines.append(f"  Additives: {', '.join(item.additives)}")

    return "\n".join(lines)


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

        service = MenuService()
        try:
            menu = service.get_menu(canteen_id, menu_date)
            if not menu.categories or all(not cat.items for cat in menu.categories):
                dispatcher.utter_message(
                    text=f"No menu available for {CANTEEN_NAMES.get(canteen_id, canteen_id)} on {menu_date}."
                )
            else:
                dispatcher.utter_message(text=format_menu(menu))
        except MenuFetchError as e:
            dispatcher.utter_message(text=f"Sorry, I couldn't fetch the menu: {str(e)}")
        except MenuParseError as e:
            dispatcher.utter_message(text=f"Sorry, I couldn't read the menu: {str(e)}")

        return [SlotSet("awaiting_canteen", False)]


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
            SlotSet("awaiting_canteen", False),
        ]
