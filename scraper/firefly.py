import logging
from os import environ

import requests

from scraper.common import ScrapeResults

log = logging.getLogger(__name__)


def api_call(request, params=None, method='GET',
             endpoint='http://localhost:5464', data=None):
    token = environ.get('FIREFLY_TOKEN')
    headers = {
        'Accept': 'application/vnd.api+json',
        'Authorization': f'Bearer {token}',
    }
    r = requests.request(method=method, url=f'{endpoint}/api/v1/{request}',
                         params=params, headers=headers, data=data)
    r.raise_for_status()
    return r.json()


def get_accounts(endpoint: str):
    accounts = api_call('accounts', {
        'page': '1',
        'type': 'asset',
    }, 'GET', endpoint)
    yield from accounts['data']
    for page in range(1, accounts['meta']['pagination']['total_pages']):
        yield from api_call('accounts', {
            'page': '1',
            'type': 'asset',
        }, 'GET', endpoint)['data']


def update_account(account, result, currency):
    pass


def firefly_upload(result: ScrapeResults, endpoint: str):
    for account in get_accounts(endpoint):
        number = account['attributes'].get('account_number')
        cleanup = []
        for currency in result.transactions.keys():
            if number == f'{result.account}-{currency}':
                update_account(account, result, currency)
                cleanup.append(currency)
        for currency in cleanup:
            result.transactions.pop(currency)

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
    log.info('connected to firefly server version {version}'.format(
        **api_call('about')['data']))

    firefly_upload(ScrapeResults(), 'http://localhost:5464')
