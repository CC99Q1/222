import re  
from pyrogram import filters, types, enums
from anony import anon, app, config, db, lang, queue, tg, yt
from anony.helpers import buttons, utils
from anony.helpers._play import checkUB
from anony.helpers.fsub import check_force_sub 


@app.on_message(
    filters.command(
        [
            "play",
            "playforce",
            "vplay",
            "vplayforce",
            "شغل",
            "تشغيل",
            "شغل فيديو",
            "تشغيل فيديو",
        ],
        prefixes=["/", "!", ".", ""],
    )
    & (filters.group | filters.channel)
    & ~app.bl_users
)
@lang.language()
@check_force_sub 
@checkUB
async def play_hndlr(
    _, 
    m: types.Message,
    force: bool = False,
    video: bool = False,
    url: str = None,  
) -> None:
    sent = await m.reply_text(m.lang["play_searching"])


    playmode_admin = await db.get_play_mode(m.chat.id)
    

    is_admin = False 
    

    if m.sender_chat:

        is_admin = True
    elif m.from_user:

        try:
            member = await _.get_chat_member(m.chat.id, m.from_user.id)
            if member.status in (enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER):
                is_admin = True
        except Exception:

            is_admin = False 


    if playmode_admin and not is_admin:

        return await sent.edit_text(m.lang["play_admin_only"])


    if len(queue.get_queue(m.chat.id)) >= 20:
        return await sent.edit_text(m.lang["queue_full"])


    query = ""
    file = None
    is_video = video 

   
    if m.command:
        command = m.command[0].lower()
        if command in ["vplay", "vplayforce", "شغل فيديو", "تشغيل فيديو"]:
            is_video = True

   
    if m.reply_to_message and m.reply_to_message.media:
        media = tg.get_media(m.reply_to_message)
        if media:
            setattr(sent, "lang", m.lang)

            file = await tg.download(m.reply_to_message, sent)
            is_video = file.video 
            
    if not file:
        if url:

            query = url
        elif len(m.command) > 1:
            
            query = " ".join(m.command[1:]).strip()
        elif m.reply_to_message and m.reply_to_message.text:
            
            query = m.reply_to_message.text.strip()


    
    if query and ("youtube.com" in query or "youtu.be" in query):
        
        match = re.search(r"(https://(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[a-zA-Z0-9_-]+)", query)
        if match:
            query = match.group(1)
    

  
    if file:
        pass
    elif query:
        
        file = await yt.search(query, sent.id, video=is_video)
    else:
        return await sent.edit_text(m.lang["play_usage"])
        

    if file and file.duration_sec == 0:
        is_video = True
        file.video = True



    if not file:
        return await sent.edit_text(
            m.lang["play_not_found"].format(config.SUPPORT_CHAT)
        )

    if file.duration_sec > 3600 and file.duration_sec != 0:
        return await sent.edit_text(m.lang["play_duration_limit"])



    user_mention = m.from_user.mention if m.from_user else (
        m.sender_chat.title if m.sender_chat else m.lang["anonymous_admin"]
    )
    file.user = user_mention
    
    if force:
        queue.force_add(m.chat.id, file)
    else:
        position = queue.add(m.chat.id, file)

        if await db.get_call(m.chat.id):
            return await sent.edit_text(
                m.lang["play_queued"].format(
                    position,
                    file.url,
                    file.title,
                    file.duration,
                    user_mention,
                ),
                reply_markup=buttons.play_queued(
                    m.chat.id, file.id, m.lang["play_now"]
                ),
            )

    if not file.file_path:
        try:
            file.file_path = await yt.download(file.id, video=is_video)
        except Exception as e:
            print(f"[Play.py] Error in yt.download: {e}")
            await anon.stop(m.chat.id)
            return await sent.edit_text(
                m.lang["error_no_file"].format(config.SUPPORT_CHAT)
            )

    await anon.play_media(
        chat_id=m.chat.id, message=sent, media=file, _lang=m.lang
    )