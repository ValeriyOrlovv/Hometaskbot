class Not200Exception(Exception):
    """Исключение вызывается, если возвращается статус, отличный от 200."""

    def __init__(self, status_code):
        self.status_code = status_code
        super().__init__(f'Ошибка ответа: {self.status_code}')


class APIRequestException(Exception):
    """Исключение при ошибке ответа."""

    def __init__(self):
        super().__init__("Ошибка запроса API")
