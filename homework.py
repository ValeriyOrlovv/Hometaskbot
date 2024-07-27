import time
import logging
from logging.handlers import RotatingFileHandler
import os
import requests
import sys

from dotenv import load_dotenv
from telebot import TeleBot, apihelper

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='homework.log',
    filemode='a'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(
    'my_logger.log',
    maxBytes=50000000,
    backupCount=5
)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """Проверяет необходимые токены."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправляет сообщение в чат."""
    chat_id = TELEGRAM_CHAT_ID
    try:
        bot.send_message(chat_id, message)
        logging.debug(f'Сообщение отправлено: {message}')
    except apihelper.ApiException as error:
        logging.error(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(timestamp):
    """Проверяет, есть ли обновления статуса домашней работы через API."""
    from_date = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params=from_date
        )
        response.raise_for_status()
    except requests.RequestException as error:
        logging.error(f'Ошибка при запросе к API: {error}')
        return error
    if response.status_code == 204:
        logging.debug('Ошибка при запросе')
        raise requests.HTTPError
    return response.json()


def check_response(response):
    """Проверяет статус ответа API."""
    try:
        homeworks = response['homeworks']
    except KeyError:
        logging.error('Данные не соответствуют ожидаемым')
        raise ValueError('Данные не соответствуют ожидаемым')
    if not isinstance(homeworks, list):
        logging.error('Значение "homeworks" не является списком')
        raise TypeError('Значение "homeworks" не является списком')
    return homeworks


def parse_status(homework):
    """Получает необходимые данные из ответа API."""
    try:
        homework_name = homework['homework_name']
        status_name = homework['status']
        verdict = HOMEWORK_VERDICTS[status_name]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except KeyError as error:
        logging.error(f'Ошибка при получении статуса домашней работы: {error}')
        raise KeyError


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Отсутствует один или несколько токенов')
        sys.exit()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework[0])
                send_message(bot, message)
                logging.debug('Сообщение отправлено')
                timestamp = response.get('current_date', timestamp)
            else:
                logging.debug('Нет изменения статуса домашней работы.')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
