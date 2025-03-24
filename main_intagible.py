import random
import shutil
import string
from pathlib import Path
from pprint import pprint
import re
import argparse
import zipfile
import json
import docx
from fake_useragent import UserAgent
from docx.opc.exceptions import PackageNotFoundError
import subprocess
import pypdf
from io import StringIO
from selenium import webdriver
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException, \
    NoSuchWindowException, UnexpectedAlertPresentException
import time
import pandas as pd
import os

from utils.config import config
from utils.database import init_db, insert_link_collect, get_links_not_collect, update_status_collect_link

# Настройки
parser = argparse.ArgumentParser(description="Trades")
parser.add_argument(
    "--name_browser",  # Имя аргумента
    type=str,   # Тип значения (можно изменить на int, float и т.д.)
    required=True,  # Обязательный аргумент
    help="Название браузера"
)
parser.add_argument(
    "--temp_dir",  # Имя аргумента
    type=str,   # Тип значения (можно изменить на int, float и т.д.)
    required=True,  # Обязательный аргумент
    help="Название браузера"
)
parser.add_argument(
    "--headless",  # Имя аргумента
    type=str,   # Тип значения (можно изменить на int, float и т.д.)
    required=True,  # Обязательный аргумент
    help="Название браузера"
)
args = parser.parse_args()
NAME_BROWSER=args.name_browser

BASE_URL = 'https://old.bankrot.fedresurs.ru/'
START_URL = 'https://old.bankrot.fedresurs.ru/TradeList.aspx'
PATH_DIR_TEMP=args.temp_dir
type_start_headless= True if args.headless=="True" else False
class Parser:
    def __init__(self,name_browser:str):
        self.options_categories = []
        self.ua = UserAgent()

        if name_browser=='Chrome':
            self.driver = self.__init_chrome()
        elif name_browser=='Firefox':
            self.driver = self.__init_firefox()
        elif name_browser=="Safari":
            self.driver = self.__init_safari()
        self.wait = WebDriverWait(self.driver, 20)
    def __init_chrome(self):
        options = webdriver.ChromeOptions()
        if type_start_headless:
            options.add_argument('-headless')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('start-maximized')
        options.add_argument("--disable-download-notifications")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-infobars")
        options.add_experimental_option("prefs", {
            "download.default_directory": PATH_DIR_TEMP,  # Указываем папку для скачивания
            "download.prompt_for_download": False,  # Отключаем запрос подтверждения
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,  # Отключить проверку безопасности (для PDF)
            "profile.default_content_settings.popups": 0,
            # Включаем безопасный просмотр
        })

        options.add_argument(f'user-agent={self.ua.random}')
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        return driver
    def __init_firefox(self):
        options = webdriver.FirefoxOptions()
        if type_start_headless:
            options.add_argument('-headless')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('start-maximized')
        options.set_preference("browser.download.folderList", 2)
        options.set_preference("browser.download.dir", PATH_DIR_TEMP)
        options.set_preference("browser.download.manager.showWhenStarting", False)
        options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/octet-stream")
        options.set_preference("browser.download.manager.showWhenStarting", False)

        # Запуск браузера с указанным профилем
        options.add_argument(f'user-agent={self.ua.random}')
        driver = webdriver.Firefox(
            service=Service(GeckoDriverManager().install()),
            options=options
        )
        return driver
    def __init_safari(self):
        options = webdriver.SafariOptions()
        options.add_argument(f'user-agent={self.ua.random}')
        driver = webdriver.Safari(
            options=options
        )
        return driver
    def __init_wait(self):
        return WebDriverWait(self.driver, 20)
    def init_options_categories(self,categories:list):
        self.options_categories = categories

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
        element_text_categories = self.wait.until(
            EC.presence_of_element_located((By.ID, "ctl00_cphBody_ucPropertyCategoriesSelect_tbSelectedText"))
        )
        element_text_categories.click()
        self.wait.until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, "//tr[@class='rwContentRow']//iframe")))
        self.wait.until(EC.presence_of_element_located((By.ID, "ctl00_BodyPlaceHolder_divContainer")))
        for option in self.options_categories:
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
            try:
                trade_type_cell = row.find_elements(By.XPATH, ".//td[6]")
            except StaleElementReferenceException:
                continue
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
        dataframe = pd.read_html(StringIO(html))[0]

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
    def get_text_document_docx(self,path_document)->str:

        doc = docx.Document(path_document)
        result = []

        for element in doc.element.body:
            if element.tag.endswith('p'):  # Если это параграф (текст)
                paragraph = element
                text = paragraph.text.strip()
                if text:
                    result.append(text)
            elif element.tag.endswith('tbl'):  # Если это таблица
                table = element
                for row in table.xpath(".//w:tr"):
                    row_data = []
                    for cell in row.xpath(".//w:tc"):
                        cell_text = "".join(node.text for node in cell.xpath(".//w:t"))
                        row_data.append(cell_text.strip())
                    result.append("\t".join(row_data))

        return "\n".join(result)

    def convert_doc_to_docx(self,doc_path):
        """
        Конвертирует .doc файл в .docx с помощью LibreOffice и сохраняет в ту же директорию.

        :param doc_path: Путь к исходному .doc файлу.
        """
        try:
            # Проверяем, существует ли исходный файл
            if not os.path.exists(doc_path):
                raise FileNotFoundError(f"Файл {doc_path} не найден.")

            # Получаем директорию и имя файла без расширения
            file_dir = os.path.dirname(doc_path)
            file_name = os.path.splitext(os.path.basename(doc_path))[0]

            # Запуск LibreOffice в headless-режиме для конвертации
            command = [
                "lowriter", "--headless", "--convert-to", "docx",
                "--outdir", file_dir, doc_path
            ]
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            pass
        except Exception as e:
            pass
        os.remove(doc_path)
        return os.path.join(doc_path)

    def unzip_acrhive_documents(self,name_docs,extract_dir,encoding_from='cp437', encoding_to='cp866')->list:
        current_files=[]
        with zipfile.ZipFile(os.path.join("data/temp/", name_docs), 'r') as zip_ref:
            for file in zip_ref.namelist():
                # Исправляем кодировку имени файла
                corrected_name = file.encode(encoding_from).decode(encoding_to)

                # Создаём полный путь для сохранения файла
                full_path = os.path.join(extract_dir, corrected_name)
                if full_path.endswith(".doc") or full_path.endswith(".docx") or full_path.endswith(".pdf"):
                    current_files.append(full_path)
                    # Создаём папки, если их нет
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)

                    # Записываем файл
                    with open(full_path, 'wb') as f:
                        f.write(zip_ref.read(file))

        return current_files
    def get_text_document_pdf(self,path_document)->str:
        reader = pypdf.PdfReader(path_document)
        return "\n".join([page.extract_text() for page in reader.pages])

    def get_info_docs(self, tag_link, ):
        result=[]
        name_docs=tag_link.text
        tag_link.click()
        time.sleep(5)
        extract_dir = PATH_DIR_TEMP+"/docs"
        current_files = []
        if name_docs.endswith(".zip"):
            current_files.extend(self.unzip_acrhive_documents(name_docs,extract_dir))
        elif name_docs.endswith(".docx") or name_docs.endswith(".doc") or name_docs.endswith(".pdf"):
            current_files.append(os.path.join("data/temp/", name_docs))
        for i,file in enumerate(current_files):
            if file.endswith(".doc"):
                file=self.convert_doc_to_docx(file)+"x"
            file_name=os.path.basename(file)
            result.append({
                "key":file_name,
                "value": self.get_text_document_pdf(file) if file.endswith(".pdf") else self.get_text_document_docx(file)
            })
        self.__clear_temp_dir("data/temp/")
        return result

    def collect_docs(self):
        result_data = []
        table_tr = self.wait.until(
            EC.presence_of_element_located(
                (By.XPATH, f"//*[@id ='ctl00_cphBody_rpvDocuments']"))
        ).find_element(By.TAG_NAME, "table")
        headlines = [header.text for header in table_tr.find_elements(By.TAG_NAME, 'th')]
        rows = table_tr.find_elements(By.TAG_NAME, 'tr')[1:]  # Пропускаем первую строку с заголовками

        # Проходим по строкам таблицы
        for row in rows:
            # Извлекаем ячейки в строке
            cells = row.find_elements(By.TAG_NAME, 'td')
            detail = cells[1].find_element(By.TAG_NAME, "a")
            detail_info = self.get_info_docs(detail)

            result_data.append({
                headlines[0]: cells[0].text,
                headlines[1]: detail_info,
            })
        return result_data
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
    def get_info_link_info_cell_EFRSB(self,tag_detail)->list:
        data = []
        time.sleep(2)
        original_tab = self.driver.current_window_handle
        # Находим кнопку, которая открывает новую страницу
        tag_detail.click()

        # Переключаемся на новую вкладку
        new_tab = self.driver.window_handles[-1]  # Последняя вкладка
        self.driver.switch_to.window(new_tab)

        # Получаем информацию (например, заголовок страницы)
        container = self.wait.until(
            EC.presence_of_element_located((By.XPATH, f"//div[@class='containerInfo']"))
        )
        tables = self.driver.find_elements(By.XPATH, f"//div[@class='containerInfo']/table")
        if tables:
            for table in tables:
                class_table=table.get_attribute('class')
                if class_table == 'headInfo' or class_table == 'bodyInfo':
                    try:
                        header = table.find_element(By.XPATH, "./preceding-sibling::div[1]").find_element(By.TAG_NAME, "b").text.strip()
                    except NoSuchElementException:
                        header = self.generate_unique_string()
                    table_info = self.get_info_table_from_TradeMessageInfo(table)
                    data.append({
                        "key": header,
                        "value": table_info
                    })
                else:
                    table_info = self.get_info_table_from_TradeMessageInfo(table)
                    data.append({
                        "key": class_table.strip(),
                        "value": table_info
                    })
        soup = BeautifulSoup(container.get_attribute('innerHTML'), 'html.parser')
        # Ищем все теги <b>
        div_msg=soup.find_all('div',class_="msg")
        for div in div_msg:
            header = div.find('b').text.strip()
            text = div.get_text(separator=' ').strip()
            data.append({
                "key": header,
                "value": text
            })
        self.driver.close()
        # Возвращаемся на исходную вкладку
        self.driver.switch_to.window(original_tab)
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
        self.driver.get(START_URL)
        self.select_classification()
        time.sleep(1)
        self.click_search_filters()
        time.sleep(10)
        self.collect_link_auctions_page()
        all_link_auctions=self.collect_all_link_on_auctions()
        # all_link_auctions=[
        #     "https://old.bankrot.fedresurs.ru/TradeCard.aspx?ID=905df1eb-ae54-4962-82ed-32d76fc8f6da",
        #     'https://old.bankrot.fedresurs.ru/TradeCard.aspx?ID=f29937fc-734b-423f-ab87-013c88bdcc39',
        #     "https://old.bankrot.fedresurs.ru/TradeCard.aspx?ID=a344e827-4bee-49c4-acc4-b0073307de64",
        #     "https://old.bankrot.fedresurs.ru/TradeCard.aspx?ID=9debafa1-6ea9-46c2-8959-2edcc54446d0"
        #     # 'https://old.bankrot.fedresurs.ru/TradeCard.aspx?ID=8bf4e8fd-4088-4bbe-a0a4-af6f4b1f46d6',
        #     # 'https://old.bankrot.fedresurs.ru/TradeCard.aspx?ID=a73875b1-8ff6-4dc7-99c1-b7e34fd76006',
        #     # 'https://old.bankrot.fedresurs.ru/TradeCard.aspx?ID=ccb6d1ef-9293-4973-9c57-84c07418b58d',
        #     # 'https://old.bankrot.fedresurs.ru/TradeCard.aspx?ID=11eb4933-035e-4bfa-9a46-5fef8b273a2a',
        #     # 'https://old.bankrot.fedresurs.ru/TradeCard.aspx?ID=27a47ab4-269c-4f21-a0fd-0357353bcff6',
        #     #
        #     # 'https://old.bankrot.fedresurs.ru/TradeCard.aspx?ID=f6156a07-af21-4088-a1de-923ab32ed79a',
        # ]
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
    options_categories = [
        "Права требования на краткосрочные долговые обязательства (дебиторская задолженность)",
        "Ценные бумаги",
        "Уступка требований по  кредитным обязательствам"
    ]
    p=Parser(NAME_BROWSER)
    p.init_options_categories(options_categories)
    p.run()
if __name__ == '__main__':
    main()
