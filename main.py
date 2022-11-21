import json
import logging
import os
import smtplib
import ssl
import sys
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import matplotlib.pyplot as plt
import numpy as np  # linear algebra
import pandas as pd  # data processing, CSV file I/O (e.g. pd.read_csv)
import requests
import seaborn as sns
import urllib3
from dotenv import load_dotenv
from IPython.display import display
from pandas.io.json import json_normalize


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding='utf-8',
    handlers=[
        logging.FileHandler(filename="debug.log", mode='w'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

SLEEP_TIME = 600
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
REFRESH_TOKEN = os.getenv('REFRESH_TOKEN')
MAIL_SMTP_SERVER = os.getenv('MAIL_SMTP_SERVER')
MAIL_FROM = os.getenv('MAIL_FROM')
MAIL_FROM_PASSW = os.getenv('MAIL_FROM_PASSW')
MAIL_TO = os.getenv('MAIL_TO')

auth_url = "https://www.strava.com/api/v3/oauth/token"
activites_url = "https://www.strava.com/api/v3/athlete/activities"


def get_tokens(refresh_token):
    if refresh_token == '':
        refresh_token = REFRESH_TOKEN
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'refresh_token': refresh_token,
        'grant_type': "refresh_token",
        'f': 'json'
    }
    try:
        res = requests.post(auth_url, data=payload, verify=False).json()
        access_token = res['access_token']
        refresh_token = res['refresh_token']
        logger.info(f'Токены успешно получены.')
        return access_token, refresh_token
    except Exception as e:
        logger.error(f'Ошибка получения токенов (функция: {__name__}): {e}')


def get_dataset(access_token):
    try:
        header = {'Authorization': 'Bearer ' + access_token}
        param = {'per_page': 200, 'page': 1}
        my_dataset = requests.get(
            activites_url, headers=header, params=param).json()
        return my_dataset
    except Exception as e:
        logger.error(f'Функция: {__name__}. Ошибка: {e}')


def sendmail(filename):
    try:
        subject = "Список тренировок"
        body = "Список тренировок"
        sender_email = MAIL_FROM
        receiver_email = MAIL_TO
        password = MAIL_FROM_PASSW

        # Создание составного сообщения и установка заголовка
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = receiver_email
        message["Subject"] = subject
        message["Bcc"] = receiver_email  # Если у вас несколько получателей

        # Внесение тела письма
        message.attach(MIMEText(body, "plain"))

        filename = filename  # В той же папке что и код

        # Открытие PDF файла в бинарном режиме
        with open(filename, "rb") as attachment:
            # Заголовок письма application/octet-stream
            # Почтовый клиент обычно может загрузить это автоматически в виде вложения
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())

        # Шифровка файла под ASCII символы для отправки по почте
        encoders.encode_base64(part)

        # Внесение заголовка в виде пара/ключ к части вложения
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {filename}",
        )

        # Внесение вложения в сообщение и конвертация сообщения в строку
        message.attach(part)
        text = message.as_string()

        # Подключение к серверу при помощи безопасного контекста и отправка письма
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(MAIL_SMTP_SERVER, 465, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, text)
        logger.info('Сообщение успешно отправлено.')

    except Exception as e:
        logger.error(f'Функция: {__name__}. Ошибка: {e}')


def main():
    refresh_token = ''
    try:
        # access_token, refresh_token = get_tokens(refresh_token)
        # my_dataset = get_dataset(access_token)
        with open('response.json', 'r', encoding='utf-8') as f:
            my_dataset = json.load(f)
        # df = pd.json_normalize(my_dataset)
        result = ''
        for item in my_dataset:
            if str(item['map']['summary_polyline']) != 'None':
                result += "'" + str(item['map']['summary_polyline']) + "',\n"

        with open('tracks.json', 'w', encoding='utf-8') as f:
            f.write(result)

    except Exception as e:
        logger.error(f'Функция: {__name__}. Ошибка: {e}')


# -------------------------------------------------------------------------

pd.options.display.float_format = '{:.1f}'.format
DISPL_COUNT = 5

with open('response.json', 'r', encoding='utf-8') as f:
    my_dataset = json.load(f)

df = pd.json_normalize(my_dataset)

df = df[df['type'] == 'Ride']

df['start_date_local'] = pd.to_datetime(df['start_date_local'])
df['start_time'] = df['start_date_local'].dt.time
df = df.assign(avg_move_spd_kmh=df['average_speed'] * 3.6)
df = df.assign(avg_total_spd_kmh=df['distance'] / df['elapsed_time'] * 3.6)
df = df.assign(avg_elev_perc=df['total_elevation_gain'] / df['distance'] * 100)
df = df.assign(dist_km=df['distance'] / 1000)
df = df.assign(start_date_r=df.start_date_local.dt.strftime('%d.%m.%Y'))
df = df.assign(start_my=df.start_date_local.dt.strftime('%Y.%m'))
df = df.assign(start_time_r=df.start_date_local.dt.strftime('%H:%M'))
df = df.assign(month=df.start_date_local.dt.month)
df = df.assign(weekday=df.start_date_local.dt.weekday)
df = df.fillna(0)
df['gear_id'] = df['gear_id'].replace(to_replace='b7149139', value='Corratec Corones')
df['gear_id'] = df['gear_id'].replace(to_replace='b6130097', value='GT Agressor')
df['gear_id'] = df['gear_id'].replace(to_replace='b8541718', value='Nishiki')
df['gear_id'] = df['gear_id'].replace(to_replace='b6856164', value='ХВЗ')

# ------------------------------- вывод данных ------------------------------

# display(pd.pivot_table(df, index=['id']))

print(f"Пробег на велосипеде всего: {df['dist_km'].sum().round(1)} км")

print("")

print(f"Средняя скорость (только в движении): {df['avg_move_spd_kmh'].mean().round(1)} км/ч")
print("...в том числе по велосипедам:")
display(df.groupby('gear_id').agg({'avg_move_spd_kmh':'mean', 'dist_km':'sum'})\
      .sort_values(by='avg_move_spd_kmh', axis=0, ascending=False)\
      .rename(columns={'gear_id':'Велосипед', 'avg_move_spd_kmh':'V движ.ср., км/ч','dist_km':'Общий пробег, км'}))

print("")

print(f"Средняя скорость (с учетом стоянок): {df['avg_total_spd_kmh'].mean().round(1)} км/ч")
print("...в том числе по велосипедам:")
display(df.groupby('gear_id').agg({'avg_total_spd_kmh':'mean', 'dist_km':'sum'})\
      .sort_values(by='avg_total_spd_kmh', axis=0, ascending=False)\
      .rename(columns={'gear_id':'Велосипед', 'avg_total_spd_kmh':'V полн. ср., км/ч','dist_km':'Общий пробег, км'}))

print("")

print(f"Средний набор высоты: {df['avg_elev_perc'].mean().round(2)} %")
print("...в том числе по велосипедам:")
display(df.groupby(['gear_id'])[['gear_id', 'avg_elev_perc']].mean()\
      .sort_values(by='avg_elev_perc', axis=0, ascending=False)\
      .rename(columns={'gear_id':'Велосипед', 'avg_elev_perc':'Средн. набор, %'})\
      .style.format(precision=2))

print("")

print(f"Кол-во поездок по дням недели:")
display(df.groupby(['weekday']).agg({'weekday':'count', 'dist_km':'sum'})\
      .rename(columns={'weekday':'Кол-во заездов', 'dist_km':'Дистанция, км'})\
      .style.format(precision=1).background_gradient(cmap='Blues'))

print("")

print(f"Пробег по месяцам года:")
df_moy = df.groupby(['month']).agg({'month':'count', 'dist_km':'sum'})\
        .rename({'month':'Месяц', 'dist_km':'дистанция, км'})\
        
display(df_moy.style.format(precision=1).background_gradient(cmap='Blues'))

df_moy[['month', 'dist_km']].plot(kind="pie", label="", subplots=True)

print("")

print(f"Показатели за все время, по месяцам:")
display(df.groupby(['start_my']).agg({'dist_km':'sum', 'avg_move_spd_kmh':'mean', 'avg_total_spd_kmh':'mean', 'avg_elev_perc':'mean'})\
        .rename(columns={'start_my':'Месяц', 'dist_km':'Дистанция, км', 'avg_move_spd_kmh':'Vср.движ., км/ч', 'avg_total_spd_kmh':'Vср.полн., км/ч', 'avg_elev_perc':'Средн. набор, %'})\
        .style.format(precision=1).background_gradient(cmap='Blues'))
              
print("")

print(f"Последние {DISPL_COUNT} тренировок:")
display(df[['name', 'start_date_r', 'start_time_r', 'dist_km', 'avg_move_spd_kmh', 'avg_total_spd_kmh', 'avg_elev_perc']]\
          .head(DISPL_COUNT)\
          .rename(columns={'name':'Название', 'start_date_r':'Дата','start_time_r':'Время','dist_km':'Дистанция, км',\
                 'avg_move_spd_kmh':'V движ.ср., км/ч','avg_total_spd_kmh':'V полн.ср., км/ч','avg_elev_perc':'Средн. набор, %'})\
          .style.format(precision=1))
