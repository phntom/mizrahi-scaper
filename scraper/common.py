import re
from dataclasses import dataclass

from selenium.webdriver import Keys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.remote.webdriver import WebDriver


@dataclass
class ScrapeResults:
    bank = ''
    account = ''
    nis = 0.0
    usd = 0.0
    eur = 0.0
    stocks = []
    transactions = {
        'nis': [],
        'usd': [],
        'eur': [],
    }


@dataclass
class ScrapeStock:
    symbol = ''
    owned = 0
    buying_total = 0
    selling_total = 0
    buying = {}
    selling = {}


def find_element_by_text(driver: WebDriver, by, value, text, exact=True):
    for element in driver.find_elements(by=by, value=value):
        if (exact and element.text == text) \
                or (not exact and text in element.text):
            return element


def safe_click(driver: WebDriver, element, timeout=10):
    element = WebDriverWait(driver, timeout).until(
        expected_conditions.element_to_be_clickable(element)
    )
    driver.execute_script('arguments[0].scrollIntoView(true)', element)
    element.send_keys(Keys.RETURN)


def clean_float(text):
    return float(re.sub('[^0-9.-]', '', text))
