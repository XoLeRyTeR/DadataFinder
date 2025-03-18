import random
import shutil
import string
from pathlib import Path
from pprint import pprint
import re
import zipfile
import json

import pypdf
from spire.doc import Document,Paragraph,Table
# TODO собрать "Объявление о торгах в ЕФРСБ	№13777116 опубликовано 11.03.2024"
# TODO собрать документы
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
import time
import pandas as pd
import os

# Настройки


BASE_URL = 'https://old.bankrot.fedresurs.ru/'
START_URL = 'https://old.bankrot.fedresurs.ru/TradeList.aspx'
PATH_DIR_TEMP="C:\\Users\\kuzic\\PycharmProjects\\DadataFinder\\data\\temp"
class Parser:
    def __init__(self,name_browser:str,path_driver:str):

        if name_browser=='Chrome':
            options = webdriver.ChromeOptions()
            # options.add_argument('--headless=new')
            # options.add_argument('--disable-gpu')
            # options.add_argument('--no-sandbox')
            options.add_experimental_option("prefs", {
                "download.default_directory": PATH_DIR_TEMP,  # Указываем папку для скачивания
                "download.prompt_for_download": False,  # Отключаем запрос подтверждения
                "download.directory_upgrade": True,  # Включаем безопасный просмотр
            })

            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            self.driver = webdriver.Chrome(
                service=Service(executable_path=path_driver),
                options=options
            )
        elif name_browser=='Firefox':
            options = webdriver.FirefoxOptions()
            # Запуск браузера с указанным профилем
            options.add_argument('-P default')
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            self.driver = webdriver.Firefox(
                service=Service(executable_path=path_driver),
                options=options,
            )
        elif name_browser=="Safari":
            options = webdriver.SafariOptions()
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            self.driver = webdriver.Safari(
                options=options
            )

        self.wait = WebDriverWait(self.driver, 20)
    def __get_link_in_a_onclick(self,onclick_text):
        pattern = r"openNewWin\('([^']+)'"

        # Поиск совпадений
        match = re.search(pattern, onclick_text)

        # Проверка, найдено ли совпадение, и извлечение результата
        if match:
            result = match.group(1)  # Извлекаем первую группу (то, что в скобках)
            return result
        else:
            return ""
    def __get_link_from_td(self,td_dom):
        try:
            link=td_dom.find_element(By.TAG_NAME,"a").get_attribute("href")
            if link:return link
            else:
                link=td_dom.find_element(By.TAG_NAME,"a").get_attribute("onclick")
                link=self.__get_link_in_a_onclick(link)
                if link:return "https://old.bankrot.fedresurs.ru"+link
                else:return ""

        except NoSuchElementException:
            return ""
    def __get_number_lot(self,text):
        # Регулярное выражение для извлечения ключа и значения
        pattern = r"(?P<key>\D+)\s*№\s*(?P<value>\d+)"

        # Поиск совпадений
        match = re.search(pattern, text)

        # Создание словаря
        if match:
            return {"key": match.group("key").strip(), "value": match.group("value")}
        else:
            return {"key": "Лот", "value": text}
    def __clear_temp_dir(self, PATH_DIR_TEMP):
        for path in Path(PATH_DIR_TEMP).glob('*'):
            if path.is_dir():
                shutil.rmtree(path,ignore_errors=True)
            else:
                path.unlink()
    def generate_unique_string(self,length=10):
        # Используем буквы и цифры для создания строки
        characters = string.ascii_letters
        # Генерируем строку случайных символов
        unique_string = ''.join(random.choice(characters) for _ in range(length))
        return unique_string
    def select_classification(self):
        options_categories=[
            "Права требования на краткосрочные долговые обязательства (дебиторская задолженность)",
            "Ценные бумаги",
            "Уступка требований по  кредитным обязательствам"
        ]
        element_text_categories = self.wait.until(
            EC.presence_of_element_located((By.ID, "ctl00_cphBody_ucPropertyCategoriesSelect_tbSelectedText"))
        )
        element_text_categories.click()
        self.wait.until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, "//tr[@class='rwContentRow']//iframe")))
        self.wait.until(EC.presence_of_element_located((By.ID, "ctl00_BodyPlaceHolder_divContainer")))
        for option in options_categories:
            text_element = self.wait.until(
                EC.presence_of_element_located((By.XPATH, f"//span[@class='rtIn' and contains(text(), '{option}')]"))
            )
            parent_element = text_element.find_element(By.XPATH, "./..")
            time.sleep(1)
            rt_checked_element = parent_element.find_element(By.CLASS_NAME, "rtUnchecked")
            time.sleep(1)
            rt_checked_element.click()

        self.wait.until(
            EC.presence_of_element_located((By.ID, f"ctl00_BodyPlaceHolder_btnSelect"))
        ).click()
        self.driver.switch_to.default_content()
    def click_search_filters(self):
        return self.wait.until(
            EC.presence_of_element_located((By.ID, f"ctl00_cphBody_btnTradeSearch"))
        ).click()
    def collect_link_auctions_page(self):
        rows = self.driver.find_elements(By.XPATH, "//table[@id='ctl00_cphBody_gvTradeList']//tr")
        trade_link = []
        for row in rows:
            trade_type_cell = row.find_elements(By.XPATH, ".//td[6]")
            if trade_type_cell:
                try:
                    trade_a = trade_type_cell[0].find_element(By.XPATH, ".//a")
                except:
                    print("тут ошибочка")
                    continue
                href = trade_a.get_attribute('href')
                if "https://old.bankrot.fedresurs.ru/TradeCard.aspx?ID" in href:
                    trade_link.append(href)
        return trade_link
    def __get_count_all_auctions(self,text)->int:
        match = re.search(r"Всего:\s*(\d+)", text)
        if match:
            total = int(match.group(1))
            return total
        else:
            return 0
    def collect_all_link_on_auctions(self):
        all_link=[]
        all_link.extend(self.collect_link_auctions_page())
        count_all_auctions = self.__get_count_all_auctions(self.driver.find_element(By.ID, "ctl00_cphBody_PaggingAdvInfo1_tdPaggingAdvInfo").text.strip())
        for page in range(2,count_all_auctions+1):
            pprint(f"page : {page}")
            td=self.driver.find_element(By.XPATH,"//*[@id='ctl00_cphBody_gvTradeList']/tbody/tr[22]/td/table/tbody/tr")
            all_tr=td.find_elements(By.TAG_NAME,"a")
            last_page_current_slideboard=all_tr[-1].text
            for i,a in enumerate(all_tr):
                if a.text=="..." and i==0:
                    continue
                if a.text=="..."  or (str(page)==a.text and a.text.isdecimal()):
                    if page==42:
                        print("stop")
                    time.sleep(1)
                    a.click()
                    time.sleep(2)
                    all_link.extend(self.collect_link_auctions_page())
                    break
            if last_page_current_slideboard==str(page):
                print("last page")
                break
        return list(set(all_link))
    def get_detail_info_lots(self, tag_detail):
        original_tab = self.driver.current_window_handle
        # Находим кнопку, которая открывает новую страницу
        tag_detail.click()

        # Переключаемся на новую вкладку
        new_tab = self.driver.window_handles[-1]  # Последняя вкладка
        self.driver.switch_to.window(new_tab)

        # Получаем информацию (например, заголовок страницы)
        text_details=self.wait.until(
            EC.presence_of_element_located((By.XPATH, f"/html/body/table/tbody/tr[2]/td"))
        ).text
        # Закрываем новую вкладку
        self.driver.close()
        # Возвращаемся на исходную вкладку
        self.driver.switch_to.window(original_tab)
        return text_details
    def collect_lots(self):
        info= []
        divs_lots=self.wait.until(
            EC.presence_of_all_elements_located((By.XPATH, f"//*[@id='ctl00_cphBody_rpvLots']/div"))
        )
        for lot in divs_lots:
            info_lot=[]
            name_lots=lot.find_element(By.TAG_NAME,"div").text
            table_tr=lot.find_element(By.TAG_NAME,"table").find_elements(By.TAG_NAME,"tr")
            for tr in table_tr:
                tds=tr.find_elements(By.TAG_NAME,"td")
                if len(tds)==2:
                    info_lot.append({
                        "key":tds[0].text,
                        "value":tds[1].text
                    })

                else:
                    div_value=tds[0].find_element(By.TAG_NAME,"div")
                    try:
                        detail=div_value.find_element(By.TAG_NAME,"a")
                        detail_info=self.get_detail_info_lots(detail)
                    except NoSuchElementException:
                        detail_info=div_value.text
                    info_lot.append({
                        "key":tds[0].find_element(By.TAG_NAME,"b").text,
                        "value":detail_info.strip()
                    })
            info.append({
                "key":name_lots,
                "value":info_lot
            })
        return info
    def get_info_table_from_TradeMessageInfo(self,table):

        # Получаем HTML-код таблицы
        html = table.get_attribute('outerHTML')

        # Преобразуем HTML в DataFrame
        dataframe = pd.read_html(html)[0]

        # Преобразуем DataFrame в словарь
        table_dict = dataframe.to_dict(orient="list")
        # Добавляем в список
        return  table_dict
    def get_info_TradeMessageInfo(self,tag_detail):
        data=[]
        time.sleep(2)
        original_tab = self.driver.current_window_handle
        # Находим кнопку, которая открывает новую страницу
        tag_detail.click()

        # Переключаемся на новую вкладку
        new_tab = self.driver.window_handles[-1]  # Последняя вкладка
        self.driver.switch_to.window(new_tab)

        # Получаем информацию (например, заголовок страницы)
        container=self.wait.until(
            EC.presence_of_element_located((By.XPATH, f"//div[@class='containerInfo']"))
        )
        tables=self.driver.find_elements(By.XPATH, f"//div[@class='containerInfo']/table")
        if tables:
            for table in tables:
                header = table.find_element(By.XPATH,"./preceding-sibling::b[1]").text.strip()
                table_info=self.get_info_table_from_TradeMessageInfo(table)
                data.append({
                    "key":header,
                    "value":table_info
                })
        soup = BeautifulSoup(container.get_attribute('innerHTML'), 'html.parser')
        # Ищем все теги <b>
        b_tags = soup.find_all('b')
        data_keys=[item["key"] for item in data]
        for b_tag in b_tags:

            # Получаем текст ключа (убираем лишние символы, например, двоеточие)
            key = b_tag.text.strip().rstrip(':')

            if  data_keys and any([True if data_key in key else False for data_key in data_keys]):continue
            # Получаем следующий элемент после тега <b>
            next_element = b_tag.next_sibling

            # Очищаем значение от лишних символов (например, &nbsp;)
            value = next_element.text.strip() if next_element else ''
            if value:data.append({"key": key, "value": value})


        self.driver.close()
        # Возвращаемся на исходную вкладку
        self.driver.switch_to.window(original_tab)
        return data
    def collect_messages(self):
        result_data=[]
        table_tr = self.wait.until(
            EC.presence_of_element_located(
                (By.XPATH, f"//*[@id ='ctl00_cphBody_gvMessages']"))
        )
        headlines=[header.text for header in table_tr.find_elements(By.TAG_NAME, 'th')]
        rows = table_tr.find_elements(By.TAG_NAME, 'tr')[1:]  # Пропускаем первую строку с заголовками

        # Проходим по строкам таблицы
        for row in rows:
            # Извлекаем ячейки в строке
            cells = row.find_elements(By.TAG_NAME, 'td')
            detail = cells[2].find_element(By.TAG_NAME, "a")
            detail_info = self.get_info_TradeMessageInfo(detail)

            result_data.append({
                headlines[0]:cells[0].text,
                headlines[1]: cells[1].text,
                headlines[2]:detail_info

            })
        return result_data
    def collect_docs(self):
        pass
    def collect_additionally(self):
        data=[]
        table = self.wait.until(
            EC.presence_of_element_located((By.XPATH, "//*[@id='ctl00_cphBody_rpvOther']/table"))
        )
        rows = table.find_elements(By.TAG_NAME, 'tr')

        # Обрабатываем каждую строку
        for row in rows:
            # Находим все ячейки в строке
            cells = row.find_elements(By.TAG_NAME, 'td')

            # Проверяем, что строка содержит две ячейки (название поля и значение)
            if len(cells) == 2:
                field_name = cells[0].text.strip()  # Название поля
                field_value = cells[1].text.strip()  # Значение поля
                data.append({
                    "key":field_name,
                    "value":field_value
                })
        return data
    def get_info_from_gen_table_auction(self):
        data=[]
        elements_info = self.wait.until(
            EC.presence_of_all_elements_located((By.XPATH, "//table[@id='ctl00_cphBody_tableTradeInfo']//tr"))
        )
        for row in elements_info:
            tds=row.find_elements(By.TAG_NAME,"td")
            if not tds[1].text:continue
            if "Объявление о торгах в ЕФРСБ"==tds[0].text.strip():
                collect_link_info_cell_EFRSB=self.get_info_link_info_cell_EFRSB(tds[1].find_element(By.TAG_NAME, "a"))
                data.append({
                    "key":tds[0].text.strip(),
                    "value":tds[1].text.strip(),
                    "href":collect_link_info_cell_EFRSB
                })
            else:
                data.append({
                    "key": tds[0].text.strip(),
                    "value": tds[1].text.strip(),
                    "href": self.__get_link_from_td(tds[1])
                })
        return data
    def get_headlines_auction(self):
        elements_headlines = self.wait.until(
                EC.presence_of_all_elements_located((By.XPATH, "//*[@id='ctl00_cphBody_rtsTrade']/div/ul/li"))
            )
        headlines_text=[li.text for li in elements_headlines]
        return headlines_text
    def get_all_data_about_auction_in_headlines(self, headlines):
        result_data=[]
        type_callback={
            'Лоты':self.collect_lots,
            'Сообщения':self.collect_messages,
            'Документы':self.collect_docs,
            'Дополнительно':self.collect_additionally,
        }
        for head in headlines:
            element_headlines = self.wait.until(
                EC.presence_of_element_located((By.XPATH, f"//*[@id='ctl00_cphBody_rtsTrade']/div/ul/li[contains(., '{head}')]"))
            )
            element_headlines.click()
            result_data.append({"key":head,"value":type_callback[head]()})
        return result_data






    def run(self):
        # self.driver.get(START_URL)
        # self.select_classification()
        # time.sleep(1)
        # self.click_search_filters()
        # time.sleep(10)
        # self.collect_link_auctions_page()
        # all_link_auctions=self.collect_all_link_on_auctions()
        # pprint(all_link_auctions)
        all_link_auctions=[
            "https://old.bankrot.fedresurs.ru/TradeCard.aspx?ID=905df1eb-ae54-4962-82ed-32d76fc8f6da"
            # 'https://old.bankrot.fedresurs.ru/TradeCard.aspx?ID=8bf4e8fd-4088-4bbe-a0a4-af6f4b1f46d6',
            # 'https://old.bankrot.fedresurs.ru/TradeCard.aspx?ID=a73875b1-8ff6-4dc7-99c1-b7e34fd76006',
            # 'https://old.bankrot.fedresurs.ru/TradeCard.aspx?ID=ccb6d1ef-9293-4973-9c57-84c07418b58d',
            # 'https://old.bankrot.fedresurs.ru/TradeCard.aspx?ID=11eb4933-035e-4bfa-9a46-5fef8b273a2a',
            # 'https://old.bankrot.fedresurs.ru/TradeCard.aspx?ID=27a47ab4-269c-4f21-a0fd-0357353bcff6',
            # 'https://old.bankrot.fedresurs.ru/TradeCard.aspx?ID=f29937fc-734b-423f-ab87-013c88bdcc39',
            # 'https://old.bankrot.fedresurs.ru/TradeCard.aspx?ID=f6156a07-af21-4088-a1de-923ab32ed79a',
        ]
        data={}
        for link_auction in all_link_auctions:
            result_link=[]
            self.driver.get(link_auction)
            time.sleep(1)
            result_link.extend(self.get_info_from_gen_table_auction())
            headlines_auction=self.get_headlines_auction()
            result_link.extend(self.get_all_data_about_auction_in_headlines(headlines_auction))
            data[link_auction]=result_link

        with open("dict_to_json_textfile_2.json", "w", encoding="utf-8") as fout:
            json.dump(data, fout, ensure_ascii=False, indent=4)


def main():
    p=Parser("Chrome",DRIVER_PATH)
    p.run()

if __name__ == '__main__':
    main()
