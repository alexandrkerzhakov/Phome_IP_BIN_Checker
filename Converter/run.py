import json
import os
import re
import shutil
from urllib.request import urlopen
import cv2
import easyocr
import numpy as np
import requests
from PIL import Image
from pdf2image import convert_from_path
from operators import OPERATORS


class Converter:
    # инициализация экземпляра класса Converter
    def __init__(self):
        self.CURRENT = os.path.join(os.getcwd(), 'CURRENT') # папка с исходными файлами в формате .png
        self.UPDATE = os.path.join(os.getcwd(), 'UPDATE') # папка с обновленными (после удаления "шумов") файлами в формате .png
        self.TEXT = os.path.join(os.getcwd(), 'TEXT') # папка с текстовыми файлами в формате .txt
        self.EXCEL = os.path.join(os.getcwd(), 'EXCEL') # папка с текстовыми файлами в формате .xls
        self.SHARE = os.path.join(os.getcwd(), 'SHARE') # папка с исходными файлами в формате .pdf

    # конвертация PDF в картину (pdf-->ppm-->png)
    def CONVERT_PDF_TO_CURRENT_IMAGE(self):
        if self.CURRENT:
            shutil.rmtree(self.CURRENT, ignore_errors=True) # удаляем папку self.CURRENT
        os.makedirs(self.CURRENT) # создаем папку self.CURRENT

        os.chdir(str(self.SHARE)) # смена директории
        list_files = os.listdir() # список файлов
        for f in list_files:
            name = f.replace(".pdf", "")
            convert_from_path(f, size=4000, dpi=600, output_file=name, output_folder=self.CURRENT)

            os.chdir(str(self.CURRENT))
            list_ppm = os.listdir()
            for ppm in list_ppm:
                if not ppm.endswith('png'):  # если не заканчивается на png
                    file_name = (ppm.replace(".ppm", "") + ".png")
                    file = Image.open(ppm)
                    file.save(file_name, 'png')
                    os.remove(ppm) # удаляем файл в формате ppm
            os.chdir(str(self.SHARE))

    # убираем точки
    def CONVERT_UPDATE_IMAGE(self):
        if self.UPDATE:
            shutil.rmtree(self.UPDATE, ignore_errors=True)
        os.makedirs(self.UPDATE)

        os.chdir(str(self.CURRENT))
        list_files = os.listdir(self.CURRENT)
        for file in list_files:
            img = cv2.imread(self.CURRENT + '\\' + file)
            img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)  # конвертация в серый
            kernel_dil = np.ones((1, 1), np.uint8)
            image_dil = cv2.dilate(img_gray, kernel_dil, iterations=3)  # дилатация
            kernel_erode = np.ones((1, 1), np.uint8)
            image_erode = cv2.erode(image_dil, kernel_erode, iterations=3)  # эрозия
            image_morph = cv2.morphologyEx(image_erode, cv2.MORPH_CLOSE, kernel_erode)  # морфологическая конвертация
            image_blur = cv2.medianBlur(image_morph, 3)  # чистка блура
            cv2.imwrite(self.UPDATE + '\\' + file, image_blur) # запись файла в папку self.UPDATE

    # конвертация картинки в текст
    def CONVERT_IMG_TO_TEXT(self):
        if self.TEXT:
            shutil.rmtree(self.TEXT, ignore_errors=True)
        os.makedirs(self.TEXT)

        os.chdir(str(self.UPDATE))
        list_files = os.listdir(self.UPDATE)
        for file in list_files:
            print(file)
            reader = easyocr.Reader(['en'], gpu=True)  # в зависимости от языка текста столбцах между датой (датами) и IP-адресами
            # reader = easyocr.Reader(['ru'], gpu=True) # русский язык
            result = reader.readtext(self.UPDATE + '\\' + file, detail=0)  # list
            os.chdir(str(self.TEXT))
            text_file = open(file.replace('.png', '.txt'), 'w+')

            for r in result:
                text_file.write(r + " , ")
            print(result)
        os.chdir(str(self.UPDATE))

    # парсинг данных из текстового файла
    def CHECK_IP_PHONE_BIN_DATA_TXT(self):

        os.chdir(str(self.TEXT))
        list_files = os.listdir(self.TEXT)

        for file in list_files:
            f = open(file, 'r')
            for line in f:
                print("Анализируем - " + file)
                list_ip = re.findall('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', line)  # list IP
                list_phone = re.findall('\+?\d{10,14}', line)  # list PHONE
                list_bin = re.findall(r"\b\d{6}\b", line)  # list BIN

                for ip in list_ip:
                    response = urlopen("http://ipwhois.app/json/" + ip + "?lang=ru")  # http.client.HTTPResponse object
                    try:
                        jsonip = json.load(response)
                        print("IP-адрес : " + jsonip['ip'])
                        print("Страна: " + jsonip['country'])
                        print("Регион: " + jsonip['region'])
                        print("Город: " + jsonip['city'])
                        for key in OPERATORS.keys():
                            if jsonip['isp'] == key:
                                print("Провайдер: " + OPERATORS.get(key))
                                break
                        else:
                            print("Провайдер: " + jsonip['isp'])
                    except Exception:
                        print("IP-адрес : " + ip + " является IP-адресом локальной вычислительной сети")
                    print()

                list_phone_temp = [] # временный список для стирания "+", добавления "7" перед "9" или "4"
                list_phone_update = [] # обновленный список с уникальными значениями phone

                for phone in list_phone:
                    if not phone.startswith("0"): # проверка на '0'
                        # не начинатеся на '7' и затем идут цифры '9' или '4' и длина равна 10
                        if not phone.startswith("7") and len(phone) == 10 and (phone.startswith("9") or phone.startswith("4")) :
                            new_phone = "7" + phone
                            list_phone_temp.append(new_phone)
                        elif phone.startswith("+"):  # проверка на '+'
                            new_phone = phone[phone.find("+") + 1:]
                            list_phone_temp.append(new_phone)
                        elif not phone.startswith("+"):  # проверка на '+'
                            list_phone_temp.append(phone)
                [list_phone_update.append(phone) for phone in list_phone_temp if phone not in list_phone_update]

                for phone in list_phone_update:
                    # print(phone)
                    # response = requests.get(f"https://www.kody.su/api/v2.1/search.json?q={phone}&key=KEY FROM KODY.SU")
                    if response.status_code == 200:
                        try:
                            value_list = response.json()['numbers']
                            for v in value_list: # list --> dict
                                if v['number_type_str'] == 'ru_mobile': # 1 (российский мобильный)
                                    if v['bdpn'] == True:
                                        print("Абонентский номер " + phone + " принадлежит номерной емкоcти оператора связи " +
                                              v['operator_full'].replace('&quot;', '') + " " + v['region'] + ", " +
                                              "происходила смена номерной емкости на оператора связи " +
                                              v['bdpn_operator'] + ".")
                                    else:
                                        print("Абонентский номер " + phone + " принадлежит номерной емкоcти оператора связи " +
                                              v['operator_full'].replace('&quot;', '') + " " + v['region'] + ".")

                                elif v['number_type_str'] == 'ru_fixed': # 2 (ip-телефония)
                                    print("Абонентский номер " + phone + " принадлежит номерной емкоcти оператора связи " +
                                          v['operator_full'].replace('&quot;', '') + " " + v['region'] + ".")

                                elif v['number_type_str'] == 'other': # 3 (иностранный)
                                    print("Абонентский номер " + phone +
                                          " является иностранным, выделялся оператором связи страны " + v['country'] + ".")
                        except Exception:
                            print("Problem)")
                    else:
                        print("Connection Error")

                list_bin_update = [] # обновленный список с уникальными значениями bin
                [list_bin_update.append(bin) for bin in list_bin if bin not in list_bin_update]

                for bin in list_bin_update:
                    payload = {}
                    headers = {"apikey": "KEY FROM APILAYER.COM"}
                    URL = f"https://api.apilayer.com/bincheck/{bin[0:6]}"
                    response = requests.request("GET", URL, headers=headers, data=payload)
                    if response.status_code == 200:
                        try:
                            res = response.text # string
                            res_dict = json.loads(res)
                            print("Банковская карта bin " + bin[0:6] +
                                  " эмитирована банком " + res_dict['bank_name'] + " (" + res_dict['country'] + ").")
                        except Exception:
                            print("Problem)")
                    else:
                        print("Connection Error")

# точка входа программы
if __name__ == '__main__':
    c = Converter()  # создание экземпляра класса
    c.CONVERT_PDF_TO_CURRENT_IMAGE() # 1
    c.CONVERT_UPDATE_IMAGE() # 2
    c.CONVERT_IMG_TO_TEXT() # 3
    c.CHECK_IP_PHONE_BIN_DATA_TXT() # 4