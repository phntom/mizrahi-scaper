import logging
from datetime import date
from os import environ
from typing import Optional

import requests

from scraper.common import ScrapeResults, id_for_transaction

log = logging.getLogger(__name__)

CURRENCY_TO_ID = {}


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


def paginated_data_call(request, method='GET',
                        endpoint='http://localhost:5464', **kwargs):
    page1 = api_call(request, {
        'page': '1',
        **kwargs
    }, method, endpoint)
    yield from page1['data']
    for page in range(2, page1['meta']['pagination']['total_pages'] + 1):
        yield from api_call(request, {'page': page, **kwargs}, method, endpoint)['data']


def account_get_all(endpoint: str):
    yield from paginated_data_call('accounts', type='asset', endpoint=endpoint)


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
    data = {
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
        'currency_code': currency_code.upper(),
        'active': str(active).lower(),
        'order': order,
        'include_net_worth': str(include_net_worth).lower(),
        'account_role': account_role,
        'credit_card_type': credit_card_type,
        'monthly_payment_date': monthly_payment_date.strftime("%Y-%m-%d")
        if monthly_payment_date else None,
        'liability_type': liability_type,
        'liability_direction': liability_direction,
        'interest': str(interest),
        'interest_period': interest_period,
        'notes': notes,
        'latitude': latitude,
        'longitude': longitude,
        'zoom_level': zoom_level,
    }
    cleanup = set()
    for k, v in data.items():
        if v is None:
            cleanup.add(k)
    for k in cleanup:
        data.pop(k)
    return api_call(
        request='accounts',
        method='POST',
        endpoint=endpoint,
        data=data,
    )


def currency_get_all(endpoint: str):
    for currency in paginated_data_call('currencies', endpoint=endpoint):
        CURRENCY_TO_ID[currency['attributes']['code']] = int(currency['id'])


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
        start=start.strftime("%Y-%m-%d") if start else '',
        end=end.strftime("%Y-%m-%d") if end else '',
        type=query_type,
    )


def transaction_create(
        endpoint: str,
        t_date: date,
        amount: float,
        description: str,
        currency: str,
        account_name: str,
        account_id: int,
        note: str,
        external_id: str,
        process_date: Optional[date],
):
    if amount > 0:
        t_type = "deposit"
        t_target = account_name
        t_target_id = account_id
        t_source = "Cash"
        t_source_id = 4
    else:
        t_type = "withdrawal"
        t_target = "Cash"
        t_target_id = 4
        t_source = account_name
        t_source_id = account_id

    return api_call(
        request='transactions',
        method='POST',
        endpoint=endpoint,
        data={
            "error_if_duplicate_hash": "true",
            "apply_rules": "true",
            "fire_webhooks": "true",
            "group_title": f"{t_date} {t_type} of {amount}",
            "transactions": [
                {
                    "type": t_type,
                    "date": t_date.strftime("%Y-%m-%d") + "T00:00:00+02:00",
                    "amount": str(abs(amount)),
                    "description": description,
                    "currency_code": currency.upper(),
                    "source_id": str(t_source_id),
                    "source_name": t_source,
                    "destination_id": str(t_target_id),
                    "destination_name": t_target,
                    "reconciled": "true",
                    "notes": note,
                    "external_id": external_id,
                    "process_date": (process_date.strftime("%Y-%m-%d") + "T00:00:00+02:00") if process_date else '',
                }
            ]
        }
    )


def update_account(account_id, result, currency_t, endpoint):
    date_min = None
    date_max = None
    transaction_by_id = set()
    for currency, entries in result.transactions.items():
        if currency != currency_t:
            continue
        for entry in entries:
            if date_min is None or entry['date'] < date_min:
                date_min = entry['date']
            if date_max is None or entry['date'] > date_max:
                date_max = entry['date']
            transaction_by_id.add(id_for_transaction(entry, currency))
    for entry in transaction_get_all(endpoint, date_min, date_max):
        for transaction in entry['attributes']['transactions']:
            external_id = transaction['external_id']
            if external_id in transaction_by_id:
                transaction_by_id.remove(external_id)
    for currency, entries in result.transactions.items():
        if currency != currency_t:
            continue
        account_name = f'{result.bank} {currency.upper()}'
        for entry in entries:
            entry_id = id_for_transaction(entry, currency)
            if entry_id not in transaction_by_id:
                continue
            transaction_create(
                endpoint,
                entry['date'],
                entry['value'],
                entry['description'],
                currency,
                account_name,
                account_id,
                f"balance: {entry['balance']}",
                entry_id,
                entry['value_date'],
            )


def firefly_upload(result: ScrapeResults, endpoint: str):
    currency_get_all(endpoint)

    for account in account_get_all(endpoint):
        number = account['attributes'].get('account_number')
        cleanup = []
        for currency in result.transactions.keys():
            if number == f'{result.account}-{currency}':
                update_account(account['id'], result, currency, endpoint)
                cleanup.append(currency)
        for currency in cleanup:
            result.transactions.pop(currency)

    for currency in result.transactions.keys():
        opening_balance = 0.0,
        opening_balance_date = date.today()
        for t in result.transactions.get(currency, []):
            if t['date'] is not None and t['date'] < opening_balance_date:
                opening_balance_date = t['date']
                opening_balance = t['balance']
        number = f'{result.account}-{currency}'
        account = account_create(
            name=f'{result.bank} {currency.upper()}',
            account_type='asset',
            account_role='defaultAsset',
            account_number=number,
            opening_balance=opening_balance,
            opening_balance_date=opening_balance_date,
            endpoint=endpoint,
            active=True,
            include_net_worth=True,
            currency_code=currency,
            currency_id=CURRENCY_TO_ID[currency.upper()],
            credit_card_type='monthlyFull',
            monthly_payment_date=date(2020, 1, 1),
            liability_type='loan',
            liability_direction='credit',
            interest=0.0,
            interest_period='monthly',
        )['data']
        update_account(account['id'], result, currency, endpoint)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    log.info('connected to firefly server version {version}'.format(
        **api_call('about')['data']))

    result_x = ScrapeResults()
    from firefly_secret import test_enrich
    test_enrich(result_x)
    firefly_upload(result_x, 'http://localhost:5464')
