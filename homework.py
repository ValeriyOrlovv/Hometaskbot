import time
import logging
import os
import requests
import sys

from dotenv import load_dotenv
from telebot import TeleBot, apihelper

from exceptions import Not200Exception, APIRequestException


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

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        filename='homework.log',
        filemode='a'
    )


def check_tokens():
    """Проверяет необходимые токены."""
    if not PRACTICUM_TOKEN:
        logging.critical('Отсутствует PRACTICUM_TOCKEN')
    if not TELEGRAM_TOKEN:
        logging.critical('Отсутствует TELEGRAM_TOCKEN')
    if not TELEGRAM_CHAT_ID:
        logging.critical('Отсутствует CHAT_ID_TOCKEN')
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправляет сообщение в чат."""
    try:
        logging.debug('Отправка сообщения')
        bot.send_message(TELEGRAM_CHAT_ID, message)
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
        if response.status_code != 200:
            raise Not200Exception(response.status_code)
    except requests.RequestException:
        raise APIRequestException
    return response.json()


def check_response(response):
    """Проверяет статус ответа API."""
    if not isinstance(response, dict):
        raise TypeError('Тип данных не соответствует ожидаемым')
    if 'homeworks' not in response:
        raise KeyError
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError('Значение "homeworks" не является списком')
    return homeworks


def parse_status(homework):
    """Получает необходимые данные из ответа API."""
    if 'homework_name' not in homework:
        raise KeyError('Нет названия домашней работы')
    if 'status' not in homework:
        raise KeyError('Нет статуса домашней работы')
    status_name = homework['status']
    if status_name not in HOMEWORK_VERDICTS:
        raise KeyError('Незадокументированный статус домашней работы')
    homework_name = homework['homework_name']
    verdict = HOMEWORK_VERDICTS[status_name]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit('Отсутствет один или несколько токенов')
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
