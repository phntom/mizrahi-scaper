import re
from datetime import datetime, date
from hashlib import sha256
from typing import Optional

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


def clean_float(text: str) -> Optional[float]:
    text = re.sub('[^0-9.-]', '', text)
    return float(text) if text else None


def date_parse(text: str) -> Optional[date]:
    return datetime.strptime(text, "%d/%m/%y").date() if text else None


def id_for_transaction(entry: dict, currency: str, account: str) -> str:
    date_use = entry['date'] if entry.get('date') else entry['value_date']
    m = sha256()
    m.update(date_use.strftime("%Y-%m-%d-").encode('utf-8'))
    m.update(entry['serial'].encode('utf-8'))
    m.update(b'-')
    m.update(currency.lower().encode('utf-8'))
    m.update(b'-')
    m.update(account.encode('utf-8'))
    m.update(b'-')
    m.update(str(entry['value']).encode('utf-8'))
    m.update(b'-')
    m.update(str(entry['balance']).encode('utf-8'))
    return m.hexdigest()
