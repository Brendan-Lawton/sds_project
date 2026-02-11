from dataclasses import dataclass, field
from typing import Optional
import requests
from bs4 import BeautifulSoup
import html
from enum import Enum



class MenuServiceError(Exception):
    """Base exception for MenuService errors."""
    pass


class MenuFetchError(MenuServiceError):
    """Raised when fetching menu data fails."""
    pass


class MenuParseError(MenuServiceError):
    """Raised when parsing menu HTML fails."""
    pass


@dataclass
class MenuItem:
    name: str
    price: Optional[str]
    allergens: list[str] = field(default_factory=list)
    additives: list[str] = field(default_factory=list)

class PriceCategory(Enum):
    Student = "student"
    EMPLOYEE = "employee"
    GUEST = "guest"

@dataclass
class MenuCategory:
    name: str
    items: list[MenuItem] = field(default_factory=list)


@dataclass
class MenuDTO:
    date: str
    canteen_id: str
    categories: list[MenuCategory] = field(default_factory=list)


_ALLERGENS: dict[str, str] = {
    "21": "Gluten-containing cereals",
    "21a": "Wheat",
    "21b": "Rye",
    "21c": "Barley",
    "21d": "Oats",
    "21e": "Spelt",
    "21f": "Kamut",
    "22": "Crustaceans",
    "23": "Eggs",
    "24": "Fish",
    "25": "Peanuts",
    "26": "Tree nuts",
    "26a": "Almonds",
    "26b": "Hazelnuts",
    "26c": "Walnuts",
    "26d": "Cashews",
    "26e": "Pecans",
    "26f": "Brazil nuts",
    "26g": "Pistachios",
    "26h": "Macadamia nuts",
    "27": "Celery",
    "28": "Soy",
    "29": "Mustard",
    "30": "Milk and dairy products (incl. lactose)",
    "31": "Sesame",
    "32": "Sulfur dioxide and sulfites",
    "33": "Lupins",
    "34": "Mollusks",
    "35": "Nitrite curing salt",
    "36": "Yeast",
    "37": "Blue poppy seeds",
}

_ADDITIVES: dict[str, str] = {
    "2": "Pork or pork gelatin",
    "3": "Alcohol",
    "4": "Flavor enhancer",
    "5": "Waxed",
    "6": "Preserved",
    "7": "Antioxidants",
    "8": "Food coloring",
    "9": "Phosphate",
    "10": "Blackened",
    "12": "Contains phenylalanine source",
    "13": "Sweeteners",
    "14": "Contains partially finely minced meat",
    "16": "Contains caffeine",
    "17": "Contains quinine",
    "19": "Sulfured",
    "20": "May have laxative effects",
}


class MenuService:
    _BASE_URL = "https://www.stw.berlin/xhr/speiseplan-wochentag.html"

    def get_menu(self, canteen_id: str, date: str, price_category: Enum, max_price: float) -> MenuDTO:
        """
        Get the menu for a given canteen and date.

        Args:
            canteen_id: The resource ID of the canteen (e.g., "1004")
            date: The date in YYYY-MM-DD format (e.g., "2026-01-22")

        Returns:
            MenuDTO containing all menu categories and items

        Raises:
            MenuFetchError: If fetching the menu fails
            MenuParseError: If parsing the HTML fails
        """
        html_content = self._fetch_menu_html(canteen_id, date)

        return self._parse_menu_html(html_content, canteen_id, date, price_category, max_price)

    def _fetch_menu_html(self, canteen_id: str, date: str) -> str:
        """Fetch the raw HTML content from the menu API using multipart/form-data."""
        try:
            response = requests.post(
                self._BASE_URL,
                data={"resources_id": canteen_id, "date": date},
                headers={"User-Agent": "MenuService/1.0"},
                timeout=10,
            )
            response.raise_for_status()

            return response.text
        except requests.exceptions.Timeout:
            raise MenuFetchError(f"Request timed out for canteen {canteen_id} on {date}")
        except requests.exceptions.ConnectionError:
            raise MenuFetchError(f"Connection failed for canteen {canteen_id} on {date}")
        except requests.exceptions.HTTPError as e:
            raise MenuFetchError(f"HTTP error {e.response.status_code} for canteen {canteen_id} on {date}")
        except requests.exceptions.RequestException as e:
            raise MenuFetchError(f"Request failed for canteen {canteen_id} on {date}: {str(e)}")

    def _parse_menu_html(self, html_content: str, canteen_id: str, date: str, price_category: Enum, max_price: float) -> MenuDTO:
        """Parse the HTML content into a MenuDTO."""
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            categories: list[MenuCategory] = []

            group_wrappers = soup.find_all("div", class_="splGroupWrapper")
            group_wrappers = [wrapper for wrapper in group_wrappers if wrapper.find("div", class_="splGroup")]

            if not group_wrappers:
                raise MenuParseError(f"No menu categories found for canteen {canteen_id} on {date}")

            for wrapper in group_wrappers:
                try:
                    category = self._parse_category(wrapper, price_category, max_price)
                    print("Parsed category:", category)  # Debug: Print the parsed category
                    if category:
                        categories.append(category)
                except Exception as e:
                    print(f"Error parsing category: {e}")
                    continue  # Skip to the next category

            return MenuDTO(date=date, canteen_id=canteen_id, categories=categories)

        except MenuParseError:
            raise
        except Exception as e:
            raise MenuParseError(f"Failed to parse menu HTML for canteen {canteen_id} on {date}: {str(e)}")

    # def filter_menu_by_max_price(menu: MenuDTO, max_price: float) -> MenuDTO:
    #     """Filter menu items by max_price."""
    #     filtered_categories = []
    #     for category in menu.categories:
    #         filtered_items = []
    #         for item in category.items:
    #             if not item.price:
    #                 continue  # Skip items with no price
    #             # Extract the numeric value from the price string (e.g., "3.50 €" -> 3.50)
    #             price_value = float(item.price.replace("€", "").strip())
    #             if price_value <= max_price or max_price == 0:
    #                 filtered_items.append(item)
    #         if filtered_items:
    #             filtered_categories.append(MenuCategory(name=category.name, items=filtered_items))

    #     return MenuDTO(
    #         date=menu.date,
    #         canteen_id=menu.canteen_id,
    #         categories=filtered_categories,
    #     )


    def _parse_category(self, wrapper, price_category, max_price) -> Optional[MenuCategory]:
        """Parse a single category wrapper into a MenuCategory."""
        category_name_elem = wrapper.find("div", class_="splGroup")
        if not category_name_elem:
            return None

        category_name = category_name_elem.get_text(strip=True)
        items: list[MenuItem] = []

        meal_rows = wrapper.find_all("div", class_="splMeal")
        for meal_row in meal_rows:
            item = self._parse_meal_item(meal_row, price_category, max_price)
            if item:
                items.append(item)

        return MenuCategory(name=category_name, items=items)

    def _parse_meal_item(self, meal_row, price_category, max_price) -> Optional[MenuItem]:
        """Parse a single meal row into a MenuItem."""
        name_elem = meal_row.find("span", class_="bold")
        if not name_elem:
            return None

        name = name_elem.get_text(strip=True)

        price = self._extract_price(meal_row)
        price_string = ""
        if price:
            if price_category == PriceCategory.Student:
                price_string = html.unescape(price.get("stud") or "").replace("\u20ac", "€").strip()
            elif price_category == PriceCategory.EMPLOYEE:
                price_string = html.unescape(price.get("employ") or "").replace("\u20ac", "€").strip()
            elif price_category == PriceCategory.GUEST:
                price_string = html.unescape(price.get("guest") or "").replace("\u20ac", "€").strip()

            if float(max_price) > 0.0 and price_string:
                try:
                    if float(price_string.replace("€", "").replace(",", ".").strip()) > float(max_price):
                        return None
                except ValueError:
                    pass

        allergens, additives = self._extract_allergens_and_additives(meal_row)
        return MenuItem(
            name=name,
            price=price_string,
            allergens=allergens,
            additives=additives,
        )

    def from_string(self, string):
        # Remove potential whitespace, quotes, etc.
        string = string
        # Parse the string - assuming format like "name,age,location"
        parts = string.split("/")
        if len(parts) != 3:
            raise ValueError("String format incorrect")

        # Extract prices and remove "€" if present
        price_stud = parts[0].replace("€", "").strip()
        price_employ = parts[1].replace("€", "").strip()
        price_guest = parts[2].replace("€", "").strip()

        return {"stud": price_stud, "employ": price_employ, "guest": price_guest}


    def _extract_price(self, meal_row):
        price_div = meal_row.find("div", class_="col-xs-12 col-md-3 text-right")
        if not price_div:
            return None

        # price_text = price_div.get_text(strip=True)
        price_data = self.from_string(price_div.get_text(strip=True))
        print(price_data)

        if price_data:
            return price_data

        return None
        # try:
        #     return self.from_string(price_text)
        # except ValueError as e:
        #     print(f"Failed to parse price: {e}")
        #     return None




    def _extract_allergens_and_additives(self, meal_row) -> tuple[list[str], list[str]]:
        """Extract and translate allergens and additives from the meal row."""
        allergens: list[str] = []
        additives: list[str] = []

        kennz_data = meal_row.get("data-kennz", "")
        if not kennz_data:
            return allergens, additives

        codes = [code.strip() for code in kennz_data.split(",") if code.strip()]

        for code in codes:
            if code in _ALLERGENS:
                allergens.append(_ALLERGENS[code])
            elif code in _ADDITIVES:
                additives.append(_ADDITIVES[code])

        return allergens, additives

