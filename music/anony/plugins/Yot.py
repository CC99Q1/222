import os
import shutil
import asyncio
from pyrogram import filters, types
from pyrogram.enums import ChatType
from anony import app, lang, yt, config 
from anony.helpers.fsub import check_force_sub

DEVELOPER_NAME = None

async def get_developer_name():

    global DEVELOPER_NAME
    if DEVELOPER_NAME is None:
        try:

            user = await app.get_users(config.OWNER_ID)

            if user.last_name:
                DEVELOPER_NAME = f"{user.first_name} {user.last_name}"
            else:
                DEVELOPER_NAME = user.first_name
        except Exception as e:
            print(f"[Yout DL Error] فشل في جلب اسم المطور: {e}")
            DEVELOPER_NAME = "المطور"
    return DEVELOPER_NAME

def get_video_id_from_link(query: str):

    query = query.strip()
    
    
    if "youtube.com/shorts/" in query:
        video_id = query.split("/shorts/")[1].split("?")[0].split("&")[0]
        return f"https://www.youtube.com/watch?v={video_id}"
    
    
    elif "youtube.com/watch" in query and "v=" in query:
        video_id = query.split("v=")[1].split("?")[0].split("&")[0]
        return f"https://www.youtube.com/watch?v={video_id}"
        
    
    elif "youtu.be/" in query:
        video_id = query.split("youtu.be/")[1].split("?")[0].split("&")[0]
        return f"https://www.youtube.com/watch?v={video_id}"
    
   
    return query


@app.on_message(
    filters.command(["يوت", "yt"], prefixes=["/", "!", ".", ""])
    & (filters.group | filters.channel | filters.private)
    & ~app.bl_users
)
@lang.language()
@check_force_sub  
async def yout_downloader(_, m: types.Message):

    
    file_path_to_send = None 

    if len(m.command) < 2:
        return await m.reply_text("<b><u>خطأ في الاستخدام**\n\nاكتب: <code>يوت</code> + اسم الأغنية أو رابط يوتيوب</b></u>")

    query = " ".join(m.command[1:]).strip()
    query = get_video_id_from_link(query)
   

    sent_text = m.lang.get("play_searching", "🔎")
    
    sent = None
    if m.chat.type != ChatType.PRIVATE:
        sent = await m.reply_text(sent_text)
    else:
        sent = await m.reply_text("...") 

    try:
        if m.chat.type != ChatType.PRIVATE:
            await m.delete()
    except Exception as e:
        print(f"[Yout DL] Failed to delete user command: {e}")
    
    try:
        track = await yt.search(query, m.id, video=False)
        if not track:
            return await sent.edit_text("<b><u>لم أتمكن من العثور على أي نتائج. جرب شيء اخر</b></u>")
    except Exception as e:
        print(f"[Yout DL Search Error] {e}")
        return await sent.edit_text(f"<b><u>لم أتمكن من العثور على أي نتائج. جرب شيء اخر</b></u>")
    
    try:
        file_path_to_send = await yt.download_mp3(track.id)
        
        if not file_path_to_send or not os.path.exists(file_path_to_send):
            raise Exception("<b><u>لم أتمكن من العثور على أي نتائج. جرب شيء اخر</b></u>")
            
    except Exception as e:
        print(f"[Yout DL Download/Cache Error] {e}")
        return await sent.edit_text(f"<b><u>لم أتمكن من العثور على أي نتائج. جرب شيء اخر</b></u>")

    
    user_mention = m.from_user.mention if m.from_user else (
        m.sender_chat.title if m.sender_chat else "مستخدم"
    )
    
    caption = f"↯︰Uploader : {user_mention}"

    try:
        button_text = m.lang.get("support", "قناه السورس") 
        button_url = config.SUPPORT_CHANNEL 

        if not button_url:
            print("[Yout DL Error] رابط القناة (SUPPORT_CHANNEL) غير موجود في الكونفج.")
            keyboard = None
        else:
            keyboard = types.InlineKeyboardMarkup(
                [
                    [
                        types.InlineKeyboardButton(
                            text=button_text,
                            url=button_url
                        )
                    ]
                ]
            )
        
        performer_name = await get_developer_name()

        await m.reply_audio(
            audio=file_path_to_send,
            caption=caption,
            title=track.title,
            performer=performer_name,
            duration=track.duration_sec,
            reply_markup=keyboard
        )
        await sent.delete() 
    
    except Exception as e:
        print(f"[Yout DL Send Error] {e}")
        await sent.edit_text(f"<b><u>حدث خطأ أثناء إرسال الملف: {e}</b></u>")
    
    finally:
        
        pass



@app.on_message(
    filters.command(["فيد", "vid", "video"], prefixes=["/", "!", ".", ""])
    & (filters.group | filters.channel | filters.private)
    & ~app.bl_users
)
@lang.language()
@check_force_sub 
async def vid_downloader(_, m: types.Message):

    
    file_path_to_send = None 

    if len(m.command) < 2:
        return await m.reply_text("<b><u>خطأ في الاستخدام**\n\nاكتب: <code>فيد</code> + اسم الفيديو أو رابط يوتيوب</b></u>")

    
    query = " ".join(m.command[1:]).strip()
    query = get_video_id_from_link(query)
    

    sent_text = m.lang.get("play_searching", "🔎")
    
    sent = None
    if m.chat.type != ChatType.PRIVATE:
        sent = await m.reply_text(sent_text)
    else:
        sent = await m.reply_text("...") 

    try:
        if m.chat.type != ChatType.PRIVATE:
            await m.delete()
    except Exception as e:
        print(f"[Vid DL] Failed to delete user command: {e}")
    
    try:
        
        track = await yt.search(query, m.id, video=True)
        if not track:
            return await sent.edit_text("<b><u>لم أتمكن من العثور على أي نتائج. جرب شيء اخر</b></u>")
    except Exception as e:
        print(f"[Vid DL Search Error] {e}")
        return await sent.edit_text(f"<b><u>لم أتمكن من العثور على أي نتائج. جرب شيء اخر</b></u>")
    
    try:
        
        file_path_to_send = await yt.download(track.id, video=True) 
        
        if not file_path_to_send or not os.path.exists(file_path_to_send):
            raise Exception("<b><u>لم أتمكن من العثور على أي نتائج. جرب شيء اخر</b></u>")
            
    except Exception as e:
        print(f"[Vid DL Download/Cache Error] {e}")
        return await sent.edit_text(f"<b><u>لم أتمكن من العثور على أي نتائج. جرب شيء اخر</b></u>")

    
    user_mention = m.from_user.mention if m.from_user else (
        m.sender_chat.title if m.sender_chat else "مستخدم"
    )
    
    caption = f"↯︰UPloader : {user_mention}"

    try:
        button_text = m.lang.get("support", "قناه السورس") 
        button_url = config.SUPPORT_CHANNEL 

        if not button_url:
            print("[Vid DL Error] رابط القناة (SUPPORT_CHANNEL) غير موجود في الكونفج.")
            keyboard = None
        else:
            keyboard = types.InlineKeyboardMarkup(
                [
                    [
                        types.InlineKeyboardButton(
                            text=button_text,
                            url=button_url
                        )
                    ]
                ]
            )
        
        
        await m.reply_video(
            video=file_path_to_send,
            caption=caption,
            duration=track.duration_sec,
            reply_markup=keyboard
        )
        
        await sent.delete() 
    
    except Exception as e:
        print(f"[Vid DL Send Error] {e}")
        await sent.edit_text(f"<b><u>حدث خطأ أثناء إرسال الملف: {e}</b></u>")
    
    finally:
       
        if file_path_to_send and os.path.exists(file_path_to_send):
            try:
                os.remove(file_path_to_send)
            except Exception as e:
                print(f"[Vid DL Cleanup Error] {e}")