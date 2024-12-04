import streamlit as st
import pandas as pd
from dadata import Dadata
import datetime
import sqlite3
import json


token = "d985c7e3b12214e90bd757d6f1a33ff7fae4dab0"
secret = "f987c2ae035d44b1967754c9b176ea759d855480"

conn = sqlite3.connect('data.db')
cursor =conn.cursor()

with open('translate_data.json', 'r', encoding='utf-8') as json_file:
    data_translate = json.load(json_file)
dadata = Dadata(token, secret)

if "page" not in st.session_state:
    st.session_state.page = "Главная"
if "result" not in st.session_state:
    st.session_state.result = None
if "button_clicked" not in st.session_state:
    st.session_state.button_clicked = False
def unix_to_date(x):
    try:
        dt = datetime.datetime.utcfromtimestamp(x / 1000)
        str=dt.strftime('%Y-%m-%d')
        return str
    except:
        return x
def prepross():
    df = pd.json_normalize(st.session_state.result)

    df["data.state.actuality_date"]=df["data.state.actuality_date"].apply(unix_to_date)
    df["data.state.registration_date"] = df["data.state.registration_date"].apply(unix_to_date)
    df["data.state.liquidation_date"] = df["data.state.liquidation_date"].apply(unix_to_date)
    df["data.ogrn_date"] = df["data.ogrn_date"].apply(unix_to_date)
    df['data.management.start_date'] = df['data.management.start_date'].apply(unix_to_date)
    df = df.reindex(columns=data_translate.keys())
    df = df.rename(columns=data_translate)
    return df

def sql_query(df):
    inn = int(df.at[0, 'ИНН'])

    cursor.execute("SELECT * FROM users WHERE ИНН = ?", (inn,))
    existing_record = cursor.fetchone()

    if (existing_record):
        for i in df.columns:
            if (df.at[0, i]):
                cursor.execute(f"UPDATE users SET '{i}' = '{df.at[0, i]}' WHERE ИНН = {inn}")
        conn.commit()
    else:
        df.to_sql('users', conn, if_exists='append', index=False)
def search_inn(inn):
    result = dadata.find_by_id("party", inn)
    if result:
        st.session_state["result"] = result
        st.session_state["page"] = "Информация по ИНН"
        st.rerun()
    else:
        st.warning("Организация с таким ИНН не найдена.")
def identification(login,password):
    table = pd.read_sql("SELECT * FROM 'accounts'", conn)
    st.write(table)
    '''
    '''
def come_back():
    st.session_state.button_clicked = False
    st.session_state.page = "Главная"
    st.session_state.result = None
def come_find():
    st.session_state.page = 'Главная'

def come_BD():
    st.session_state.page = 'База данных'

def come_tabl():
    st.session_state.page= 'Таблица с заполнением'

if st.session_state.page=="База данных":
    st.set_page_config(layout="wide")
    st.title("База данных компаний")
    try:
        all_users = pd.read_sql("SELECT * FROM users", conn)
        st.dataframe(all_users, width=1000000000)
        st.button('Поиск по ИНН', on_click=come_find)
    except:
        df = pd.DataFrame(columns=data_translate.values())
        df.to_sql('users', conn, if_exists='append', index=False)
        all_users = pd.read_sql("SELECT * FROM users", conn)
        st.dataframe(all_users, width=1000000000)
        st.button('Поиск по ИНН', on_click=come_find)

elif st.session_state.page == "Главная":
    st.set_page_config(layout="centered")

    col1,col2,col3 = st.columns([4,1.2,1])
    with(col1):
        st.subheader('едите ИНН?')
    with col2:
        st.button('Все компании',on_click=come_BD)
    with col3:
        st.button('Таблица',on_click=come_tabl)
    with st.form(key="inn_form"):
        inn = st.text_input("Введите ИНН")
        submit_button = st.form_submit_button("Найти")
        if submit_button and inn:
            search_inn(inn)

elif st.session_state.page == "Информация по ИНН":
    st.button('Вернуться назад', on_click=come_back)
    st.write("Компания - " + st.session_state.result[0]['value'])
    df = prepross().head(1)
    st.write(df)
    sql_query(df)
elif st.session_state.page == "Таблица с заполнением":
    st.set_page_config(layout="wide")
    st.button('Вернуться',on_click=come_back)
    table = pd.read_sql("SELECT * FROM 'table'", conn)
    st.dataframe(table)
    if not st.session_state.button_clicked:
        if st.button("Добавить новую запись"):
            st.session_state.button_clicked = True
            st.rerun()
    if st.session_state.button_clicked:
        mp={}
        with st.form(key='form'):
            mp['Номер на ЕФРСБ']=st.text_input('Введите номер на ЕФРСБ')
            mp['Наименование должника']=st.text_input('Введите наименование должника')
            mp['Вид торгов'] = st.text_input('Введите вид торгов')
            mp['Дата начала подачи заявок'] = st.date_input('Введите дату начала подачи заявок',min_value=datetime.date(2000, 1, 1), max_value=datetime.date(2030, 12, 31))
            mp['Дата окончания подачи заявок'] = st.date_input('Введите дату окончания подачи заявок',min_value=datetime.date(2000, 1, 1), max_value=datetime.date(2030, 12, 31))
            mp['Место проведения'] = st.text_input('Введите место проведения')
            mp['Номер лота'] = st.text_input('Введите номер лота')
            mp['Начальная цена'] = st.text_input('Введите начальную цену')
            mp['Информация о снижении'] = st.text_input('Введите информацию о снижении')
            mp['Описание'] = st.text_input('Введите описание')
            mp['ИНН'] = st.text_input('Введите ИНН')
            mp['Номер арбитражного дела'] = st.text_input('Введите номер арбитражного дела')
            mp['(3) Дата отчетного года'] = st.date_input('Введите дату отчетного года',min_value=datetime.date(2000, 1, 1), max_value=datetime.date(2030, 12, 31))
            mp['Сумма ДЗ'] = st.text_input('Введите cумму ДЗ')
            mp['(3) Сумма общих долгов'] = st.text_input('Введите сумму общих долгов')
            mp['(3) Процентное отношение ДЗ к общим долгам общества'] = st.text_input('Введите процентное отношение ДЗ к общим долгам общества')
            mp['(2) Статус'] = st.radio('Введите статус',('Действующее','Не действующее'))
            mp['(2) Наличие недостоверных сведений'] = st.radio('Есть ли наличие недостоверных сведений',('Да','Нет'))
            mp['(2) Заинтересованность третьих лиц'] = st.radio('Есть ли заинтересованность третьих лиц',('Да','Нет'))
            mp['(2) Наличие блокировок от налоговой'] = st.radio('Есть ли наличие блокировок от налоговой',('Да','Нет'));
            mp['(2) Наличие гос участия'] = st.radio('Наличие гос участия',('Без гос участия','С гос участием','Не определено'))
            mp['(2) Наличие у руководителя должника сторонних действующих обществ'] = st.text_input('Наличие у руководителя должника сторонних действующих обществ (если есть указывается ИНН, наименование и чистые активы общества в одном поле)')
            mp['(2) Наличие у участника должника сторонних действующих обществ'] = st.text_input('Наличие у участника должника сторонних действующих обществ (если есть указывается ИНН, наименование и чистые активы общества в одном поле)')
            mp['(2) Смена руководителя'] = st.date_input('Введите дату смены руководителя',min_value=datetime.date(2000, 1, 1), max_value=datetime.date(2030, 12, 31))
            mp['(2) Смена участника'] = st.date_input('Введите дату смены участника',min_value=datetime.date(2000, 1, 1), max_value=datetime.date(2030, 12, 31))
            mp['(2) Количество юр лиц директора'] = st.text_input('Введите количество юр лиц директора')
            mp['(2) Количество юр лиц участника'] = st.text_input('Введите количество юр лиц участника')
            mp['(3) Сумма основных средств (ОС)'] = st.text_input('Введите сумму основных средств (ОС)')
            mp['(3) Динамика изменения ОС'] = st.text_input('Введите динамику изменения ОС')
            mp['(3) Сумма запасов'] = st.text_input('Введите сумму запасов')
            mp['(3) Динамика изменения запасов'] = st.text_input('Введите динамику изменения запасов')
            mp['(3) Чистые активы'] = st.text_input('Введите чистые активы')
            mp['Наличие задолженностей (для физ лиц)'] = st.text_input('Введите количество и общая сумма непогашенной задолженности (ФССП)')
            mp['Итоговая оценка'] = st.text_input('Введите итоговую оценку')
            mp['Судебная практика'] = st.text_input('Введите судебную практику')
            send = st.form_submit_button('Добавить запись')
        if (send):
            df = pd.DataFrame([mp])
            df.to_sql('table', conn, if_exists='append', index=False)
            st.success("Строка добавлена!")
            st.session_state.button_clicked = False
            st.rerun()



