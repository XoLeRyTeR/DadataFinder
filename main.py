import streamlit as st
import pandas as pd
from dadata import Dadata

# Инициализация токенов для DaData
token = "d985c7e3b12214e90bd757d6f1a33ff7fae4dab0"
secret = "f987c2ae035d44b1967754c9b176ea759d855480"
dadata = Dadata(token, secret)

# Инициализация состояния
if "page" not in st.session_state:
    st.session_state.page = "Главная"
if "result" not in st.session_state:
    st.session_state.result = None


# Функция для поиска по ИНН и обновления состояния
def search_inn(inn):
    result = dadata.find_by_id("party", inn)
    if result:
        st.session_state["result"] = result
        #st.write(st.session_state["result"])
        st.session_state["page"] = "INN"
        #st.write(st.session_state["page"])
        st.rerun()
    else:
        st.warning("Организация с таким ИНН не найдена.")


# Функция для возврата на главную страницу
def come_back():
    st.session_state.page = "Главная"
    st.session_state.result = None  # Очистка результата при возврате на главную


# Отображение страниц в зависимости от состояния
if st.session_state.page == "Главная":
    st.title('Введите ИНН')
    # Создание формы для единовременного ввода и нажатия кнопки
    with st.form(key="inn_form"):
        inn = st.text_input("Введите ИНН")
        submit_button = st.form_submit_button("Найти")

        if submit_button and inn:
            search_inn(inn)

elif st.session_state.page == "INN":
    st.button('Вернуться назад', on_click=come_back)
    if st.session_state.result:
        st.json(st.session_state.result)