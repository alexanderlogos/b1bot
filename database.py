import sqlite3
import pandas as pd
import mysql.connector

# Шаг 1: Экспорт данных из SQLite в CSV файлы

def export_sqlite_to_csv(sqlite_db, tables):
    # Подключаемся к SQLite базе данных
    sqlite_conn = sqlite3.connect(sqlite_db)

    # Экспортируем каждую таблицу в отдельный CSV файл
    for table in tables:
        df = pd.read_sql_query(f"SELECT * FROM {table}", sqlite_conn)
        df.to_csv(f'{table}.csv', index=False)

    # Закрываем подключение к SQLite
    sqlite_conn.close()

# Шаг 2: Импорт данных из CSV файлов в MySQL

def import_csv_to_mysql(mysql_config, tables):
    # Подключаемся к MySQL базе данных
    mysql_conn = mysql.connector.connect(**mysql_config)
    cursor = mysql_conn.cursor()

    # Создание таблицы users
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        lang TEXT,
        ref_link TEXT,
        balance INT DEFAULT 0,
        ref_count INT DEFAULT 0,
        wallet TEXT,
        balance_q INT DEFAULT 0,
        current_task INT DEFAULT 0
    )''')
    mysql_conn.commit()

    # Создание таблицы tweet
    cursor.execute('''CREATE TABLE IF NOT EXISTS tweet (
        id INT PRIMARY KEY AUTO_INCREMENT,
        tweet_link TEXT
    )''')
    mysql_conn.commit()

    # Создание таблицы admins
    cursor.execute('''CREATE TABLE IF NOT EXISTS admins (
        id INT PRIMARY KEY AUTO_INCREMENT,
        user_id VARCHAR(255)
    )''')
    mysql_conn.commit()

    # Создание таблицы skipped_tasks
    cursor.execute('''CREATE TABLE IF NOT EXISTS skipped_tasks (
        user_id BIGINT,
        task_id INT
    )''')
    mysql_conn.commit()

    # Перенос данных из CSV файлов в MySQL
    for table in tables:
        # Загружаем данные из CSV файла
        df = pd.read_csv(f'{table}.csv')

        # Заменяем NaN значения на None для корректной вставки в MySQL
        df = df.where(pd.notnull(df), None)

        # Преобразуем все данные в стандартные типы данных Python
        df = df.astype(object).where(pd.notnull(df), None)

        # Определяем SQL запрос для вставки данных
        columns = ", ".join(df.columns)
        values = ", ".join(["%s"] * len(df.columns))
        insert_query = f"INSERT INTO {table} ({columns}) VALUES ({values})"

        # Преобразуем DataFrame в список кортежей
        data = [tuple(row) for row in df.to_numpy()]

        # Выполняем вставку данных в таблицу
        cursor.executemany(insert_query, data)
        mysql_conn.commit()

    # Закрываем подключение к MySQL
    cursor.close()
    mysql_conn.close()
# Параметры конфигурации
sqlite_db = 'users.db'
tables = ["users", "tweet", "admins", "skipped_tasks"]

mysql_config = {
    'host': 'localhost',
    'user': 'buser',  # замените 'yourusername' на ваше имя пользователя
    'password': 'buser',  # замените 'yourpassword' на ваш пароль
    'database': 'b1coin'  # замените 'b1coin' на вашу базу данных
}

# Выполнение экспорта и импорта
export_sqlite_to_csv(sqlite_db, tables)
import_csv_to_mysql(mysql_config, tables)
