import instaloader
import asyncio

async def get_latest_instagram_posts(username, num_posts=3):
    # Инициализация Instaloader с использованием сохраненной сессии
    L = instaloader.Instaloader()
    session_file = '/root/.config/instaloader/session-sahatown'
    L.load_session_from_file('sahatown', session_file)
    
    # Получение профиля пользователя
    profile = await asyncio.to_thread(instaloader.Profile.from_username, L.context, username)
    
    # Получение последних постов
    posts = []
    for post in profile.get_posts():
        if len(posts) >= num_posts:
            break
        posts.append(f"https://www.instagram.com/p/{post.shortcode}/")
    
    return posts

