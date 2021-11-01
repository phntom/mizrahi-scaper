import logging
from os import environ

import requests

from scraper.common import ScrapeResults

log = logging.getLogger(__name__)


def api_call(request, params=None, method='GET', endpoint='http://localhost:5464', data=None):
    token = environ.get('FIREFLY_TOKEN')
    headers = {
        'Accept': 'application/vnd.api+json',
        'Authorization': f'Bearer {token}',
    }
    r = requests.request(method=method, url=f'{endpoint}/api/v1/{request}', params=params, headers=headers, data=data)
    r.raise_for_status()
    return r.json()


def firefly_upload(result, endpoint):
    accounts = api_call('accounts', {
        'page': '1',
        'type': 'asset',
    }, 'GET', endpoint)
    for account in accounts['data']:
        number = account['attributes'].get('account_number')
        if number == result.account:
            return  # account found; update existing

    # account not found, create one
    api_call('accounts', None, 'POST', endpoint, {
        "name": "Mizrahi Tefahot USD",
        "type": "asset",
        "iban": "",
        "bic": "",
        "account_number": result.account,
        "opening_balance": result.usd,
        "opening_balance_date": "2021-10-31",
        "virtual_balance": "",
        "currency_id": "12",
        "currency_code": "EUR",
        "active": True,
        "order": 1,
        "include_net_worth": True,
        "account_role": "defaultAsset",
        "credit_card_type": "monthlyFull",
        "monthly_payment_date": "2018-09-17",
        "liability_type": "loan",
        "liability_direction": "credit",
        "interest": "5.3",
        "interest_period": "monthly",
        "notes": "Some example notes",
        "latitude": 51.983333,
        "longitude": 5.916667,
        "zoom_level": 6
    })


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    log.info('connected to firefly server version {version}'.format(**api_call('about')['data']))

    result = ScrapeResults()
    result.account = '573-290817'
    result.nis = 27762.46
    result.usd = 33034.04
    result.eur = 251.6
    result.stocks = [
        {
            "fullName": "\u200f.\u200fA\u200f.\u200fP\u200f.\u200fC S\u200f "
                        "& \u200fPIAGGIO",
            "bankSymbol": "(PIA IM) 328500 / 2",
            "price": 3.17,
            "quantity": 4000.0,
            "profitPercent": 6.02,
            "profitNis": 3002.43
        },
        {
            "fullName": "\u200fTESLA MOTORS",
            "bankSymbol": "(TSLA) 382283 / 2",
            "price": 1037.86,
            "quantity": 20.0,
            "profitPercent": 32.92,
            "profitNis": 16272.63
        },
        {
            "fullName": "\u200fSHIFT TECHNOLOGIES INC",
            "bankSymbol": "(SFT) 32057002 / 2",
            "price": 6.77,
            "quantity": 2400.0,
            "profitPercent": 0.34,
            "profitNis": 175.46
        },
        {
            "fullName": "\u200f50\u200f \u200fP\u200f&\u200fPROSHARES "
                        "ULTRAPRO S",
            "bankSymbol": "(UPRO) 379917 / 2",
            "price": 133.91,
            "quantity": 1.0,
            "profitPercent": 75.23,
            "profitNis": 181.95
        }
    ]
    firefly_upload(result, 'http://localhost:5464')
