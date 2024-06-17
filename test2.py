import asyncio
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest, GetRepliesRequest
from telethon.tl.types import PeerChannel

API_ID = '29719825'
API_HASH = '7fa19eeed8c2e5d35036fafb9a716f18'
PHONE_NUMBER = '+99362896637'

async def get_last_posts_comments(channel_username, num_posts=3):
    client = TelegramClient('session_name', API_ID, API_HASH)
    await client.start(phone=lambda: PHONE_NUMBER)

    comments_data = []
    try:
        channel = await client.get_entity(channel_username)
        history = await client(GetHistoryRequest(
            peer=PeerChannel(channel.id),
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
            post_data = {
                "post_id": post.id,
                "post_message": post.message,
                "comments": []
            }
            result = await client(GetRepliesRequest(
                peer=PeerChannel(channel.id),
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
                if sender:
                    post_data["comments"].append({
                        "user": sender.username,
                        "comment": comment.message
                    })
                else:
                    post_data["comments"].append({
                        "user": None,
                        "comment": comment.message
                    })

            comments_data.append(post_data)
    finally:
        await client.disconnect()

    return comments_data
