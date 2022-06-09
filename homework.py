import logging
import os
import time
import datetime as dt

import requests
from dotenv import load_dotenv
from telegram import Bot

import exceptions as e

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    filename='main.log',
    filemode='a',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID_TOKEN')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

check_change = None


def send_message(bot, message):
    """Отправка сообщения боту."""
    try:
        if message is not None:
            bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logging.error(
            f'An error occurred while sending a message to Telegram {error}'
        )
    logging.info(f'Message has been sended {message}')


def get_api_answer(current_timestamp):
    """Запрос к эндпоинту, возврат json в случае ответа."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != 200:
        message = f'Endpoint request error; {response.status_code}'
        logging.error(message)
        raise requests.exceptions.HTTPError(response.status_code)
    return response.json()


def check_response(response):
    """Проверка ответа от API."""
    if type(response) is list:
        return response[0].get('homeworks')
    if type(response.get('homeworks')) is not list:
        logging.error('Response does not match expected type')
        raise e.IncorrectTypeError
    if response.get('homeworks') is None:
        logging.error('Response does not contain key "homeworks"')
        raise e.NoHaveKeyError
    return response.get('homeworks')


def parse_status(homework):
    """Извлекаем информацию о статусе работы, а так же об изменениях."""
    global check_change
    if type(homework) is not dict:
        homework = homework[0]
    if homework.get('homework_name') is None:
        logging.error('Homework name does not name')
        raise KeyError
    if homework.get('status') is None:
        logging.error('Homework check status is "None"')
        raise KeyError
    if check_change == homework.get('status'):
        return None
    check_change = homework.get('status')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES[homework_status]
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
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID and PRACTICUM_TOKEN:
        return True
    return False


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Completion of the program')
        return False

    bot = Bot(token=TELEGRAM_TOKEN)
    # current_timestamp = int(time.time())
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
