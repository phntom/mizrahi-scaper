import argparse
import logging
from sys import stderr, exc_info
from traceback import print_exception

from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.remote.remote_connection import LOGGER

from scraper.firefly import firefly_upload
from scraper.mizrahi import scrape


def main():
    logging.basicConfig()
    LOGGER.setLevel(logging.INFO)
    parser = argparse.ArgumentParser(description="scrape data")
    parser.add_argument("--target", default="http://127.0.0.1:4444")
    parser.add_argument("--browser", default="chrome")
    parser.add_argument("--type", default="mizrahi")
    parser.add_argument('--firefly', default='http://firefly.web.svc:8080')
    args = parser.parse_args()

    if args.type == 'mizrahi':
        result = scrape(
            args.target,
            getattr(DesiredCapabilities, args.browser.upper()),
        )
        if args.firefly:
            firefly_upload(result, args.firefly)


if __name__ == '__main__':
    # noinspection PyBroadException
    try:
        main()
    except BaseException as e:
        exc_type, exc_value, exc_traceback = exc_info()
        print_exception(exc_type, exc_value, exc_traceback, file=stderr)
        exit(1)
