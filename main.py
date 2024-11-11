import streamlit as st
import pandas as pd
import numpy as np
from dadata import Dadata
from datetime import datetime
import sqlite3
import json

token = "d985c7e3b12214e90bd757d6f1a33ff7fae4dab0"
secret = "f987c2ae035d44b1967754c9b176ea759d855480"

conn = sqlite3.connect('my_database.db')
cursor =conn.cursor()

with open('translate_data.json', 'r', encoding='utf-8') as json_file:
    data_translate = json.load(json_file)
dadata = Dadata(token, secret)

if "page" not in st.session_state:
    st.session_state.page = "Главная"
if "result" not in st.session_state:
    st.session_state.result = None
def unix_to_date(x):
    try:
        dt = datetime.utcfromtimestamp(x / 1000)
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

def come_back():
    st.session_state.page = "Главная"
    st.session_state.result = None
def come_find():
    st.session_state.page = 'Главная'

def come_BD():
    st.session_state.page = 'База данных'

if st.session_state.page=="База данных":
    st.title("База данных компаний")
    all_users = pd.read_sql("SELECT * FROM users", conn)
    st.dataframe(all_users, width=10000)
    st.button('Поиск по ИНН', on_click=come_find)

elif st.session_state.page == "Главная":
    col1,col2 = st.columns([4,1])
    with(col1):
        st.subheader('Введите ИНН')
    with col2:
        st.button('Все компании',on_click=come_BD)
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

    st.json(st.session_state.result)