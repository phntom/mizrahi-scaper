import logging
from datetime import date
from os import environ
from typing import Optional

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


def paginated_data_call(request, asset='asset', method='GET',
                        endpoint='http://localhost:5464', **kwargs):
    page1 = api_call(request, {
        'page': '1',
        'type': asset,
        **kwargs
    }, method, endpoint)
    yield from page1['data']
    for page in range(1, page1['meta']['pagination']['total_pages']):
        yield from api_call(request, {
            'page': '1',
            'type': asset,
        }, method, endpoint)['data']


def account_get_all(endpoint: str):
    yield from paginated_data_call('accounts', endpoint=endpoint)


def account_create(
        name: str,
        account_type: str = 'asset',
        iban: str = '',
        bic: str = '',
        account_number: str = '',
        opening_balance: Optional[float] = None,
        opening_balance_date: Optional[date] = None,
        virtual_balance: Optional[float] = None,
        currency_id: Optional[int] = None,
        currency_code: str = '',
        active: bool = False,
        order: Optional[int] = None,
        include_net_worth: bool = True,
        account_role: str = '',
        credit_card_type: str = '',
        monthly_payment_date: Optional[date] = None,
        liability_type: str = '',
        liability_direction: str = '',
        interest: Optional[float] = None,
        interest_period: str = '',
        notes: str = '',
        latitude: float = 0.0,
        longitude: float = 0.0,
        zoom_level: int = 0,
        endpoint: str = None,
):
    return api_call(
        request='accounts',
        method='POST',
        endpoint=endpoint,
        data={
            'name': name,
            'type': account_type,
            'iban': iban,
            'bic': bic,
            'account_number': account_number,
            'opening_balance': str(opening_balance) if opening_balance else '',
            'opening_balance_date': opening_balance_date.strftime("%Y-%m-%d")
            if opening_balance_date else '',
            'virtual_balance': str(virtual_balance) if virtual_balance else '',
            'currency_id': str(currency_id) if currency_id else '',
            'currency_code': currency_code,
            'active': active,
            'order': order if order is not None else 1,
            'include_net_worth': include_net_worth,
            'account_role': account_role,
            'credit_card_type': credit_card_type,
            'monthly_payment_date': monthly_payment_date.strftime("%Y-%m-%d")
            if monthly_payment_date else '',
            'liability_type': liability_type,
            'liability_direction': liability_direction,
            'interest': str(interest) if interest else '',
            'interest_period': interest_period,
            'notes': notes,
            'latitude': latitude,
            'longitude': longitude,
            'zoom_level': zoom_level,
        }
    )


def transaction_get_all(
        endpoint: str,
        start: Optional[date] = None,
        end: Optional[date] = None,
        query_type='all'
):
    # type query_type : all, withdrawal, withdrawals, expense, deposit,
    # deposits, income, transfer, transfers, opening_balance,
    # reconciliation, special, specials, default
    yield from paginated_data_call(
        'transactions',
        endpoint=endpoint,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        type=query_type,
    )


def transaction_create(endpoint: str,):
    pass


def update_account(account_number, result, currency, endpoint):
    pass


def firefly_upload(result: ScrapeResults, endpoint: str):
    for account in account_get_all(endpoint):
        number = account['attributes'].get('account_number')
        cleanup = []
        for currency in result.transactions.keys():
            if number == f'{result.account}-{currency}':
                update_account(number, result, currency, endpoint)
                cleanup.append(currency)
        for currency in cleanup:
            result.transactions.pop(currency)

    for currency in result.transactions.keys():
        opening_balance = 0.0,
        opening_balance_date = date.today(),
        for t in result.transactions.get(currency, []):
            if t['date'] < opening_balance_date:
                opening_balance_date = t['date']
                opening_balance = t['balance']
        number = f'{result.account}-{currency}'
        account_create(
            name=f'{result.bank} {currency.upper()}',
            account_type='asset',
            account_number=number,
            opening_balance=opening_balance,
            opening_balance_date=opening_balance_date,
        )
        update_account(number, result, currency, endpoint)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    log.info('connected to firefly server version {version}'.format(
        **api_call('about')['data']))

    firefly_upload(ScrapeResults(), 'http://localhost:5464')
