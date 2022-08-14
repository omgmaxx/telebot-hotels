from telebot import types, TeleBot
from telebot.types import Message, CallbackQuery
from requests import request
from json import loads, dump
from re import sub
from typing import Any, Optional
from datetime import datetime


def value_check(value: Any, chat_id: int, limit: int) -> bool:
    """
    Функция, проверяющая, является ли значение int'ом и входит ли он в диапазон 0->limit

    Args:
        value (Any): проверяемое значение
        chat_id (int): ID чата
        limit (int): лимит значений
    """
    try:
        int(value)
    except ValueError:
        bot.send_message(chat_id, 'Не числовое значение')
        return False
    if not limit >= int(value) > 0:
        bot.send_message(chat_id, 'Вне области значений')
        return False
    return True


def time_check(date: str, chat_id: int) -> bool:
    try:
        datetime.strptime(date, '%d-%m-%Y')
    except ValueError:
        bot.send_message(chat_id, 'Неверный формат')
        return False
    return True


def show_photos(chat_id: int, hotel_media: list[str]) -> None:
    """
    Функция, отправляющая в указанный чат фотографии из списка ссылок

    Args:
        chat_id (int): ID чата
        hotel_media (list[str]): список ссылок на фотографии
    """
    photo_array = list()
    link_cnt = 0
    for img_link in hotel_media:
        link_cnt += 1
        photo_array.append(types.InputMediaPhoto(img_link))
        if link_cnt == 5:
            bot.send_media_group(chat_id, photo_array)
            link_cnt = 0
            photo_array = list()
    else:
        bot.send_media_group(chat_id, photo_array)


def create_search_instance(command: str, user_id: int, date: str) -> dict[str | int | dict]:
    """
    Инициализация инстанса кэша поиска

    Args:
        command (str): задаваемая команда
        user_id (int): ID пользователя
        date (str): дата запроса

    :return: словарь - инстанс кэша поиска
    """
    search = {
        'search_date': date,
        'command': command,
        'city_id': 0,
        'city_name': '',
        'hotel_amt': 0,
        'photo_amt': 0,
        'start_date': '',
        'end_date': '',
        'hotel': dict()
    }

    global search_cache
    search_cache[user_id] = search
    return search


""" ================== Инициализация ================== """


# Кэш с персонифицированными под-словарями
search_cache = dict()

# Десериализация token.txt
with open('token.txt', 'r') as txt:
    token = txt.read()

# Инициализация бота
bot: TeleBot = TeleBot(token)

# Ключи к api
with open('api-key.txt', 'r') as txt:
    api_key = txt.read()
api_headers: dict[str: str] = {
    "X-RapidAPI-Host": "hotels4.p.rapidapi.com",
    "X-RapidAPI-Key": api_key
}

# Ссылки для запросов
api_url: str = "https://hotels4.p.rapidapi.com/locations/v2/search"
list_url: str = "https://hotels4.p.rapidapi.com/properties/list"
photo_url: str = "https://hotels4.p.rapidapi.com/properties/get-hotel-photos"

# Ключи для запросов
sort_orders: dict[str: str] = {
    'low_price': 'PRICE',
    'high_price': 'PRICE_HIGHEST_FIRST',
    'best_deal': 'DISTANCE_FROM_LANDMARK'
}


""" ================== Команды ================== """


@bot.message_handler(commands=['help', 'start'])
def start_work(message: Message) -> None:
    """
    Стартовая функция

    Args:
        message (Message): вся информация о сообщении
    """

    bot.send_message(message.chat.id, '/low_price - Узнать топ самых дешёвых отелей в городе\n'
                                      '/high_price - Узнать топ самых дорогих отелей в городе\n'
                                      # '/best_deal - Узнать топ отелей, '
                                      # 'наиболее подходящих по цене и расположению от центра\n'
                                      '/history - Узнать историю поиска отелей')


@bot.message_handler(commands=['low_price'])
def low_price(message: Message) -> None:
    """
    Запрос самых дешёвых

    Args:
        message (Message): вся информация о сообщении
    """
    create_search_instance(
        'low_price',
        message.chat.id,
        datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    )
    ask_start_time(message)


@bot.message_handler(commands=['high_price'])
def high_price(message: Message) -> None:
    """
    Запрос самых дорогих отелей

    Args:
        message (Message): вся информация о сообщении
    """
    create_search_instance(
        'high_price',
        message.chat.id,
        datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    )
    ask_start_time(message)


@bot.message_handler(commands=['best_deal'])
def best_deal(message: Message) -> None:
    """
    Запрос отелей по лучшим условиям

    Args:
        message (Message): вся информация о сообщении
    """
    create_search_instance(
        'best_deal',
        message.chat.id,
        datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    )
    ask_start_time(message)


@bot.message_handler(commands=['history'])
def history(message: Message) -> None:
    """
    Запрос истории запросов

    Args:
        message (Message): вся информация о сообщении
    """
    markup = types.ForceReply(selective=False)
    msg = bot.send_message(message.chat.id,
                           'Сколько последних запросов из истории берём? (не более 10)',
                           reply_markup=markup)
    bot.register_next_step_handler(msg, history_result)


@bot.message_handler(content_types=['text'])
def unknown_command(message: Message) -> None:
    """
    Ответ на неизвестный запрос

    Args:
        message (Message): вся информация о сообщении
    """
    bot.send_message(message.chat.id, 'Неизвестная команда. Попробуйте /start или /help')


""" ================== Действия ================== """


def history_result(message: Message) -> None:
    """
    Выдача результатов запроса истории

    Args:
        message (Message): вся информация о сообщении
    """
    user_id = message.chat.id
    if not value_check(message.text, user_id, 10):
        history(message)
        return

    # Открытие файла истории
    try:
        with open('history.json', 'r', encoding='utf-8') as file:
            history_json = loads(file.read())
    except FileNotFoundError:
        bot.send_message(user_id, 'Нет сохранённой истории')
        return

    # Запрос к истории запросов юзера
    search_list = history_json['user_id'][str(user_id)][: -int(message.text)-1: -1]
    for search_instance in search_list:

        # Сбор информации о запросе
        search_input = '==============================\n' \
                       f'Запрос: [{search_instance["command"]}]\n' \
                       f'Время запроса: [{search_instance["search_date"]}]\n' \
                       f'Город: [{search_instance["city_name"]}]\n' \
                       f'Количество отелей: [{search_instance["hotel_amt"]}]\n' \
                       f'Количество фотографий: [{search_instance["photo_amt"]}]\n' \
                       '=============================='
        bot.send_message(user_id, search_input)

        # Вывод всей информации, полученной из запроса
        for hotel in search_instance['hotel']:
            hotel = search_instance['hotel'][hotel]
            bot.send_message(user_id, hotel['message'])
            if hotel['media']:
                show_photos(user_id, hotel['media'])


def ask_start_time(message: Message) -> None:
    """
    Функция, запрашивающая время записи

    Args:
        message (Message): вся информация о сообщении
    """
    markup = types.ForceReply(selective=False)
    msg = bot.send_message(message.chat.id,
                           'На какое время записываемся? (формат записи "DD-MM-YYYY")',
                           reply_markup=markup)
    bot.register_next_step_handler(msg, ask_end_time)


def ask_end_time(message: Message) -> None:
    """
    Функция, запрашивающая время выписки

    Args:
        message (Message): вся информация о сообщении
    """
    user_id = message.chat.id

    # Проверка на формат
    if not time_check(message.text, user_id):
        ask_start_time(message)
        return

    # Проверка на соответствие дат
    cur_date = datetime.now().strftime("%d-%m-%Y")
    if cur_date > message.text:
        bot.send_message(user_id, 'Нельзя бронировать на прошедшую дату')
        ask_start_time(message)
        return

    search_cache[user_id]['start_date'] = message.text

    markup = types.ForceReply(selective=False)
    msg = bot.send_message(user_id,
                           'До какого времени записываемся? (формат записи DD-MM-YYYY)',
                           reply_markup=markup)
    bot.register_next_step_handler(msg, ask_town, message.text)


def ask_town(message: Message, start_date: Optional[str] = None) -> None:
    """
    Функция, запрашивающая город

    Args:
        message (Message): вся информация о сообщении
        start_date (str): дата записи
    """
    user_id = message.chat.id

    if not search_cache[user_id]['end_date']:
        # Проверка на формат
        if not time_check(message.text, user_id):
            ask_end_time(message)
            return

        # Проверка на соответствие дат
        if start_date > message.text:
            bot.send_message(user_id, 'Нельзя выписаться до дня записи')
            ask_end_time(message)
            return

    search_cache[user_id]['end_date'] = message.text

    markup = types.ForceReply(selective=False)
    msg = bot.send_message(message.chat.id, 'В каком городе ищем?', reply_markup=markup)
    bot.register_next_step_handler(msg, choose_town)


def choose_town(message: Message) -> None:
    """
    Функция, уточняющая выбор города

    Args:
        message (Message): вся информация о сообщении
    """
    user_id = message.chat.id

    # Запрос информации о совпадениях с названием запрошенного города
    querystring = {
        "query": message.text,
        "locale": "en_US",
        "currency": "USD"
    }
    response = request("GET", api_url, headers=api_headers, params=querystring)
    city_json = loads(response.text)

    # Составление списка совпадений
    cities_list = dict()
    try:
        if "CITY_GROUP" in city_json["suggestions"][0]["group"]:
            for city in city_json["suggestions"][0]["entities"][:10]:
                cities_list[city["name"]] = f'id_{city["destinationId"]}_{city["name"]}'
        else:
            raise ImportError('Нет CITY_GROUP')
    except ImportError as e:
        bot.send_message(user_id, e.msg)

    # Совпадений не найдено
    if not cities_list:
        bot.send_message(user_id, "Ничего не найдено, попробуйте другой запрос")
        ask_town(message)
        return

    # Создание кнопок
    markup = types.InlineKeyboardMarkup()
    for city, dest_id in cities_list.items():
        markup.add(types.InlineKeyboardButton(city, callback_data=dest_id))
    bot.send_message(user_id, "Уточните город", reply_markup=markup)


@bot.callback_query_handler(lambda msg: msg.data[:3] == 'id_')
def ask_quantity(call: CallbackQuery) -> None:
    """
    Функция, спрашивающая, сколько искать отелей

    Args:
        call (CallbackQuery): вся информация о вызове (включая call.message - содержание изначального сообщения)
    """
    city = call.data.split('_')
    user_id = call.message.chat.id

    search_cache[user_id]['city_id'] = int(city[1])
    search_cache[user_id]['city_name'] = city[2]

    bot.edit_message_reply_markup(user_id, call.message.id)
    bot.edit_message_text('Вы выбрали: {}'.format(search_cache[user_id]['city_name']),
                          user_id,
                          call.message.id)

    markup = types.ForceReply(selective=False)
    msg = bot.send_message(user_id, 'Сколько отелей ищем (не более 10)', reply_markup=markup)
    bot.register_next_step_handler(msg, ask_photos, call)


def ask_photos(message: Message, call: CallbackQuery) -> None:
    """
    Функция, спрашивающая, нужны ли фотографии

    Args:
        message (Message): вся информация о сообщении
        call (CallbackQuery): вся информация о вызове (включая call.message - содержание изначального сообщения)
    """
    user_id = message.chat.id

    if not value_check(message.text, user_id, 10):
        ask_quantity(call)
        return

    search_cache[user_id]['hotel_amt'] = int(message.text)

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Да", callback_data='ph_yes'),
               types.InlineKeyboardButton("Нет", callback_data='ph_no'))
    bot.send_message(user_id, 'Показывать фотографии?', reply_markup=markup)


@bot.callback_query_handler(lambda msg: msg.data[:3] == 'ph_')
def ask_photo(call: CallbackQuery) -> None:
    """
    Функция запроса количества фотографий

    Args:
        call (CallbackQuery): вся информация о вызове (включая call.message - содержание изначального сообщения)
    """

    user_id = call.message.chat.id

    if call.data == 'ph_yes':
        markup = types.ForceReply(selective=False)
        msg = bot.send_message(user_id, 'Сколько фотографий предоставить (не более 15)', reply_markup=markup)
        bot.register_next_step_handler(msg, show_result, call)
        res = 'Да'

    elif call.data == 'ph_no':
        search_cache[user_id]['photo_amt'] = 0
        res = 'Нет'
        show_result(call.message, call)

    else:
        raise ValueError('Неверный ввод')

    bot.edit_message_reply_markup(user_id, call.message.id)
    bot.edit_message_text('Вы выбрали: '+res, user_id, call.message.id)


def show_result(message: Message, call: CallbackQuery,
                price_min: Optional[int] = None, price_max: Optional[int] = None) -> None:
    """
    Функция сбора и вывода информации

    Args:
        message (Message): вся информация о сообщении
        call (CallbackQuery): вся информация о вызове (включая call.message - содержание изначального сообщения)
        price_min (Optional[int]): минимальное значение цены
        price_max (Optional[int]): максимальное значение цены
    """
    user_id = message.chat.id

    if call.data != 'ph_no':
        if not value_check(message.text, user_id, 15):
            ask_photo(call)
            return
        search_cache[user_id]['photo_amt'] = int(message.text)

    # Составление и отправка запроса в api
    dest_id, hotel_amt, command = map(str, [search_cache[user_id]['city_id'],
                                            search_cache[user_id]['hotel_amt'],
                                            search_cache[user_id]['command']]
                                      )
    querystring = {
        "destinationId": dest_id,
        "pageNumber": "1",
        "pageSize": hotel_amt,
        "checkIn": "2020-01-08",
        "checkOut": "2020-01-15",
        "adults1": "1",
        "sortOrder": sort_orders[command],
        "locale": "en_US",
        "currency": "USD"
    }

    # Дополнения для команды best_deal
    if search_cache[user_id]['command'] == 'best_deal':
        querystring.update(priceMin=price_min, priceMax=price_max, landmarkIds="City center")

    response = request("GET", list_url, headers=api_headers, params=querystring)
    search_list_json = loads(response.text)

    # Сбор информации из полученного json по региону
    for x in search_list_json['data']['body']['searchResults']['results']:
        try:
            hotel_id = x['id']
            search_cache[user_id]['hotel'][hotel_id] = {'message': '', 'media': list()}
            hotel_info = ''

            hotel_info += '{: <10} {}'.format(
                'Название: ', x['name'])

            hotel_info += '\n{: <10} {}'.format(
                'Стоимость: ', x['ratePlan']['price']['current'])

            try:
                hotel_info += '\n{: <10} {}'.format(
                    'Адрес: ', x['address']['streetAddress'])
                hotel_info += '\n{: <10} {}'.format(
                    '', x['address']['extendedAddress'])

            except KeyError:
                hotel_info += '\n{: <10} {}'.format(
                    'Адрес: ', x['address']['locality'])

            for y in x['landmarks']:
                if y['label'] == 'City center':
                    distance = float(y['distance'].split()[0])
                    distance = round(distance * 1609.344 / 1000, 1)   # Мили -> Километры
                    hotel_info += '\n{: <10} {} км'.format(
                        'От центра: ', str(distance))

            # Вывод описания
            search_cache[user_id]['hotel'][hotel_id]['message'] = hotel_info
            bot.send_message(user_id, hotel_info)

            # Получение фото к нынешнему сообщению
            if search_cache[user_id]['photo_amt']:
                querystring = {
                    "id": x['id']
                }
                response = request("GET", photo_url, headers=api_headers, params=querystring)
                res = loads(response.text)

                try:
                    for hotel_img in res['hotelImages'][:search_cache[user_id]['photo_amt']]:
                        link = hotel_img['baseUrl']
                        link = sub(r'\{size}', 'z', link)
                        search_cache[user_id]['hotel'][hotel_id]['media'].append(link)
                except Exception:
                    bot.send_message(user_id, 'Ошибка с получением фотографий.')

                # Вывод фотографий
                show_photos(user_id, search_cache[user_id]['hotel'][hotel_id]['media'])

        except KeyError:
            bot.send_message(user_id, 'Ошибка с получением результатов.')

    # Запись в историю
    try:
        with open('history.json', 'r') as file:
            history_json = loads(file.read())
    except FileNotFoundError:
        history_json = {'user_id': {}}

    if history_json['user_id'].get(str(user_id)):
        history_json['user_id'][str(user_id)].append(search_cache[user_id])
    else:
        history_json['user_id'][str(user_id)] = [search_cache[user_id]]

    with open('history.json', 'w') as file:
        dump(history_json, file, indent=4)

    # Очистка кэша поиска
    del search_cache[user_id]


if __name__ == '__main__':
    bot.infinity_polling()
