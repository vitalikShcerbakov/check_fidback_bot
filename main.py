import logging
import csv
import time
from datetime import datetime
from threading import Thread

import schedule
import telebot
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from telebot import types

from settings import TG_TOKEN

bot = telebot.TeleBot(TG_TOKEN)

logging.basicConfig(
    filename='app.log',
    filemode='w',
    format='%(name)s : %(levelname)s : %(message)s',
    datefmt='%d-%b-%y %H:%M:%S'
    )


TIME_SENDING_MESSAGE = 15
TIME_CHECK_VENDOR_CODE = 10
ADMIN_LIST = [
    816283898,   # Дима
    815599051,   # Я
    631613499,   # Наська
    ]

def crutch(lst):
    while True:
        if len(lst) < 5:
            lst.append(0)
        else:
            return lst
    
        


def check_fidback():
    result = read_from_datebase()
    list_vc: list[int] = [int(val[0]) for val in result if val is not None]
    list_vendor_code = []

    cls_name2 = 'comment-card__stars'

    # result = ['52232480','67578772','38272884','34964682','88107650','113068831','113068944']
    # list_vc = [int(val) for val in result]


    options_chrome = webdriver.ChromeOptions()
    options_chrome.add_argument('--headless')
    options_chrome.add_argument('--no-sandbox')
    s = Service('/usr/local/bin/chromedriver')

    with webdriver.Chrome(options=options_chrome, service=s) as browser:

        for i, vc in enumerate(list_vc):
            logging.info(f'running {vc}')
            line = []           
            print(round((i + 1) / len(list_vc) * 100), end=' ')
            url = f'https://www.wildberries.ru/catalog/{vc}/detail.aspx?targetUrl=BP'
            browser.get(url=url)
            time.sleep(3)
            browser.execute_script("window.scrollBy(0,1000)")
            time.sleep(2)
            browser.execute_script("window.scrollBy(0,2000)")
            line.append(vc)
            line.append(url)
            count = 0
            try:
                time.sleep(1)
                value = browser.find_elements(By.CLASS_NAME, cls_name2)
                
                for l in value:
                    logging.info(f'running {l}')
                    try:
                        result = l.get_attribute("class")
                        count += 1
                        number_of_stars = int(result[-1])
                        if number_of_stars < 4:
                            line.append(number_of_stars)
                        else:
                            line.append(number_of_stars)
                        if count == 3:
                            break
                    except Exception as e:
                        print(f'Error get_attribute("class") - {e}')
                        line.append('error')            
            except Exception as e:
                print(f'browser.find_elements(By.CLASS_NAME, cls_name2) - {e}')
            line = crutch(line)
            date_now = datetime.now()

            line.append(f'{date_now:%Y-%m-%d %H:%M:%S}')
            list_vendor_code.append(line)
    write_to_database(list_vendor_code)
    print('Новый список проверен и загружен')

def write_to_database(list_vc: list) -> None:
    with open('datebase.csv', 'w+') as csv_file:
        writer = csv.writer(csv_file)
        for line in list_vc:
            writer.writerow(line)


def read_from_datebase():
    result = []
    with open('datebase.csv', 'r') as csv_file:
        file_read = csv.reader(csv_file, delimiter=',', quotechar='|')
        for row in file_read:
            result.append(row)
    return result


def download_article_list(msg, user_id):
    if user_id in ADMIN_LIST:
        if '\n' in msg or ' ' in msg:
            list_vendor_code = msg.split()
            if all(value.isdigit() for value in list_vendor_code):
                list_vendor_code = list(map(int, list_vendor_code))
                list_vendor_code = [[vc, None, True, True, None] for vc in list_vendor_code]
                write_to_database(list_vendor_code)
                print('Список загружен')
                return True
    return False


def send_message():
    '''Функция рассылки сообщений пользователям'''
    users_id = []
    with open('users_datebase.txt', 'r') as file:
        file_read = file.readlines()
        for line in file_read:
            try:
                id, name, flag = line.split()
                if flag != 'False':
                    users_id.append(id)
            except Exception as e:
                print(f'Error added userd in list - send_message: {e}')
    data = read_from_datebase()
    for user in users_id:
        for line_text in data:
            fidback = list(map(int, line_text[2:5]))
            if [True for i in fidback if i < 4]:
                bot.send_message(user, f'{line_text[1]} - есть плохой отзыв',)
                print(line_text[1], line_text[2:5])

    
def notification_on_off(chad_id, flag):
    with open('users_datebase.txt', 'r') as file:
        data = file.readlines()
        new_data = []
        try:
            for i, line in enumerate(data):
                id, name, _ = line.split()
                if chad_id == int(id):
                    new_data.append(f'{id} {name} {flag} \n')
                else:
                    new_data.append(line)
        except Exception as e:
            print(f'Error - notification_on_off : {e}')
    with open('users_datebase.txt', 'w') as file:
        file.writelines(new_data)


@bot.message_handler(commands=['start'])
def start(message):
    with open('users_datebase.txt', 'r+') as file:
        data = file.readlines()
        list_id = []
        try:
            for line in data:
                id, name, flag = line.split()
                list_id.append(int(id))
        except Exception as e:
            print(e)

        if message.chat.id not in list_id:
            file.write(f'{message.chat.id} {message.from_user.first_name} {True} \n')

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Включить уведомления")
    btn2 = types.KeyboardButton("Выключить уведомления")
    btn3 = types.KeyboardButton("Просмотр товаров с плохими отзывами")
    btn4 = types.KeyboardButton("Полный просмотр")
    markup.add(btn1, btn2, btn3, btn4,)
    bot.send_message(
        message.chat.id, text="Привет, {0.first_name}! Теперь ты подписан(а) на рассылку =)"
        .format(message.from_user), reply_markup=markup)
    bot.send_message(
        message.chat.id, f'Уведомления будут приходить каждые {TIME_SENDING_MESSAGE} мин. \n'
                         f'eсли будут товары с плохими отзывами. \n'
                         f'Для загрузки нового списка артикулов \n'
                         f'тебе нужно быть администратором. \n'
                         f'Введи спискок через запятую  или пробел - \n'
                         f'xxxxxxx, xxxxxxx, xxxxxx, xxxxxx \n'
                         f'Или каждый с новой строки - \n'
                         f'xxxxxxx \n'
                         f'xxxxxxx \n'
                         f'xxxxxxx \n'
                         f'xxxxxxx \n')
        

@bot.message_handler(regexp="test")
def handle_message(message):
    users_id = []
    with open('users_datebase.txt', 'r') as file:
        file_read = file.readlines()
        for line in file_read:
            try:
                id, name, flag = line.split()
                if flag != 'False':
                    users_id.append(id)
            except Exception as e:
                print(f'Error added userd in list - send_message: {e}')
    for user in users_id:
        bot.send_message(user, f'Что нового:\n'
                'Добавлена кнопка очистки чата, для ее активации введите /start но перед этим рекомендуется очистить полностью чат')


@bot.message_handler(content_types=['text'])
def func(message):
    if (message.text == "Включить уведомления"):
        notification_on_off(message.chat.id, True)
        bot.send_message(
            message.chat.id, 'Уведомления включены')

    elif (message.text == "Выключить уведомления"):
        notification_on_off(message.chat.id, False)
        bot.send_message(
            message.chat.id, 'Уведомления выключены')

    elif message.text == 'Просмотр товаров с плохими отзывами':
        answer = read_from_datebase()
        for line in answer:
            fidback = list(map(int, line[2:5]))
            if [True for i in fidback if i < 4]:
                bot.send_message(message.chat.id, f'{line[1]} - есть плохой отзыв',)
                print(line[1], line[2:5])    

        # if all(list([True if val[3] == 'True' else False for val in answer])):
        #     bot.send_message(message.chat.id, 'Нет товаров c плохими отзывами 😉')
        # else:
        #     bot.send_message(message.chat.id, 'Срочно что то сделать 😕')
        # bot.send_message(
        #     message.chat.id, f'Время последней проверки: {line[-1]}')


    elif message.text == 'Полный просмотр':
        answer = read_from_datebase()
        for line in answer:
            bot.send_message(message.chat.id, f'{line[1]} {line[2:5]}')
        bot.send_message(
            message.chat.id, f'Время последней проверки: {line[-1]}')
            
    
    elif message.text == 'Удалить сообщения':
        for i in range(int(message.message_id), 1, -1):
            try:             
                message.message_id = i
                bot.delete_message(message.chat.id, message.message_id)
            except Exception:
                break


    else:
        if download_article_list(message.text, message.chat.id):
            bot.send_message(message.chat.id, 'Cписок загружен')
        else:
            bot.send_message(
                message.chat.id, 'Некорректный ввод нажми /start')


def sheduler():
    schedule.every(TIME_CHECK_VENDOR_CODE).minutes.do(check_fidback)
    schedule.every(TIME_SENDING_MESSAGE).minutes.do(send_message)
    while True:
        schedule.run_pending()
        time.sleep(1)


def main():
    Thread(target=sheduler, args=()).start()
    bot.polling(none_stop=True, timeout=5, interval=1)

    while True:
        try:
            bot.polling(non_stop=True, interval=0)
        except Exception as e:
            print(e)
            time.sleep(5)
            continue


if __name__ == '__main__':
    main()
