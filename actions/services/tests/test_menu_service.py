import os

import pytest
from unittest.mock import Mock, patch
import requests

from actions.services.menu_service import (
    MenuService,
    MenuDTO,
    MenuCategory,
    MenuItem,
    MenuFetchError,
    MenuParseError,
)


# located in cwd/stubs/sample_menu.html
SAMPLE_HTML = os.path.join(os.path.dirname(__file__), "stubs", "sample_menu.html")
with open(SAMPLE_HTML, "r", encoding="utf-8") as f:
    SAMPLE_HTML = f.read()

EMPTY_HTML = os.path.join(os.path.dirname(__file__), "stubs", "empty_menu.html")
with open(EMPTY_HTML, "r", encoding="utf-8") as f:
    EMPTY_HTML = f.read()


class TestMenuService:
    @pytest.fixture
    def service(self):
        return MenuService()

    @pytest.fixture
    def mock_response(self):
        mock = Mock()
        mock.text = SAMPLE_HTML
        mock.raise_for_status = Mock()
        return mock

    @patch("actions.services.menu_service.requests.get")
    def test_get_menu_success(self, mock_get, service, mock_response):
        mock_get.return_value = mock_response

        menu = service.get_menu("321", "2026-01-19")

        assert isinstance(menu, MenuDTO)
        assert menu.canteen_id == "321"
        assert menu.date == "2026-01-19"
        assert len(menu.categories) == 3

    @patch("actions.services.menu_service.requests.get")
    def test_get_menu_categories_parsed_correctly(self, mock_get, service, mock_response):
        mock_get.return_value = mock_response

        menu = service.get_menu("321", "2026-01-19")

        category_names = [cat.name for cat in menu.categories]
        assert "Vorspeisen" in category_names
        assert "Salate" in category_names
        assert "Desserts" in category_names

    @patch("actions.services.menu_service.requests.get")
    def test_get_menu_items_parsed_correctly(self, mock_get, service, mock_response):
        mock_get.return_value = mock_response

        menu = service.get_menu("321", "2026-01-19")

        vorspeisen = next(cat for cat in menu.categories if cat.name == "Vorspeisen")
        assert len(vorspeisen.items) == 1
        assert vorspeisen.items[0].name == "Bulgursalat mit Minze"

        salate = next(cat for cat in menu.categories if cat.name == "Salate")
        assert len(salate.items) == 2

    @patch("actions.services.menu_service.requests.get")
    def test_get_menu_price_extracted(self, mock_get, service, mock_response):
        mock_get.return_value = mock_response

        menu = service.get_menu("321", "2026-01-19")

        vorspeisen = next(cat for cat in menu.categories if cat.name == "Vorspeisen")
        assert vorspeisen.items[0].price == "€ 1,95/2,15/2,35"

    @patch("actions.services.menu_service.requests.get")
    def test_get_menu_price_none_when_missing(self, mock_get, service, mock_response):
        mock_get.return_value = mock_response

        menu = service.get_menu("321", "2026-01-19")

        salate = next(cat for cat in menu.categories if cat.name == "Salate")
        french_dressing = next(item for item in salate.items if item.name == "French-Dressing")
        assert french_dressing.price is None

    @patch("actions.services.menu_service.requests.get")
    def test_get_menu_allergens_translated(self, mock_get, service, mock_response):
        mock_get.return_value = mock_response

        menu = service.get_menu("321", "2026-01-19")

        vorspeisen = next(cat for cat in menu.categories if cat.name == "Vorspeisen")
        bulgur = vorspeisen.items[0]
        assert "Wheat" in bulgur.allergens

    @patch("actions.services.menu_service.requests.get")
    def test_get_menu_multiple_allergens(self, mock_get, service, mock_response):
        mock_get.return_value = mock_response

        menu = service.get_menu("321", "2026-01-19")

        desserts = next(cat for cat in menu.categories if cat.name == "Desserts")
        porridge = next(item for item in desserts.items if "Porridge" in item.name)

        assert "Oats" in porridge.allergens
        assert "Almonds" in porridge.allergens

    @patch("actions.services.menu_service.requests.get")
    def test_get_menu_additives_translated(self, mock_get, service, mock_response):
        mock_get.return_value = mock_response

        menu = service.get_menu("321", "2026-01-19")

        salate = next(cat for cat in menu.categories if cat.name == "Salate")
        salad = next(item for item in salate.items if item.name == "Große Salatschale")

        assert "Sweeteners" in salad.additives

    @patch("actions.services.menu_service.requests.get")
    def test_get_menu_mixed_allergens_and_additives(self, mock_get, service, mock_response):
        mock_get.return_value = mock_response

        menu = service.get_menu("321", "2026-01-19")

        desserts = next(cat for cat in menu.categories if cat.name == "Desserts")
        porridge = next(item for item in desserts.items if "Porridge" in item.name)

        assert "Antioxidants" in porridge.additives
        assert "Oats" in porridge.allergens
        assert "Almonds" in porridge.allergens

    @patch("actions.services.menu_service.requests.get")
    def test_get_menu_no_allergens_or_additives(self, mock_get, service, mock_response):
        mock_get.return_value = mock_response

        menu = service.get_menu("321", "2026-01-19")

        desserts = next(cat for cat in menu.categories if cat.name == "Desserts")
        obstsalat = next(item for item in desserts.items if "Obstsalat" in item.name)

        assert obstsalat.allergens == []
        assert obstsalat.additives == []

    @patch("actions.services.menu_service.requests.get")
    def test_fetch_error_timeout(self, mock_get, service):
        mock_get.side_effect = requests.exceptions.Timeout()

        with pytest.raises(MenuFetchError) as exc_info:
            service.get_menu("321", "2026-01-19")

        assert "timed out" in str(exc_info.value)

    @patch("actions.services.menu_service.requests.get")
    def test_fetch_error_connection(self, mock_get, service):
        mock_get.side_effect = requests.exceptions.ConnectionError()

        with pytest.raises(MenuFetchError) as exc_info:
            service.get_menu("321", "2026-01-19")

        assert "Connection failed" in str(exc_info.value)

    @patch("actions.services.menu_service.requests.get")
    def test_fetch_error_http_error(self, mock_get, service):
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_get.return_value = mock_response

        with pytest.raises(MenuFetchError) as exc_info:
            service.get_menu("321", "2026-01-19")

        assert "HTTP error 404" in str(exc_info.value)

    @patch("actions.services.menu_service.requests.get")
    def test_parse_error_no_categories(self, mock_get, service):
        mock_response = Mock()
        mock_response.text = EMPTY_HTML
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with pytest.raises(MenuParseError) as exc_info:
            service.get_menu("321", "2026-01-19")

        assert "No menu categories found" in str(exc_info.value)

    @patch("actions.services.menu_service.requests.get")
    def test_request_params_correct(self, mock_get, service, mock_response):
        mock_get.return_value = mock_response

        service.get_menu("321", "2026-01-22")

        mock_get.assert_called_once_with(
            "https://www.stw.berlin/xhr/speiseplan-wochentag.html",
            params={"resources_id": "321", "date": "2026-01-22"},
            timeout=10,
        )
