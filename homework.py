import logging
import os
import time

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


def send_message(bot, message):
    """Отправка сообщения боту."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logging.error(
            f'При отправке сообщения в Telegram возникла ошибка {error}'
        )
    logging.info(f'Отправлено сообщение {message}')


def get_api_answer(current_timestamp):
    """Запрос к эндпоинту, возврат json в случае ответа."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != 200:
        message = f'Ошибка запроса к эндпоинту; {response.status_code}'
        logging.error(message)
        raise requests.exceptions.HTTPError(response.status_code)
    return response.json()


def check_response(response):
    """Проверка ответа от API."""
    if type(response) is list:
        return response[0].get('homeworks')
    if type(response.get('homeworks')) is not list:
        logging.error('Ответ не соответствует ожидаемому типу')
        raise e.IncorrectTypeError
    if response.get('homeworks') is None:
        logging.error('Ответ не содержит ключа "homeworks"')
        raise e.NoHaveKeyError
    return response.get('homeworks')


def parse_status(homework):
    """Извлекаем информацию о статусе работы, а так же об изменениях."""
    if homework.get('homework_name') is None:
        homework_name = 'Unnamed'
    homework_name = homework.get('homework_name')
    if homework.get('status') is None:
        logging.error('Статус проверки домашнего задания "None"')
        raise e.NoHaveKeyError
    else:
        homework_status = homework.get('status')
        verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности переменных окружения."""
    error_text = 'Отсутствует обязательная переменная окружения -'
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
        logging.critical('Завершение работы программы')
        return False

    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            message = parse_status(check_response(response))
            if message is not None:
                send_message(bot, message)
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
