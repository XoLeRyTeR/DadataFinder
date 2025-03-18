from pprint import pprint
import re

import json
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
from urllib.parse import urljoin

# Настройки

DRIVER_PATH = '/opt/homebrew/bin/chromedriver'
BASE_URL = 'https://old.bankrot.fedresurs.ru/'
START_URL = 'https://old.bankrot.fedresurs.ru/TradeList.aspx'

class Parser:
    def __init__(self,name_browser:str,path_driver:str):

        if name_browser=='Chrome':
            options = webdriver.ChromeOptions()
            # options.add_argument('--headless=new')
            # options.add_argument('--disable-gpu')
            # options.add_argument('--no-sandbox')
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

    def __get_link_from_td(self,td_dom):
        try:
            return str(td_dom.find_element(By.TAG_NAME,"a").get_attribute("href"))
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
    def get_deatail_info(self,tag_detail):
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
        info=[]
        name_lots=self.wait.until(
            EC.presence_of_element_located((By.XPATH, f"//*[@id='ctl00_cphBody_rpvLots']"))
        ).find_element(By.TAG_NAME,"div").find_element(By.TAG_NAME,"div").text
        info.append(self.__get_number_lot(name_lots))
        table_tr=self.wait.until(
            EC.presence_of_all_elements_located((By.XPATH, f"//*[@id='ctl00_cphBody_lvLotList_ctrl0_tblTradeLot']/tbody/tr"))
        )

        for tr in table_tr:
            tds=tr.find_elements(By.TAG_NAME,"td")
            if len(tds)==2:
                info.append({
                    "key":tds[0].text,
                    "value":tds[1].text
                })

            else:
                div_value=tds[0].find_element(By.TAG_NAME,"div")
                try:
                    detail=div_value.find_element(By.TAG_NAME,"a")
                    detail_info=self.get_deatail_info(detail)
                except NoSuchElementException:
                    detail_info=div_value.text
                info.append({
                    "key":tds[0].find_element(By.TAG_NAME,"b").text,
                    "value":detail_info.strip()
                })
        return info
    def collect_messages(self):
        pass
    def collect_docs(self):
        pass
    def collect_additionally(self):
        pass
    def all_data_about_auction_in_headlines(self,headlines):
        result_data=dict()
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
            result_data[head]=type_callback[head]()
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
