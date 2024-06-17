import instaloader
import asyncio

async def get_latest_instagram_posts(username, num_posts=3):
    L = instaloader.Instaloader()
    posts = []
    
    profile = await asyncio.to_thread(instaloader.Profile.from_username, L.context, username)
    
    for post in profile.get_posts():
        if len(posts) >= num_posts:
            break
        posts.append(f"https://www.instagram.com/p/{post.shortcode}/")
    
    return posts
