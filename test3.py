import sqlite3
import streamlit as st
import pandas as pd

# Создаём подключение к базе данных
conn = sqlite3.connect('my_database.db')
cursor = conn.cursor()

# Создание таблицы (если таблица не существует)
cursor.execute('''CREATE TABLE IF NOT EXISTS users
              (id INTEGER PRIMARY KEY, name TEXT, age INTEGER, gender TEXT)''')
conn.commit()

# Функция для добавления данных в базу данных
def add_user(name, age, gender):
    cursor.execute("INSERT INTO users (name, age, gender) VALUES (?, ?, ?)", (name, age, gender))
    conn.commit()

# Функция для получения данных из базы данных
def get_users():
    cursor.execute("SELECT * FROM users")
    return cursor.fetchall()

# Streamlit интерфейс
st.title("User Database")

# Форма для ввода данных
name = st.text_input("Name")
age = st.number_input("Age", min_value=0, max_value=100)
gender = st.selectbox("Gender", ["Male", "Female", "Other"])

if st.button("Add User"):
    add_user(name, age, gender)
    st.success("User added successfully!")

# Отображение всех пользователей
users = get_users()
df = pd.DataFrame(users, columns=["ID", "Name", "Age", "Gender"])
st.write("User Database:")
st.dataframe(df)

# Закрытие соединения
conn.close()
