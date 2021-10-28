import requests

from scraper.common import ScrapeResults


def api_call(request, params, method='GET', endpoint='http://firefly:8080'):
    r = requests.request(method, f'{endpoint}/api/v1/{request}', params=params)
    r.raise_for_status()


def firefly_upload(result, endpoint):
    accounts = api_call('accounts', {
        'page': '1',
        'type': 'asset',
    }, endpoint)


if __name__ == '__main__':
    result = ScrapeResults()
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
    firefly_upload(result, 'http://localhost:4141')
