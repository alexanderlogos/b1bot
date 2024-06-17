import os
import json
import sqlite3
import asyncio
import qrcode
import aiohttp
from PIL import Image
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command
from aiogram import F
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from test2 import get_last_posts_comments
from instaloader_script import get_latest_instagram_posts  
import pandas as pd
import urllib.parse
import random
class WalletStates(StatesGroup):
    waiting_for_wallet = State()

with open('config.json', 'r', encoding='utf-8') as f:
    settings = json.load(f)
ref_bonus = 200
bot = Bot(token=settings['bot_token'])
dp = Dispatcher()
reminder_tasks = {}

conn = sqlite3.connect('users.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        lang TEXT,
        ref_link TEXT,
        balance INTEGER DEFAULT 0,
        ref_count INTEGER DEFAULT 0,
        wallet TEXT,
        current_task INTEGER DEFAULT 0,
        balance_q INTEGER DEFAULT 0
    )
''')
conn.commit()
cursor.execute('''CREATE TABLE IF NOT EXISTS tweet (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tweet_link TEXT
    )
''')
conn.commit()
cursor.execute('''CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT
    )
''')
conn.commit()
cursor.execute("""
CREATE TABLE IF NOT EXISTS skipped_tasks (
    user_id INTEGER,
    task_id INTEGER
)
""")
conn.commit()
latest_tweet = "None"
async def get_tweet():
    global latest_tweet
    cursor.execute("SELECT tweet_link FROM tweet DESC LIMIT 1")
    tweet = cursor.fetchone()
    if tweet:
        latest_tweet = tweet[0]
    return latest_tweet
asyncio.run(get_tweet())
    
tasks = [
    {
        "id": 1,
        "title": "Задание #1/15: Подписаться на Telegram-канал подкаста.",
        "description": "“ТТ Крипто: Trading Talks” - это подкаст от фаундеров $B1COIN про криптовалюты, трейдинг и инвестиции.\nПодписаться  -  @tradingtalkscrypto",
        "link": "@tradingtalkscrypto",
        "reward": 200
    },
    {
        "id": 2,
        "title": "Задание #2/15: Подписаться на YouTube канал.",
        "description": "Виктор Липский, 1 из 2х фаундеров $B1COIN - профессиональный трейдер с опытом в крипте более 6 лет.",
        "link": "https://www.youtube.com/@VICTOR_MOC",
        "reward": 300
    },
    {
        "id": 3,
        "title": "Задание #3/15: Подписаться на Instagram $B1COIN.",
        "description": "Из всех инстаграммов будет самым красочным! А также видосы про ламбу там удобней смотреть...  ",
        "link": "https://www.instagram.com/b1coin",
        "reward": 200
    },
    {
        "id": 4,
        "title": "Задание #4/15: Подписаться на Twitter (X) $B1COIN.",
        "description": "Твиттер поможет нам построить англоговорящую $B1COIN ARMY !",
        "link": "https://x.com/B1Coin_TON",
        "reward": 400
    },
    {
        "id": 5,
        "title": "Вопрос #1: Какую уникальную цель преследует проект $B1COIN?",
        "description": "Выберите один из трех вариантов ответа.",
        "options": ["A)Запустить первый мем-токен на Марсе.\n", "B)Раздать всем холдерам бесплатные пончики.\n", "C)Достичь капитализации в $1 млрд\n"],
        "optionss": ["A", "B", "C"],
        "correct_option": 2,
        "reward": 50,
        "correct_text": "Правильный ответ!\n\nМолодчина!\n\nХотя я был бы удивлен, если бы твой ответ был про пончики...\n\n$B1COIN ARMY, которая с нами с самого начала, сможет заработать более х100 к капиталу. \n\nА для этого мы разгоним капитализацию до $1 млрд!\n\nВсе, что нам нужно - вера в проект, качественный нарратив и, конечно же, юмор!",
        "incorrect_text": "Конечно, идея прекрасная...\n\nНо есть и покруче - озолотить нашу преданную $B1COIN ARMY, которая с нами с самого начала, более чем х100 к капиталу. \n\nА для этого мы разгоним капитализацию до $1 млрд!\n\nВсе, что нам нужно - вера в проект, качественный нарратив и, конечно же, юмор!"
    
    },
    {
        "id": 6,
        "title": "Вопрос #2: Что делает $B1COIN уникальным?",
        "description": "Выберите один из трех вариантов ответа.",
        "options": ["A)Розыгрыш настоящей Lamborghini среди холдеров.\n", "B)Возможность использовать токены для покупки пиццы.\n", "C)Доступ к секретным мемам.\n"],
        "optionss": ["A", "B", "C"],
        "correct_option": 0,
        "reward": 50,
        "correct_text":"Правильный ответ!\nНу а кто сомневался...\n\nЧестный розыгрыш Ламбы. Даже белки в лесу об этом мечтают!\n\nХолдишь токены - каждые сутки получаешь тикеты, позволяющие участвовать в лотерее, а в конце выбираешь цвет, говоришь локацию. \n\nА кто в свою победу не верит - тот и не выигрывает.",
        "incorrect_text":"Реально так думаешь?\nХотя в целом... \n\nНо все таки нет... Ламбу разыгрываем же! Любого цвета, в любое место... Хоть в Тюмень доставим!\n\nА те, кто не верят в свою победу - те и не выигрывают."
    },
    {
        "id": 7,
        "title": "Вопрос #3: Почему в $B1COIN на запуске нет китов и фондов?",
        "description": "Выберите один из трех вариантов ответа.",
        "options": ["A)Потому что фаундеры просто забыли их позвать.\n", "B)Чтобы избежать давления продавцов и крупного слива токенов.\n", "C)Потому что все фонды заняты запуском других проектов.\n"],
        "optionss": ["A", "B", "C"],
        "correct_option": 1,
        "reward": 50,
        "correct_text":"Правильный ответ!\n\nФонды на борту - это ТОП-1 риск для любого крипто проекта.\n\nПоэтому у нас их и нет. А все токены, которые будут продаваться в рынок после аирдропа, будут нами оперативно откуплены.\n\nВедь сливать этот жеттон по настолько мизерной цене будет только очень недальновидный человек! (🤡)",
        "incorrect_text":"Фонды на борту - это ТОП-1 риск для любого крипто проекта.\n\nОни получают токены задолго до пресейла за бесценок и затем нещадно сливают их в толпу.  \n\nПоэтому китов и знакомые фонды мы просто не позвали, чтобы избежать давления продавцов. \n\n🫥 Более того мы отказали нескольким достаточно крупным ребятам на старте и вежливо попросили откупать их с рынка, раз они в нас так верят."
    },
    {
        "id": 8,
        "title": "Вопрос #4: Кто основал проект $B1COIN?",
        "description": "Выберите один из трех вариантов ответа.",
        "options": ["A)Основатели хедж-фонда с опытом запуска блокчейна и анонимного мессенджера.\n", "B)Группа энтузиастов без опыта в криптовалюте.\n", "C)Известный музыкант и актер.\n"],
        "optionss": ["A", "B", "C"],
        "correct_option": 0,
        "reward": 50,
        "correct_text":"Правильный ответ!\n\nНу а кто сомневался...\n\nВиктор & Макс - это не просто фаундеры, а настоящие визионеры с многолетним опытом в маркетинге, финансах и крипте.\n\nНо им не нужны нелепые звания и титулы, чтобы привлечь твое внимание. \n\nОни просто собрали команду, которая знает, как разогнать актив до $1 ярда капы!",
        "incorrect_text":"Видимо ты смешно шутишь в офлайн-жизни!\n\nЗови на стендап-концерты, комик!\n\nВиктор & Макс - это не просто фаундеры, а настоящие визионеры с многолетним опытом в маркетинге, финансах и крипте.\n\nНо им не нужны нелепые звания и титулы, чтобы привлечь твое внимание. \n\nОни просто собрали команду, которая знает, как разогнать актив до $1 ярда капы!"
    },
    {
        "id": 9,
        "title": "Вопрос #5: Какой подход используют фаундеры $B1COIN?",
        "description": "Выберите один из трех вариантов ответа.",
        "options": ["A)Покупают дорогие машины и дома, забывая о проекте.\n", "B)Закрывают проект после первого этапа.\n", "C)Создают нарратив и сосредоточены на органическом росте мема.\n"],
        "optionss": ["A", "B", "C"],
        "correct_option": 2,
        "reward": 50,
        "correct_text":"Правильный ответ!\n\nМы были бы и рады смотаться с деньгами после пресейла, но к сожалению не знаем, как их отмыть... \n\nПоэтому придется запускаться... и выполнять все поставленные цели, общения и разыгрывать ламбу 😎",
        "incorrect_text":"Ну... Почти...\n\nМы были бы и рады смотаться с деньгами после пресейла, но к сожалению не знаем, как их отмыть... \n\nПоэтому придется запускаться... и выполнять все поставленные цели, общения и разыгрывать ламбу 😎"
    },
    {
        "id": 10,
        "title": "Вопрос #6: Как можно увеличить свои шансы на выигрыш Lamborghini?",
        "description": "Выберите один из трех вариантов ответа.",
        "options": ["A)Регулярно делая селфи с логотипом $B1COIN.\n", "B)Участвуя в гонках на игрушечных машинках.\n", "C)Дольше холдя $B1COIN. STRONG HODL!\n"],
        "optionss": ["A", "B", "C"],
        "correct_option": 2,
        "reward": 50,
        "correct_text":"Правильный ответ!\n\nКто бы не мечтал о шикарной машине? Мы даем каждому холдеру $B1COIN шанс выиграть настоящую Lamborghini!\n\nПоэтому держи токены, получай лотерейные билеты каждый день. Чем больше билетов - тем выше шанс на выигрыш!",
        "incorrect_text":"🤗 Вариант, конечно, неплохой.. но тем не менее \n\nКто бы не мечтал о шикарной машине? Мы даем каждому холдеру $B1COIN шанс выиграть настоящую Lamborghini!\n\nПоэтому держи токены, получай лотерейные билеты каждый день. Чем больше билетов - тем выше шанс на выигрыш!"
    },
    {
        "id": 11,
        "title": "Вопрос #7: Какие планы у $B1COIN на будущее?",
        "description": "Выберите один из трех вариантов ответа.",
        "options": ["A)Построить собственный тематический парк.\n", "B)Регулярные розыгрыши и запуск новых продуктов и сервисов в экосистеме TON.\n", "C)Организовать ежегодные соревнования по бегу.\n"],
        "optionss": ["A", "B", "C"],
        "correct_option": 1,
        "reward": 50,
        "correct_text":"Правильный ответ!\n\nИ никто этому не помешает!\n\nКоманда мема $B1COIN имеет амбициозные планы на будущее, включая запуск крутейшей NFT-коллекции, Lam₿a game и гэмблинг-платформы $B1COIN CASINO.\n\nНо даже не смотря на это все... wen lam₿a, sir?",
        "incorrect_text":"Почти верно!\n\nКоманда мема $B1COIN имеет амбициозные планы на будущее, включая запуск крутейшей NFT-коллекции, Lam₿a game и гэмблинг-платформы $B1COIN CASINO.\n\nНо даже не смотря на это все... wen lam₿a, sir?"
    },
    {
        "id": 12,
        "title": "Задание #5/15: Сделать репост в Twitter (X) $B1COIN.",
        "description": f"Что репостить:\n\n{latest_tweet}\n\nОтправь ссылку на свой репост в Twitter (X) ответным сообщением:",
        "reward": 300,
        "type": "twitter",
        "link": f"{latest_tweet}"
    },
    {
        "id": 13,
        "title": "Задание #6/15: Пригласить еще от 5 друзей.",
        "description": "Твои друзья станут рефералами.\n\nЗа каждого подключенного друга",
        "reward": 200,
        "referral": True
    },
    {
        "id": 14,
        "title": "Задание #7/15: Напиши комментарии к 3 крайним постам.",
        "description": "В русскоязычном Telegram-канале токена $B1COIN:\n@b1coin_ton_ru",
        "reward": 150,
        "type": "comments",
        "channel": "@b1coin_ton_ru"
    },
    {
        "id": 15,
        "title": "Задание #8/15: Напиши комментарии к 3 крайним постам.",
        "description": "В англоязычном Telegram-канале токена $B1COIN:\n@b1coin_ton",
        "reward": 150,
        "type": "comments",
        "channel": "@b1coin_ton"
    },
    {
        "id": 16,
        "title": "Задание #9/15: Напиши комментарии к 3 крайним постам.",
        "description": "В Telegram-канале криптоподкаста “TT Крипто: Trading Talks”:\n@tradingtalkscrypto",
        "reward": 150,
        "type": "comments",
        "channel": "@tradingtalkscrypto"
    },
    {
        "id": 17,
        "title": "Задание #10/15: Напиши комментарии к 3 крайним постам.",
        "description": "В Instagram-аккаунте токена $B1COIN:\n...\n[3 ссылки]\n3 ссылки генерируются автоматически на 3 последних поста\nавтообновление 1 раз в сутки в 9:00",
        "reward": 250,
        "type": "comments",
        "platform": "Instagram"
    }
]
async def is_admin(user_id):
    cursor.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
    return cursor.fetchone() is not None




language_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="RU", callback_data="lang_ru"),
        InlineKeyboardButton(text="ENG", callback_data="lang_eng")
    ]
])


channels = settings['channels']


check_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="Проверить ✅", callback_data="start_check")
    ]
])
ref_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="Пригласить друзей 🫂", callback_data="ref_b")
    ]
])
menu2_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="Задания 🎮", callback_data="quest"),
        InlineKeyboardButton(text="Баланс 💳", callback_data="balance")
    ],
    [
        InlineKeyboardButton(text="Lamba 🏎️", callback_data="lamba"),
        InlineKeyboardButton(text="Рейтинг 🔥", callback_data="top")
    ],
    [
        InlineKeyboardButton(text="Пригласить 👥", callback_data="ref_b"),
        InlineKeyboardButton(text="QR 🪧", callback_data="qrcode")
    ]
])
async def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone()
async def update_user_task(user_id, task_id):
    cursor.execute("UPDATE users SET current_task = ? WHERE user_id = ?", (task_id, user_id))
    conn.commit()

@dp.callback_query(lambda c: c.data == "top")
async def show_leaderboard(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    cursor.execute("SELECT user_id, balance FROM users ORDER BY balance DESC, user_id ASC LIMIT 10")
    top_users = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT user_id, balance FROM users ORDER BY balance DESC, user_id ASC LIMIT 1 OFFSET ?", (total_users - 1,))
    last_user = cursor.fetchone()

    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    user_balance = cursor.fetchone()[0]

    user_position = "..."
    user_rank = None
    for index, (top_user_id, _) in enumerate(top_users):
        if top_user_id == user_id:
            user_rank = index + 1
            user_position = f"<b>ТЫ {user_rank}. id: {user_id}, Баллы: {user_balance} $B1COIN.</b>"

    if user_position == "...":
        cursor.execute("SELECT COUNT(*) FROM users WHERE balance > ?", (user_balance,))
        user_rank = cursor.fetchone()[0] + 1
        user_position = f"{user_rank}. id: {user_id}"

    leaderboard_text = "Рейтинг:\n\n"
    for rank, (top_user_id, balance) in enumerate(top_users, start=1):
        if top_user_id == user_id:
            leaderboard_text += f"<b>ТЫ {rank}. id: {top_user_id}, Баллы: {balance} $B1COIN.</b>\n"
        else:
            leaderboard_text += f"{rank}. id: {top_user_id}, Баллы: {balance} $B1COIN.\n"

    leaderboard_text += f"\n{user_position}\n{total_users}. id: {last_user[0]}, Баллы: {last_user[1]} $B1COIN.\n"

    menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Меню 🪧", callback_data="menu_b")],
        [InlineKeyboardButton(text="Пригласить 👥", callback_data="ref_b")],
        [InlineKeyboardButton(text="Задания 🎮", callback_data="quest")]
    ])

    await bot.send_message(callback_query.from_user.id, leaderboard_text, reply_markup=menu_keyboard, parse_mode = "HTML")
    await callback_query.answer()

async def update_tweet(tweet_link):
    cursor.execute("UPDATE tweet SET tweet_link = ? WHERE user_id = 0", (tweet_link))
async def check_subscriptions(user_id: int):
    for channel in channels:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except TelegramBadRequest as e:
            if 'user not found' in str(e):
                return False
            raise e
    return True
async def check_subscriptions2(user_id: int):
    try:
        member = await bot.get_chat_member(chat_id="@tradingtalkscrypto", user_id=user_id)
        if member.status not in ['member', 'administrator', 'creator']:
            return False
    except TelegramBadRequest as e:
        if 'user not found' in str(e):
            return False
        raise e
    return True


@dp.callback_query(F.data == 'terms')
async def handle_terms(callback_query: types.CallbackQuery):
    global ref_bonus
    user_id = callback_query.from_user.id
    user = await get_user(user_id)
    ref_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Пригласить друзей 🫂", callback_data="ref_b")
        ]
    ])
    ref_link = user[2] 

    terms_text = (
        "📋 Условия участия в AIRDROP никогда не были еще такими простыми. Абсолютно каждый участник получит $B1COIN 🔥\n\n"
        "Чтобы участвовать, необходимо:\n"
        "1. Быть подписанным на каналы:\n"
        "@victor_moc - канал Виктора, 1 из фаундеров\n"
        "@b1coin_ton_ru (RU) - канал токена\n"
        "@b1coin_ton_en (EN) - канал токена\n"
        "2. Пригласить как можно больше друзей.\n\n"
        f"За каждого приведенного друга ты получишь {ref_bonus} $B1COIN.\n\n"
        "Чтобы увеличить баланс, выполняй задания во вкладке 'Выполнить задание' и приглашай больше друзей!\n\n"
        f"Используй для приглашения свою персональную ссылку:\n{ref_link}\n\n"
    )
    photo = FSInputFile("images/13.jpg")
    await bot.send_photo(user_id, photo, caption=terms_text,reply_markup = ref_keyboard)
    await callback_query.answer()
async def send_reminder(user_id):
    photo = FSInputFile("images/2.jpg")
    await bot.send_photo(user_id, photo, caption="🤔 Видимо кого-то отвлекли...\n\n"
                                   "Подпишись всего на 3 телеграмм-канала и участвуй в щедром AIRDROP!\n\n"
                                   "Кто не участвует, тот чебурашка... 👹\n\n"
                                   "Подпишись на каналы и участвуй в раздаче денег:\n"
                                   "@victor_moc - канал Виктора, 1 из фаундеров\n"
                                   "@b1coin_ton_ru (RU) - канал токена\n"
                                   "@b1coin_ton_en (EN) - канал токена", parse_mode='HTML',reply_markup = check_keyboard)

async def schedule_reminder(user_id):
    await asyncio.sleep(600)  
    await send_reminder(user_id)
class BroadcastStates(StatesGroup):
    waiting_for_message = State()
    waiting_for_image = State()
    waiting_for_url_buttons = State()
    ready_to_broadcast = State()
admin_panel_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Админ Панель")]
    ],
    resize_keyboard=True
)

@dp.callback_query(lambda c: c.data == "rating")
async def show_rating(callback_query: types.CallbackQuery):
    cursor.execute("SELECT user_id, balance FROM users ORDER BY balance DESC")
    users = cursor.fetchall()

    total_users = len(users)

    rating_text = "Рейтинг:\n\n"
    top_users = users[:10]

    for i, (uid, balance) in enumerate(top_users, start=1):
        rating_text += f"{i}. ID: {uid}, Баллы: {balance}\n"



    if total_users > 0:
        last_user = users[-1]
        rating_text += f"\nПоследний участник (id: {last_user[0]})"

    rating_text += f"\n\nВсего участников: {total_users}"
    photo = FSInputFile("images/16.jpg")
    await bot.send_photo(callback_query.from_user.id, photo, caption=rating_text)

    await callback_query.answer()
@dp.message(lambda message: message.text == "Админ Панель")

async def admin_panel(message: types.Message):
    if await is_admin(message.from_user.id):
        await message.reply("Панель администратора", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Пост", callback_data="post")],
            [InlineKeyboardButton(text="Рейтинг", callback_data="rating")],
            [InlineKeyboardButton(text="Баллы", callback_data="points")],
            [InlineKeyboardButton(text="Выгрузить базу", callback_data="export")]
        ]))
    else:
        await message.reply("У вас нет доступа к этой панели.")
class AdminStates(StatesGroup):
    waiting_for_points = State()
@dp.callback_query(lambda c: c.data in ["post", "rating", "points", "export"])
async def handle_admin_actions(callback_query: types.CallbackQuery, state: FSMContext):
    action = callback_query.data
    if action == "post":
        await bot.send_message(callback_query.from_user.id, "Введите сообщение для рассылки:")
        await state.set_state(BroadcastStates.waiting_for_message)
    elif action == "rating":
        await bot.send_message(callback_query.from_user.id, "Здесь будет рейтинг.")
    elif action == "points":
        await bot.send_message(callback_query.from_user.id, "Введите новое значение бонуса за реферала (число):")
        await state.set_state(AdminStates.waiting_for_points)
    elif action == "export":
        await export_user_data(callback_query.from_user.id)

    await callback_query.answer()
async def export_user_data(user_id):
    cursor.execute('SELECT user_id, wallet, balance FROM users')
    users_data = cursor.fetchall()

    data = [{'№': i + 1, 'Адрес кошелька': row[1], 'Сумма баллов': row[2]} for i, row in enumerate(users_data)]
    df = pd.DataFrame(data)
    excel_path = 'users_data.xlsx'
    df.to_excel(excel_path, index=False)

    await bot.send_document(user_id, types.FSInputFile(excel_path))
@dp.message(AdminStates.waiting_for_points)
async def set_ref_bonus(message: types.Message, state: FSMContext):
    global ref_bonus
    try:
        new_ref_bonus = int(message.text)
        ref_bonus = new_ref_bonus
        await message.reply(f"Новое значение бонуса за реферала установлено: {ref_bonus}")
        await state.clear()
    except ValueError:
        await message.reply("Пожалуйста, введите корректное число.")
@dp.message(BroadcastStates.waiting_for_message)
async def set_broadcast_message(message: types.Message, state: FSMContext):
    await state.update_data(broadcast_message=message.text)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text = "Предпросмотр", callback_data="preview")],
        [InlineKeyboardButton(text = "Добавить картинку", callback_data="add_image")],
        [InlineKeyboardButton(text = "Добавить URL-кнопку", callback_data="add_url_button")],
        [InlineKeyboardButton(text = "Опубликовать", callback_data="publish")],
        [InlineKeyboardButton(text = "Удалить", callback_data="delete")]
    ])
    await message.reply("Вы хотите добавить изображение?", reply_markup=keyboard)
    await state.set_state(BroadcastStates.ready_to_broadcast)

@dp.callback_query(lambda c: c.data == "add_image", BroadcastStates.ready_to_broadcast)
async def ask_for_image(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.send_message(callback_query.from_user.id, "Пришлите ссылку или медиафайл (до 5 Мб)")
    await state.set_state(BroadcastStates.waiting_for_image)
    await callback_query.answer()

@dp.message(BroadcastStates.waiting_for_image, F.content_type.in_({'photo'}))
async def set_broadcast_image(message: types.Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    await state.update_data(broadcast_image=file_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text = "Предпросмотр", callback_data="preview")],
        [InlineKeyboardButton(text = "Добавить URL-кнопку", callback_data="add_url_button")],
        [InlineKeyboardButton(text = "Опубликовать", callback_data="publish")],
        [InlineKeyboardButton(text = "Удалить", callback_data="delete")]
    ])
    await message.reply("Медиафайл прикреплен к сообщению.", reply_markup=keyboard)
    await state.set_state(BroadcastStates.ready_to_broadcast)

@dp.callback_query(lambda c: c.data == "add_url_button", BroadcastStates.ready_to_broadcast)
async def ask_for_url_buttons(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.send_message(callback_query.from_user.id, "Отправьте мне список URL-кнопок в одном сообщении. Пожалуйста, следуйте этому формату:\n\nКнопка 1 - http://example1.com\nКнопка 2 - http://example2.com")
    await state.set_state(BroadcastStates.waiting_for_url_buttons)
    await callback_query.answer()

@dp.message(BroadcastStates.waiting_for_url_buttons)
async def set_broadcast_url_buttons(message: types.Message, state: FSMContext):
    url_buttons = []
    lines = message.text.split('\n')
    for line in lines:
        parts = line.split(' - ')
        if len(parts) == 2:
            url_buttons.append(InlineKeyboardButton(text=parts[0], url=parts[1]))

    await state.update_data(broadcast_url_buttons=url_buttons)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text = "Предпросмотр", callback_data="preview")],
        [InlineKeyboardButton(text = "Опубликовать", callback_data="publish")],
        [InlineKeyboardButton(text = "Удалить", callback_data="delete")]
    ])
    await message.reply("URL-кнопки сохранены. Продолжайте отправлять сообщения.", reply_markup=keyboard)
    await state.set_state(BroadcastStates.ready_to_broadcast)

@dp.callback_query(lambda c: c.data == "preview", BroadcastStates.ready_to_broadcast)
async def preview_broadcast(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    broadcast_message = data['broadcast_message']
    broadcast_image = data.get('broadcast_image')
    broadcast_url_buttons = data.get('broadcast_url_buttons')

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text = "Отправить", callback_data="send_broadcast")]
    ])
    if broadcast_url_buttons:
        keyboard.inline_keyboard.extend([button] for button in broadcast_url_buttons)

    if broadcast_image:
        await bot.send_photo(callback_query.from_user.id, broadcast_image, caption=broadcast_message, reply_markup=keyboard)
    else:
        await bot.send_message(callback_query.from_user.id, broadcast_message, reply_markup=keyboard)

    await callback_query.answer()

@dp.callback_query(lambda c: c.data == "publish", BroadcastStates.ready_to_broadcast)
async def confirm_publish(callback_query: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text = "Отправить", callback_data="send_broadcast")],
        [InlineKeyboardButton(text = "Удалить", callback_data="delete")]
    ])
    await bot.send_message(callback_query.from_user.id, "Готово к отправке? Нажмите 'Отправить'", reply_markup=keyboard)
    await callback_query.answer()

@dp.callback_query(lambda c: c.data == "delete", BroadcastStates.ready_to_broadcast)
async def delete_broadcast(callback_query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await bot.send_message(callback_query.from_user.id, "Сообщение удалено. Панель администратора", reply_markup=admin_panel_keyboard)
    await callback_query.answer()

@dp.callback_query(lambda c: c.data == "send_broadcast", BroadcastStates.ready_to_broadcast)
async def send_broadcast(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    broadcast_message = data['broadcast_message']
    broadcast_image = data.get('broadcast_image')
    broadcast_url_buttons = data.get('broadcast_url_buttons')

    cursor.execute("SELECT user_id FROM users")
    user_ids = cursor.fetchall()

    keyboard = None
    if broadcast_url_buttons:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[button] for button in broadcast_url_buttons]
        )

    for user_id_tuple in user_ids:
        user_id = user_id_tuple[0]
        try:
            if broadcast_image:
                await bot.send_photo(user_id, broadcast_image, caption=broadcast_message, reply_markup=keyboard)
            else:
                await bot.send_message(user_id, broadcast_message, reply_markup=keyboard)
        except Exception as e:

    await bot.send_message(callback_query.from_user.id, "Рассылка завершена.")
    await state.clear()
    await callback_query.answer()



async def start_reminder_task(user_id):
    if user_id in reminder_tasks:
        reminder_tasks[user_id].cancel()
    
    reminder_tasks[user_id] = asyncio.create_task(schedule_reminder(user_id))
@dp.message(Command('start'))
async def send_welcome(message: types.Message):
    global ref_bonus
    referrer_id = None
    args = message.text.split()
    if len(args) > 1:
        try:
            referrer_id = int(args[1])
        except ValueError:
            pass

    user_id = message.from_user.id
    cursor.execute('SELECT lang, ref_link FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    is_user_admin = await is_admin(user_id)
    if is_user_admin:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Админ Панель")]
            ],
            resize_keyboard=True
        )
    else:
        keyboard = ReplyKeyboardMarkup(keyboard=[], resize_keyboard=True)

    if not user:
        ref_link = f"https://t.me/b1coin_bot?start={user_id}"
        cursor.execute('INSERT INTO users (user_id, lang, ref_link, balance, ref_count) VALUES (?, ?, ?, ?, ?)', (user_id, None, ref_link, 0, 0))
        conn.commit()
        if referrer_id and referrer_id != user_id:
            cursor.execute('UPDATE users SET balance = balance + ?, ref_count = ref_count + 1 WHERE user_id = ?', (ref_bonus, referrer_id,))
            conn.commit()
            cursor.execute('UPDATE users SET balance = 50 WHERE user_id = ?', (user_id,))
            conn.commit()
            cursor.execute('SELECT balance, ref_count FROM users WHERE user_id = ?', (referrer_id,))
            referrer_data = cursor.fetchone()
            await bot.send_message(referrer_id, f"Вы получили {ref_bonus} $B1COIN за приглашение нового пользователя!")
        await message.reply("Select your language:", reply_markup=language_keyboard)
    else:
        lang = user[0]
        ref_link = user[1]
        if lang == 'ru':
            if await check_subscriptions(user_id):
                photo_path = 'start_image.jpg'
                photo = FSInputFile(photo_path)
                await bot.send_photo(user_id, photo, caption="🎊 ТОПОВЫЙ AIRDROP $B1COIN \n\nЗарабатывай баллы $B1COIN за каждого приведенного друга! Самые лучшие и честные условия!\nАбсолютно каждый участник получит DROP от $B1COIN.\n\n🎉 А теперь пригласи хотя бы 1 друга по кнопке:", reply_markup=ref_keyboard)
            else:
                photo = FSInputFile("images/1.jpg")
                await bot.send_photo(user_id, photo, caption=settings['start_message'], reply_markup=keyboard)
                await bot.send_message(message.chat.id, f"🤝 Чтобы участвовать в топовом AIRDROP, сначала подпишись на каналы:\n@victor_moc - канал Виктора, 1 из фаундеров\n@b1coin_ton_ru (RU) - канал токена\n@b1coin_ton (EN) - канал токена\n\nТвоя реферальная ссылка: {ref_link}", reply_markup=check_keyboard)
        else:
            if await check_subscriptions(user_id):
                photo_path = 'start_image.jpg'
                photo = FSInputFile(photo_path)
                await bot.send_photo(user_id, photo, caption="🎊 ТОПОВЫЙ AIRDROP $B1COIN \n\nЗарабатывай баллы $B1COIN за каждого приведенного друга! Самые лучшие и честные условия!\nАбсолютно каждый участник получит DROP от $B1COIN.\n\n🎉 А теперь пригласи хотя бы 1 друга по кнопке:", reply_markup=ref_keyboard)
            else:
                photo = FSInputFile("images/1.jpg")
                await bot.send_photo(user_id, photo, caption=settings['start_message'], reply_markup=keyboard)
                await bot.send_message(message.chat.id, f"🤝 Чтобы участвовать в топовом AIRDROP, сначала подпишись на каналы:\n@victor_moc - канал Виктора, 1 из фаундеров\n@b1coin_ton_ru (RU) - канал токена\n@b1coin_ton (EN) - канал токена\n\nТвоя реферальная ссылка: {ref_link}", reply_markup=check_keyboard)
        await start_reminder_task(user_id)
def is_quiz_completed(task_id):
    quiz_task_ids = [task['id'] for task in tasks if 'options' in task]
    return task_id == max(quiz_task_ids)
@dp.callback_query(F.data == 'lang_ru')
async def process_language_selection_ru(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    ref_link = f"https://t.me/b1coin_bot?start={user_id}"
    cursor.execute('REPLACE INTO users (user_id, lang, ref_link) VALUES (?, ?, ?)', (user_id, 'ru', ref_link))
    conn.commit()
    
    await callback_query.message.edit_reply_markup(reply_markup=None)
    await callback_query.message.reply(settings['start_message'])
    await bot.send_message(callback_query.message.chat.id, f"🤝 Чтобы участвовать в топовом AIRDROP, сначала подпишись на каналы:\n@victor_moc - канал Виктора, 1 из фаундеров\n@b1coin_ton_ru (RU) - канал токена\n@b1coin_ton (EN) - канал токена\n\nТвоя реферальная ссылка: {ref_link}", reply_markup=check_keyboard)
    await callback_query.answer() 
    await start_reminder_task(user_id)

@dp.callback_query(F.data == 'lang_eng')
async def process_language_selection_eng(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    ref_link = f"https://t.me/b1coin_bot?start={user_id}"
    cursor.execute('REPLACE INTO users (user_id, lang, ref_link) VALUES (?, ?, ?)', (user_id, 'ru', ref_link))
    conn.commit()
    
    await callback_query.message.edit_reply_markup(reply_markup=None)
    await callback_query.message.reply(settings['start_message'])
    await bot.send_message(callback_query.message.chat.id, f"🤝 Чтобы участвовать в топовом AIRDROP, сначала подпишись на каналы:\n@victor_moc - канал Виктора, 1 из фаундеров\n@b1coin_ton_ru (RU) - канал токена\n@b1coin_ton (EN) - канал токена\n\nТвоя реферальная ссылка: {ref_link}", reply_markup=check_keyboard)
    await callback_query.answer() 
    await start_reminder_task(user_id)


@dp.callback_query(F.data == 'start_check')
async def check_subscriptions_callback(callback_query: types.CallbackQuery):
    photo_path = 'start_image.jpg'
    photo = FSInputFile(photo_path)
    user_id = callback_query.from_user.id

    if user_id in reminder_tasks:
        reminder_tasks[user_id].cancel()
        del reminder_tasks[user_id]
    if await check_subscriptions(user_id):
        await bot.send_photo(user_id, photo, caption="🎊 ТОПОВЫЙ AIRDROP $B1COIN \n\nЗарабатывай баллы $B1COIN за каждого приведенного друга! Самые лучшие и честные условия!\nАбсолютно каждый участник получит DROP от $B1COIN.\n\n🎉 А теперь пригласи хотя бы 1 друга по кнопке:", reply_markup=ref_keyboard)
    else:
        photo = FSInputFile("images/2.jpg")
        await bot.send_photo(user_id, photo, caption="😵‍💫 Бикона не проведешь! Нужно сначала подписаться на каналы:\n@victor_moc - канал Виктора, 1 из фаундеров\n@b1coin_ton_ru (RU) - канал токена\n@b1coin_ton (EN) - канал токена", reply_markup=check_keyboard)    
    await callback_query.answer() 


@dp.callback_query(F.data == 'ref_b')
async def ref_f(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    ref_link = await get_user(user_id)
    if user_id in reminder_tasks:
        reminder_tasks[user_id].cancel()
        del reminder_tasks[user_id]
    text = (
        "Подключайся со мной к топовому AIRDROP на TON, выполняй простые задания и зарабатывай токены $B1COIN!\n"
        "\n Среди холдеров разыгрывается новенькая Lamborghini...\n\n"
        " - wen lam₿a, sir? 🏎💨!"
    )
    encoded_ref_link = urllib.parse.quote(ref_link[2], safe='')
    encoded_text = urllib.parse.quote(text, safe='')
    share_url = f"https://t.me/share/url?url={encoded_ref_link}&text={encoded_text}"
    menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Меню 🪧", callback_data="menu_b"),
            InlineKeyboardButton(text="Поделиться", url=share_url)
        ]
    ])

    if await check_subscriptions(user_id):
        await bot.send_message(
                                    user_id,
                                    f"<b>{ref_link[2]}</b>\n\n"
                                    "Подключайся со мной к топовому AIRDROP на TON, выполняй простые задания и зарабатывай токены $B1COIN!\n\n"
                                    "Среди холдеров разыгрывается новенькая <b>Lamborghini</b>...\n\n"
                                    "- wen lam₿a, sir? 🏎💨",
                                    parse_mode='HTML',reply_markup =menu_keyboard
                                )
    else:
        photo = FSInputFile("images/2.jpg")
        await bot.send_photo(user_id, photo, caption="😵‍💫 Бикона не проведешь! Нужно сначала подписаться на каналы:\n@victor_moc - канал Виктора, 1 из фаундеров\n@b1coin_ton_ru (RU) - канал токена\n@b1coin_ton (EN) - канал токена", reply_markup=check_keyboard)    
    await callback_query.answer() 

@dp.callback_query(F.data == 'menu_b')
async def ref_f(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    ref_link = await get_user(user_id)
    menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Меню 🪧", callback_data="menu_b")
        ]
    ])

    if await check_subscriptions(user_id):
        photo = FSInputFile("images/3.jpg")
        await bot.send_photo(user_id, photo, caption=f"<strong>Меню</strong>\n\n"
                                    "Выбери действие ниже, чтобы продолжить зарабатывать $B1COIN! 🚀!\n\n",
                                    parse_mode='HTML',reply_markup=menu2_keyboard)  
    else:
        photo = FSInputFile("images/2.jpg")
        await bot.send_photo(user_id, photo, caption="😵‍💫 Бикона не проведешь! Нужно сначала подписаться на каналы:\n@victor_moc - канал Виктора, 1 из фаундеров\n@b1coin_ton_ru (RU) - канал токена\n@b1coin_ton (EN) - канал токена", reply_markup=check_keyboard)    
    await callback_query.answer() 
@dp.callback_query(F.data == 'lamba')
async def ref_f(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    ref_link = await get_user(user_id)
    menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Меню 🪧", callback_data="menu_b"),
            InlineKeyboardButton(text="Пригласить 👥", callback_data="ref_b")
        ]
    ])

    if await check_subscriptions(user_id):
            await bot.send_message(
                user_id,
                "<strong>🏎️ Розыгрыш Lamborghini среди холдеров $B1COIN!</strong>\n\n"
                "🔹 Розыгрыш будет проводиться на блокчейне, что обеспечит полную прозрачность и честность.\n\n"
                "🔹 Розыгрыш состоится, как только будет набрана сумма, заложенная в нашей токеномике.\n\n"
                "🔹 Чем дольше вы храните токены $B1COIN, тем больше баллов начисляется на ваш счет и тем выше ваши шансы на победу!\n\n"
                "Простые правила:\n"
                "1. Холдите $B1COIN в своем кошельке.\n"
                "2. Получайте тикеты за каждый день хранения.\n"
                "3. Участвуйте в розыгрыше и выиграйте Lamborghini!\n\n"
                "Не зависит от локации!\n"
                "Вперед, зарабатывать $B1COIN!",
                parse_mode='HTML',
                reply_markup=menu_keyboard
            )  
    else:
        photo = FSInputFile("images/2.jpg")
        await bot.send_photo(user_id, photo, caption="😵‍💫 Бикона не проведешь! Нужно сначала подписаться на каналы:\n@victor_moc - канал Виктора, 1 из фаундеров\n@b1coin_ton_ru (RU) - канал токена\n@b1coin_ton (EN) - канал токена", reply_markup=check_keyboard)    
    await callback_query.answer()
@dp.callback_query(F.data == 'balance')
async def ref_f(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user = await get_user(user_id)
    menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="Кошелек 💳", callback_data="wallet"),
        InlineKeyboardButton(text="Меню 🪧", callback_data="menu_b")
    ],
    [
        InlineKeyboardButton(text="Условия 📋", callback_data="terms")
    ]
    ])

    if await check_subscriptions(user_id):
            await bot.send_message(
                user_id,
                "Адрес кошелька:\n\n"
                f"{user[5]}\n\n"
                f"Баланс баллов: {user[3]} $B1COIN.\n"
                f"Баланс рефералов: {user[4]} ref.\n"
                "Реферальная ссылка::\n"
                f"{user[2]}\n\n"
                "Чтобы увеличить баланс, выполняй задания во вкладке “Выполнить задание” и приглашай больше друзей!\n\n"
                "Мы отправим $B1COIN по окончании AIRDROP на данный адрес.\n\n"
                "Если вы ошиблись в адресе кошелька или хотите его сменить - просто перейдите во вкладку “Кошелек”.\n",
                parse_mode='HTML',
                reply_markup=menu_keyboard
            )  
    else:
        photo = FSInputFile("images/2.jpg")
        await bot.send_photo(user_id, photo, caption="😵‍💫 Бикона не проведешь! Нужно сначала подписаться на каналы:\n@victor_moc - канал Виктора, 1 из фаундеров\n@b1coin_ton_ru (RU) - канал токена\n@b1coin_ton (EN) - канал токена", reply_markup=check_keyboard)    
    await callback_query.answer() 
@dp.callback_query(F.data == 'wallet')
async def handle_wallet(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user = await get_user(user_id)
    menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Поменять ✅", callback_data="change_wallet"),
            InlineKeyboardButton(text="Назад 🪧", callback_data="menu_b")
        ]
    ])

    if await check_subscriptions(user_id):
        if not user[5]:
            await bot.send_message(
                user_id,
                "💳 Тебе нужно привязать НЕкастодиальный кошелек сети TON - например, Tonkeeper.\n\n"
                "Введи адрес своего Tonkeeper:\n",
                parse_mode='HTML'
            )
            await state.set_state(WalletStates.waiting_for_wallet)
        else:
            await bot.send_message(
                user_id,
                f"💳 Адрес твоего кошелька:\n{user[5]}\n\n"
                "Хочешь его поменять?",
                parse_mode='HTML',
                reply_markup=menu_keyboard
            )
    else:
        photo = FSInputFile("images/2.jpg")
        await bot.send_photo(user_id, photo, caption="😵‍💫 Бикона не проведешь! Нужно сначала подписаться на каналы:\n@victor_moc - канал Виктора, 1 из фаундеров\n@b1coin_ton_ru (RU) - канал токена\n@b1coin_ton (EN) - канал токена", reply_markup=check_keyboard)    

    await callback_query.answer()

@dp.message(WalletStates.waiting_for_wallet)
async def handle_wallet_input(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    wallet_address = message.text.strip()
    menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="Кошелек 💳", callback_data="wallet"),
        InlineKeyboardButton(text="Меню 🪧", callback_data="menu_b")
    ],
    [
        InlineKeyboardButton(text="Условия 📋", callback_data="terms")
    ]
    ])
    if len(wallet_address) == 48:
        cursor.execute('UPDATE users SET wallet = ? WHERE user_id = ?', (wallet_address, user_id))
        conn.commit()
        user = await get_user(user_id)
        await bot.send_message(
            user_id,
            f"Адрес кошелька:\n{user[5]}\n\n"
            f"Баланс баллов: {user[3]} $B1COIN.\n"
            f"Баланс рефералов: {user[4]} ref.\n"
            "Реферальная ссылка:\n"
            f"{user[2]}\n\n"
            "Чтобы увеличить баланс, выполняй задания во вкладке “Выполнить задание” и приглашай больше друзей!\n\n"
            "Мы отправим $B1COIN по окончании AIRDROP на данный адрес.\n\n"
            "Если вы ошиблись в адресе кошелька или хотите его сменить - просто перейдите во вкладку “Кошелек”.\n",
            parse_mode='HTML',reply_markup=menu_keyboard
        )
        await state.clear()
    else:
        await bot.send_message(
            user_id,
            "💳 Проверь, в сообщении должен быть только адрес, 48 символов. Memo/Tag отправлять не нужно.\n\n"
            "Жду от тебя только адрес, много букав!\n\n"
            "Введи адрес своего Tonkeeper:\n",
            parse_mode='HTML'
        )

@dp.callback_query(F.data == 'change_wallet')
async def handle_change_wallet(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    await bot.send_message(
        user_id,
        "Введи новый адрес своего Tonkeeper:\n",
        parse_mode='HTML'
    )
    await state.set_state(WalletStates.waiting_for_wallet)
    await callback_query.answer()
@dp.callback_query(F.data == 'qrcode')
async def handle_qrcode(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user = await get_user(user_id)
    ref_link = user[2]

   
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=5,
        border=1,
    )
    qr.add_data(ref_link)
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')


    base_img = Image.open('1080X1920.png')
    qr_img = qr_img.resize((800, 800))  

    position = ((base_img.width - qr_img.width) // 2, base_img.height - qr_img.height - 100)

    combined_img = Image.new('RGB', base_img.size)
    combined_img.paste(base_img, (0, 0))
    combined_img.paste(qr_img, position)


    final_img_path = 'final_image_with_qr.png'
    combined_img.save(final_img_path)

    photo = FSInputFile(final_img_path)
    await bot.send_photo(user_id, photo, caption="Вот ваш реферальный QR-код!")

    await callback_query.answer() 
class YoutubeTaskStates(StatesGroup):
    waiting_for_youtube_answer = State()
    waiting_for_instagram_answer = State()
    waiting_for_twitter_answer =  State()
@dp.callback_query(lambda c: c.data == 'quest')
async def handle_quest(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    await send_next_task(user_id)
    await callback_query.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith('check_youtube_'))
async def check_youtube_task(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id

    await state.set_state(YoutubeTaskStates.waiting_for_youtube_answer)
    await state.update_data(youtube_task=2)
    
    await bot.send_message(
        user_id,
        "Как называется плейлист с прямыми эфирами каждое воскресенье?:"
    )
@dp.message(YoutubeTaskStates.waiting_for_youtube_answer)
async def handle_youtube_answer(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()

    if data.get('youtube_task') == 2:
        answer = message.text.strip()
        if answer.lower() == "еженедельный обзор":
            task = tasks[1]
            cursor.execute("UPDATE users SET balance = COALESCE(balance, 0) + ?, current_task = current_task + 1 WHERE user_id = ?", (task['reward'], user_id))
            conn.commit()

            await bot.send_message(
                user_id,
                f"Ты успешно завершил задание и заработал {task['reward']} $B1COIN!"
            )
            await state.clear()
            await send_next_task(user_id)
        else:
            photo = FSInputFile("images/2.jpg")
            await bot.send_photo(user_id, photo, caption="😵‍💫 Бикона не проведешь! Выполняй задание.")    

            await handle_quest(callback_query=types.CallbackQuery(id="dummy", from_user=types.User(id=user_id, is_bot=False), message=None, data="quest"), state=state)
    else:
        await bot.send_message(user_id, "Пожалуйста, сначала выполните задание.")

@dp.callback_query(lambda c: c.data and c.data.startswith('check_instagram_'))
async def check_instagram_task(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user = await get_user(user_id)
    current_task_id = user[-1]

    if current_task_id == 2:
        await state.set_state(YoutubeTaskStates.waiting_for_instagram_answer)
        await state.update_data(instagram_task=3)

        await bot.send_message(
            user_id,
            "Какой последний хештег указан в описании аккаунта?:"
        )

    await callback_query.answer()
@dp.message(YoutubeTaskStates.waiting_for_instagram_answer)
async def handle_instagram_answer(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()

    if data.get('instagram_task') == 3:
        answer = message.text.strip()
        if answer.lower() == "#b1coin":
            task = tasks[2]
            cursor.execute("UPDATE users SET balance = COALESCE(balance, 0) + ?, current_task = current_task + 1 WHERE user_id = ?", (task['reward'], user_id))
            conn.commit()

            await bot.send_message(
                user_id,
                f"Ты успешно завершил задание и заработал {task['reward']} $B1COIN!"
            )
            await state.clear()
            await send_next_task(user_id)
        else:
            photo = FSInputFile("images/2.jpg")
            await bot.send_photo(user_id, photo, caption="😵‍💫 Бикона не проведешь! Выполняй задание.")  
            await handle_quest(callback_query=types.CallbackQuery(id="dummy", from_user=types.User(id=user_id, is_bot=False), message=None, data="quest"), state=state)
    else:
        await bot.send_message(user_id, "Пожалуйста, сначала выполните задание.")

@dp.callback_query(lambda c: c.data and c.data.startswith('check_twitter_'))
async def check_twitter_task(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user = await get_user(user_id)
    current_task_id = user[-1]

    if current_task_id == 3: 
        await state.set_state(YoutubeTaskStates.waiting_for_twitter_answer)
        await state.update_data(twitter_task=4)

        await bot.send_message(
            user_id,
            "Какой хештег указан в закрепленном твите?:"
        )

    await callback_query.answer()
@dp.message(YoutubeTaskStates.waiting_for_twitter_answer)
async def handle_twitter_answer(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()

    if data.get('twitter_task') == 4:
        answer = message.text.strip()
        if answer.lower() == "#b1coinarmy":
            task = tasks[3]
            cursor.execute("UPDATE users SET balance = COALESCE(balance, 0) + ?, current_task = current_task + 1 WHERE user_id = ?", (task['reward'], user_id))
            conn.commit()

            await bot.send_message(
                user_id,
                f"Ты успешно завершил задание и заработал {task['reward']} $B1COIN!"
            )
            photo = FSInputFile("images/21.jpg")
            await bot.send_photo(user_id, photo, caption="Задание #4А/15: КВИЗ $B1COIN.\n\nДорогой человек, теперь пришло время... вступить в ряды $B1COIN ARMY, по-настоящему ценной части нашего аирдропа.\n\nКВИЗ: Это 7 вопросов с выбором 1го правильного утверждения из 3х.\n\nЗа каждый правильный ответ ты заработаешь 50 $B1COIN.")

            await state.clear()
            await send_next_task(user_id)
        else:
            photo = FSInputFile("images/2.jpg")
            await bot.send_photo(user_id, photo, caption="😵‍💫 Бикона не проведешь! Выполняй задание.")  
            await handle_quest(callback_query=types.CallbackQuery(id="dummy", from_user=types.User(id=user_id, is_bot=False), message=None, data="quest"), state=state)
    else:
        await bot.send_message(user_id, "Пожалуйста, сначала выполните задание.")
@dp.callback_query(lambda c: c.data and c.data.startswith('answer_'))
async def handle_quiz_answer(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data.split('_')
    task_id = int(data[1])
    selected_option = int(data[2])
    user = await get_user(user_id)
    current_task_id = user[-1]
    
    if task_id == current_task_id:
        task = tasks[current_task_id]
        correct_text = task.get('correct_text', "Правильный ответ!")
        incorrect_text = task.get('incorrect_text', "Неправильный ответ. Попробуй еще раз.")
        if selected_option == task['correct_option']:
            reward = task['reward']
            cursor.execute("UPDATE users SET balance = COALESCE(balance, 0) + ?, current_task = current_task + 1 WHERE user_id = ?", (reward, user_id))
            conn.commit()
            cursor.execute("UPDATE users SET balance_q = COALESCE(balance_q, 0) + ? WHERE user_id = ?", (reward, user_id))
            conn.commit()
            photo = FSInputFile("images/4.jpg")
            await bot.send_photo(user_id, photo, caption=f"{correct_text}")
            if task_id == 10:
                user2 = await get_user(user_id)
                photo = FSInputFile("images/15.jpg")
                await bot.send_photo(user_id, photo, caption=f"Класс! Ты прошел квиз!\n\nСветлые головы нужны нашему комьюнити...\n\nТы заработал {user2[6]} $B1COIN.\n\nВелком проходить следующие задания!")
        else:
            cursor.execute("UPDATE users SET current_task = current_task + 1 WHERE user_id = ?", (user_id,))
            conn.commit()
            photo = FSInputFile("images/4.jpg")
            await bot.send_photo(user_id, photo, caption=f"{incorrect_text}")
            if task_id == 10:
                user2 = await get_user(user_id)
                photo = FSInputFile("images/15.jpg")
                await bot.send_photo(user_id, photo, caption=f"Класс! Ты прошел квиз!\n\nСветлые головы нужны нашему комьюнити...\n\nТы заработал {user2[6]} $B1COIN.\n\nВелком проходить следующие задания!")
        await send_next_task(user_id)
    else:
        await bot.send_message(user_id, "Пожалуйста, сначала выполните текущее задание.")

    await callback_query.answer()

async def send_next_task(user_id):
    user = await get_user(user_id)
    current_task_id = user[-1]
    if current_task_id < len(tasks):
        task = tasks[current_task_id]
        if 'optionss' in task:

            task_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text=option, callback_data=f"answer_{current_task_id}_{i}") for i, option in enumerate(task['optionss'])
                ],
                [
                    InlineKeyboardButton(text="Меню 🪧", callback_data="menu_b")
                ]
            ])
        elif task.get('type') == 'twitter':
            task_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Перейти", url=task['link'])],
                [InlineKeyboardButton(text="Пропустить 😕", callback_data=f"skip_task_{task['id']}")],
                [InlineKeyboardButton(text="Меню 🪧", callback_data="menu_b")]
            ])
        elif task.get('referral'):
            task_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Далее 😎", callback_data=f"send_task_{task['id']}")],
                [InlineKeyboardButton(text="Пригласить 👥", callback_data="ref_b")],
                [InlineKeyboardButton(text="Меню 🪧", callback_data="menu_b")]
            ])
        elif task.get('type') == 'comments' and task.get('platform', '') != 'Instagram':
            task_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Проверить ✅", callback_data=f"check_comments_{task['id']}")],
                [InlineKeyboardButton(text="Пропустить 🙂", callback_data=f"skip_task_{task['id']}")],
                [InlineKeyboardButton(text="Меню 🪧", callback_data="menu_b")]
            ])
        elif task.get('platform', '') == 'Instagram' and task.get('type') == 'comments':
            latest_posts = await get_latest_instagram_posts('b1coin')
            task['description'] = f"В Instagram-аккаунте токена $B1COIN:\n{latest_posts[0]}\n{latest_posts[1]}\n{latest_posts[2]}\n"
            task_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Перейти #1", url=latest_posts[0])],
                [InlineKeyboardButton(text="Перейти #2", url=latest_posts[1])],
                [InlineKeyboardButton(text="Перейти #3", url=latest_posts[2])],
                [InlineKeyboardButton(text="Проверить ✅", callback_data=f"check_task_{task['id']}")],
                [InlineKeyboardButton(text="Меню 🪧", callback_data="menu_b")]
            ])
        elif task['id'] == 2:  
            task_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Перейти на YouTube", url=task['link'])],
                
                [InlineKeyboardButton(text="Проверить ✅", callback_data=f"check_youtube_{task['id']}")]
                
            ])
        elif task['id'] == 3: 
            task_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Перейти на Instagram", url=task['link'])],
                [InlineKeyboardButton(text="Проверить ✅", callback_data=f"check_instagram_{task['id']}")],
                [InlineKeyboardButton(text="Пропустить 🙂", callback_data=f"skip_task_{task['id']}")]
                
                
            ])
        elif task['id'] == 1:
             task_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Проверить ✅", callback_data=f"check_task_{task['id']}")],
                
                [InlineKeyboardButton(text="Меню 🪧", callback_data="menu_b")]
            ])
        elif task['id'] == 4:
            task_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Перейти на Twitter(X)", url=task['link'])],
                [InlineKeyboardButton(text="Проверить ✅", callback_data=f"check_twitter_{task['id']}")],
                [InlineKeyboardButton(text="Пропустить 🙂", callback_data=f"skip_task_{task['id']}")],
                [InlineKeyboardButton(text="Меню 🪧", callback_data="menu_b")]
            ])
        else:
            task_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Проверить ✅", callback_data=f"check_task_{task['id']}")],
                [InlineKeyboardButton(text="Пропустить 🙂", callback_data=f"skip_task_{task['id']}")],
                [InlineKeyboardButton(text="Меню 🪧", callback_data="menu_b")]
            ])
        photos = ['images/5.jpg','images/6.jpg','images/7.jpg','images/8.jpg','images/9.jpg','images/10.jpg','images/11.jpg','images/12.jpg','images/13.jpg','images/14.jpg','images/15.jpg',
                'images/16.jpg','images/17.jpg','images/18.jpg','images/20.jpg','images/21.jpg','images/22.jpg','images/23.jpg','images/24.jpg'        
        ]
        
        if 'options' in task:
            photo = FSInputFile(random.choice(photos))
            await bot.send_photo(user_id, photo, caption=f"{task['title']}\n\n{task['description']}\n\n{task['options'][0]}\n{task['options'][1]}\n{task['options'][2]}\n\nТы заработаешь {task['reward']} $B1COIN.",
                reply_markup=task_keyboard)
        else:
            photo = FSInputFile(random.choice(photos))
            await bot.send_photo(user_id, photo, caption=f"{task['title']}\n\n{task['description']}\n\nТы заработаешь {task['reward']} $B1COIN.",
                reply_markup=task_keyboard)  
    else:
        photo = FSInputFile("images/7.jpg")
        await bot.send_photo(user_id, photo, caption="Пока что заданий больше нет!\n\nПриходи попозже... Еще заработаем с тобой кучу $B1COIN !")


@dp.callback_query(lambda c: c.data and c.data.startswith('skip_task_'))
async def handle_skip_task(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user = await get_user(user_id)
    current_task_id = user[-1]
    task_id = user[-1]
    cursor.execute("UPDATE users SET current_task =current_task + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    if (task_id == 3):
        photo = FSInputFile("images/21.jpg")
        await bot.send_photo(user_id, photo, caption="Задание #4А/15: КВИЗ $B1COIN.\n\nДорогой человек, теперь пришло время... вступить в ряды $B1COIN ARMY, по-настоящему ценной части нашего аирдропа.\n\nКВИЗ: Это 7 вопросов с выбором 1го правильного утверждения из 3х.\n\nЗа каждый правильный ответ ты заработаешь 50 $B1COIN.")

    await send_next_task(user_id)
    await callback_query.answer()
@dp.callback_query(lambda c: c.data and c.data.startswith('send_task_'))
async def handle_send_task(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    task_id = int(callback_query.data.split('_')[-1])
    cursor.execute("UPDATE users SET current_task = ? WHERE user_id = ?", (task_id,user_id,))
    conn.commit()
    await send_next_task(user_id)
    await callback_query.answer()
@dp.callback_query(lambda c: c.data and c.data.startswith('check_comments_'))
async def check_comments(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user = await get_user(user_id)
    task_id = user[-1]
    current_task_id = user[-1]
    task = tasks[current_task_id]

    if task_id == current_task_id:
        group_id = task['channel'] 

        try:
            comments_data = await get_last_posts_comments(group_id)
            user_commented = any(
                any(comment['user'] == callback_query.from_user.username for comment in post['comments'])
                for post in comments_data
            )
            if user_commented:
                reward = task['reward']
                cursor.execute("UPDATE users SET balance = COALESCE(balance, 0) + ?, current_task = current_task + 1 WHERE user_id = ?", (reward, user_id))
                conn.commit()
                await bot.send_message(user_id, f"Ты заработал {reward} $B1COIN! Теперь у тебя {user[3] + reward if user[3] else reward} $B1COIN.")
                await send_next_task(user_id)
            else:
                await bot.send_message(user_id, "Ты еще не оставил комментарий на последних трех постах.")
        except Exception as e:
            await bot.send_message(user_id, "Произошла ошибка при проверке комментариев. Попробуйте позже.")
    else:
        await bot.send_message(user_id, "Пожалуйста, сначала выполните текущее задание.")

    await callback_query.answer()


@dp.message(F.text.contains('https://x.com/'))
async def handle_twitter_link(message: types.Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    current_task_id = user[-1]

    if current_task_id < len(tasks):
        task = tasks[current_task_id]
        if task.get('type') == 'twitter':
            tweet_link = message.text.strip()
            if validate_tweet_link(tweet_link):
                reward = task['reward']
                cursor.execute("UPDATE users SET balance = COALESCE(balance, 0) + ?, current_task = current_task + 1 WHERE user_id = ?", (reward, user_id))
                conn.commit()
                await bot.send_message(
                    user_id,
                    f"Ты заработал {reward} $B1COIN! Теперь у тебя {user[3] + reward if user[3] else reward} $B1COIN.",
                )
                await send_next_task(user_id)
            else:
                await bot.send_message(
                    user_id,
                    "😵‍💫 Либо ты пытаешься провести Бикона, либо ссылка некорректна! Отправь реальную ссылку на свой репост ниже:"
                )
        else:
            await bot.send_message(user_id, "Пожалуйста, следуй инструкциям текущего задания.")
    else:
        await bot.send_message(user_id, "Пожалуйста, сначала выполните текущее задание.")

def validate_tweet_link(tweet_link):
    return tweet_link.startswith("https://x.com/")

@dp.callback_query(lambda c: c.data and c.data.startswith('check_task_'))
async def check_task(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    user = await get_user(user_id)
    task_id = user[-1]
    current_task_id = user[-1]

    if task_id == current_task_id:
        task = tasks[current_task_id]
        reward = task['reward']
        if await check_subscriptions2(user_id):
            cursor.execute("UPDATE users SET balance = COALESCE(balance, 0) + ?, current_task = current_task + 1 WHERE user_id = ?", (reward, user_id))
            conn.commit()

            await bot.send_message(
                user_id,
                f"Ты заработал {reward} $B1COIN! Теперь у тебя {user[3] + reward if user[3] else reward} $B1COIN.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Продолжить к следующему заданию 🚀", callback_data="quest")],
                    [InlineKeyboardButton(text="Меню 🪧", callback_data="menu_b")]
                ])
            )
        else:
            task_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Проверить ✅", callback_data=f"check_task_{task['id']}")],
                [InlineKeyboardButton(text="Меню 🪧", callback_data="menu_b")]
            ])
            photo = FSInputFile("images/2.jpg")
            await bot.send_photo(user_id, photo, caption="😵‍💫 Бикона не проведешь! Выполняй задание.")  
    else:
        await bot.send_message(user_id, "Пожалуйста, сначала выполните текущее задание.")

    await callback_query.answer()
    
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())

