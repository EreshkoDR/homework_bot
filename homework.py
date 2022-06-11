import logging
import os
import sys
import time
import datetime as dt
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telegram import Bot

import exceptions

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID_TOKEN')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statusess/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщения боту."""
    try:
        logging.info('Attempt to send a message...')
        if message is not None:
            bot.send_message(TELEGRAM_CHAT_ID, message)
            logging.info(f'Message has been sent! {message}')
        logging.info('Homework status has not changed')
    except Exception as error:
        raise error


def get_api_answer(current_timestamp):
    """Запрос к эндпоинту, возврат json в случае ответа."""
    logging.info('Endpit request attempt')
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != HTTPStatus.OK:
        message = 'Endpoint request error'
        logging.error(message)
        raise requests.exceptions.HTTPError(message)
    return response.json()


def check_response(response):
    """Проверка ответа от API."""
    logging.info('Response check started')
    if isinstance(response, list):
        return response[0].get('homeworks')
    if not isinstance(response.get('homeworks'), list):
        error_message = 'Response does not match expected type'
        logging.error(error_message)
        raise exceptions.IncorrectTypeError(error_message)
    if response.get('homeworks') is None:
        error_message = 'Response does not contain key "homeworks"'
        logging.error(error_message)
        raise exceptions.NoHaveKeyError(error_message)
    if response.get('current_date') is None:
        error_message = 'Response does not contain key "current_date"'
        logging.error(error_message)
        raise exceptions.NoHaveKeyError(error_message)
    return response.get('homeworks')


def parse_status(homework):
    """Извлекаем информацию о статусе работы, а так же об изменениях."""
    logging.info('Parse status started')
    check_change = None
    if type(homework) is not dict:
        homework = homework[0]
    if homework.get('homework_name') is None:
        error_message = 'Homework name does not name'
        logging.error(error_message)
        raise KeyError(error_message)
    if homework.get('status') is None:
        error_message = 'Homework check status is "None"'
        logging.error(error_message)
        raise KeyError(error_message)
    if check_change == homework.get('status'):
        return None
    check_change = homework.get('status')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности переменных окружения."""
    error_text = 'Missing required environment variable -'
    if not TELEGRAM_TOKEN:
        logging.critical(f'{error_text} "TELEGRAM_TOKEN"')
    if not TELEGRAM_CHAT_ID:
        logging.critical(f'{error_text} "TELEGRAM_CHAT_ID"')
    if not PRACTICUM_TOKEN:
        logging.critical(f'{error_text} "PRACTICUM_TOKEN"')
    return all((
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID,
        PRACTICUM_TOKEN
    ))


def main():
    """Основная логика работы бота."""
    logging.basicConfig(
        level=logging.INFO,
        filename='main.log',
        filemode='a',
        format='%(asctime)s, %(levelname)s, %(message)s, '
               'function:%(funcName)s, line:%(lineno)d, %(name)s',
    )
    if not check_tokens():
        logging.critical('Completion of the program')
        return sys.exit('Missing required environment variable')

    bot = Bot(token=TELEGRAM_TOKEN)
    thirty_days_ago = dt.datetime.now() - dt.timedelta(days=30)
    unix_time = time.mktime(dt.datetime.timetuple(thirty_days_ago))

    while True:
        try:
            response = get_api_answer(int(unix_time))
            message = parse_status(check_response(response))
            if message is not None:
                send_message(bot, message)
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Programm crash: {error}'
            logging.error(message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
