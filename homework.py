import logging
import os
import time

import requests

import telegram
from logging.handlers import RotatingFileHandler
from http import HTTPStatus

from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
    filemode='w',
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(
    'my_logger.log',
    maxBytes=50000000,
    backupCount=5
)
logger.addHandler(handler)


def send_message(bot, message):
    """Отправка сообщения в телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(
            f'Message sent to Telegram: {message}'
        )
        return message
    except telegram.TelegramError as telegram_error:
        logger.error(
            f'Message not sent to Telegram: {telegram_error}'
        )


def get_api_answer(current_timestamp):
    """Пролучение данных с яндекса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
        if response.status_code != HTTPStatus.OK:
            check_message = (
                f'Ссылка {ENDPOINT} недоступна'
                f'Код ответа API: {response.status_code}'
            )
            logger.error(check_message)
            raise Exception(check_message)
        return response.json()
    except requests.RequestException as exception:
        raise ConnectionError(f'Ошибка сервера. {exception},'
                              f'URL{ENDPOINT}, HEADERS, params, TIMEOUT')


def check_response(response):
    """Проверка ответа API на корректность."""
    if not isinstance(response, dict):
        error_message = 'API is not a dictionary'
        logger.error(error_message)
        raise TypeError(error_message)
    if 'homeworks' not in response.keys():
        error_message = 'There is no key homeworks'
        logger.error(error_message)
        raise KeyError(error_message)
    if not isinstance(response.get('homeworks'), list):
        error_message = 'API is not a list'
        logger.error(error_message)
        raise TypeError(error_message)
    return response.get('homeworks')


def parse_status(homework):
    """Проверка информации о конкретной домашней работе."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES.keys():
        msg = 'Not existing homework status'
        logger.error(msg)
        raise KeyError(msg)

    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка наличия токенов."""
    tokens = True
    if PRACTICUM_TOKEN is None:
        tokens = False
        logger.critical(
            'Missing PRACTICUM_TOKEN'
        )
    if TELEGRAM_TOKEN is None:
        tokens - False
        logger.critical(
            'Missing TELEGRAM_TOKEN'
        )
    if TELEGRAM_CHAT_ID is None:
        tokens - False
        logger.critical(
            'Missing TELEGRAM_CHAT_ID'
        )
    return tokens


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        error_message = 'Token verification failed'
        logger.error(error_message)
        raise SystemExit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    ...

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework:
                send_message(bot, parse_status(homework[0]))

            current_timestamp = response.get(
                'current_date',
                current_timestamp
            )
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            send_message(bot, message)
            time.sleep(RETRY_TIME)
        else:
            ...


if __name__ == '__main__':
    main()
