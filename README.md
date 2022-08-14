# Telebot для взаимодействия с API https://www.hotels.com/

## Описание

Бот для получения подборки отелей (с картинками или без) с сайта-агрегатора hotels.com

Для начала работы вводится команда /start или /help и выбирается один из вариантов работы

__Поддерживаются только регионы США__

## Установка

### Настройка проекта
(из папки проекта)
```sh
python3 -m venv venv                    # создание виртуальной среды в папке `pythonenv`
source venv/Scripts/activate                # активация среды
pip install -r requirements.txt         # загрузка необходимых пакетов
```

### Настройка API
- Зарегистрироваться на https://rapidapi.com/
- Подписаться на https://rapidapi.com/apidojo/api/hotels4
- Внести X-RapidAPI-Key в api-key.txt

### Настройка бота
- Создать бота https://core.telegram.org/bots
- Внести токен бота в token.txt

## Команды

- /start; /help — помощь по командам бота
- /lowprice — вывод самых дешёвых отелей в указанном городе
- /highprice — вывод самых дорогих отелей в указанном городе
- [WIP] /best_deal
- /history — вывод истории поиска отелей.