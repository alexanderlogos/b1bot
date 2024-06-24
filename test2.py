import asyncio
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest, GetRepliesRequest
from telethon.tl.types import PeerChannel
from telethon.sessions import StringSession

API_ID = '29719825'
API_HASH = '7fa19eeed8c2e5d35036fafb9a716f18'
PHONE_NUMBER = '+79917233514'
STRING_SESSION = '1ApWapzMBuwFVnCkR-mYLf5P4xWw-YgiqSzWK4mhfvljEUBymG5PrYiwMTQvnWkvaaAQfxTGsB_J-SIwOucIX7AHEJvSDOjUPq2A54bqIfAbHXI2w3wzLyhxtLZt_RMtT33Y-yylJRtEr36r-6pIifJXk4sVTo-tUx-ohtFH0gPw4Ydof2-cr1bTiscnpK7i4BSLIXeqhPrcacp2dJCLIOVpxNSyAceGx89_m6v3jujshX1m7M_2RjUDPbkEE21J6jZik4y1QvoGcA-g1c5G5BA9BlCp8KBKoJwQwR7Voz1trYqPJwlWp3pHpa3mz2xN_m3QX1ccLGUjTifdsGHpv29TQL-MuBMQ='


async def get_last_posts_comments(channel_username, num_posts=3):
    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.start(phone=lambda: PHONE_NUMBER)

    comments_data = []
    try:
        channel = await client.get_entity(channel_username)
        peer_channel = PeerChannel(channel.id)

        history = await client(GetHistoryRequest(   
            peer=peer_channel,
            offset_id=0,
            offset_date=None,
            add_offset=0,
            limit=num_posts,
            max_id=0,
            min_id=0,
            hash=0
        ))

        posts = history.messages

        for post in posts:
            if not post.id or not post.message:
                print(f"Skipping invalid post: {post}")
                continue

            post_data = {
                "post_id": post.id,
                "post_message": post.message,
                "comments": []
            }

            try:
                result = await client(GetRepliesRequest(
                    peer=peer_channel,
                    msg_id=post.id,
                    offset_id=0,
                    offset_date=None,
                    add_offset=0,
                    limit=100,
                    max_id=0,
                    min_id=0,
                    hash=0
                ))

                comments = result.messages
                for comment in comments:
                    sender = await client.get_entity(comment.from_id.user_id) if comment.from_id else None
                    post_data["comments"].append({
                        "user": sender.username if sender else None,
                        "comment": comment.message
                    })
            except Exception as e:
                print(f"Failed to get replies for post {post.id}: {e}")

            comments_data.append(post_data)
    finally:
        await client.disconnect()

    return comments_data

async def main():
    comments = await get_last_posts_comments("@b1coin_ton_ru")
    for comment in comments:
        print(comment)

if __name__ == "__main__":
    asyncio.run(main())