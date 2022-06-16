import os
import sys
import time
import requests
import urllib3
from dotenv import load_dotenv
import logging
import pandas as pd
from pandas.io.json import json_normalize
import json

import pandas as pd
from pandas.io.json import json_normalize
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import email, smtplib, ssl
 
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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
# PROXIES = {'http': "socks5://72.195.34.59:4145", 'https': "socks5://72.195.34.59:4145"}

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
        my_dataset = requests.get(activites_url, headers=header, params=param).json()
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
        access_token, refresh_token = get_tokens(refresh_token)
        my_dataset = get_dataset(access_token)
        # with open('sample.json', 'r', encoding='utf-8') as f:
        #     my_dataset = json.load(f)
        activities = pd.json_normalize(my_dataset)
        cols = ['name', 'upload_id', 'type', 'distance', 'moving_time',   
                'average_speed', 'max_speed','total_elevation_gain',
                'start_date_local'
            ]
        activities = activities[cols]
        activities['start_date_local'] = pd.to_datetime(activities['start_date_local'])
        activities['start_time'] = activities['start_date_local'].dt.time
        activities['start_date_local'] = activities['start_date_local'].dt.date
        # rides = activities.loc[activities['type'] == 'Ride']
        print(activities.head(5))
        with open('activities_list.csv', 'w', encoding='utf-8') as f:
            my_dataset = activities.to_csv(f)
        sendmail('activities_list.csv')
    except Exception as e:
        logger.error(f'Функция: {__name__}. Ошибка: {e}')


if __name__ == '__main__':
    main()
