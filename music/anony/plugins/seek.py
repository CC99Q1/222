from pyrogram import filters, types

from anony import anon, app, db, lang, queue
from anony.helpers import can_manage_vc


@app.on_message(
    filters.regex(r"^(تقديم|ترجيع)\s+(\d+)$")
    & (filters.group | filters.channel)
    & ~app.bl_users
)
@lang.language()
@can_manage_vc
async def _seek(_, m: types.Message):
    try:
        command = m.matches[0].group(1)
        to_seek = int(m.matches[0].group(2))
    except (ValueError, TypeError):
        return await m.reply_text(m.lang["play_seek_usage"].format("تقديم / ترجيع"))

    if to_seek < 10:
        return await m.reply_text(m.lang["play_seek_min"])

    if not await db.get_call(m.chat.id):
        return await m.reply_text(m.lang["not_playing"])

    if not await db.playing(m.chat.id):
        return await m.reply_text(m.lang["play_already_paused"])

    media = queue.get_current(m.chat.id)
    if not media.duration_sec:
        return await m.reply_text(m.lang["play_seek_no_dur"])

    sent = await m.reply_text(m.lang["play_seeking"])
    if command == "ترجيع":
        stype = m.lang["backward"]
        start_from = media.time - to_seek
        if start_from < 1:
            start_from = 1
    else:
        stype = m.lang["forward"]
        start_from = media.time + to_seek
        if start_from + 10 > media.duration_sec:
            start_from = media.duration_sec - 5

    if m.from_user:
        user = m.from_user.mention
    elif m.sender_chat:
        user = m.sender_chat.title
    else:
        user = "Anonymous Admin"

    media.time = start_from


    await anon.play_media(
        chat_id=m.chat.id,
        message=sent,
        media=media,
        _lang=m.lang,
    )


    try:
        await sent.delete()
    except:
        pass  

 
    await m.reply_text(
        m.lang["play_seeked"].format(stype, start_from, user)
    )
   