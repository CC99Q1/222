import asyncio
import os
import json
import re  
from pyrogram import errors, filters, types
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from anony import app, db, lang
broadcasting = False

@app.on_message(filters.command(["broadcast", "اذاعه"], prefixes=["", "/", "!", "."]) & app.sudoers)
@lang.language()
async def _broadcast(_, message: types.Message):
    global broadcasting
    if not message.reply_to_message:
        return await message.reply_text(message.lang["gcast_usage"])

    if broadcasting:
        return await message.reply_text(message.lang["gcast_active"])

    msg = message.reply_to_message
    count, ucount = 0, 0
    chats = []
    sent = await message.reply_text(message.lang["gcast_start"])

    
    broadcast_mode = "users" 
    if len(message.command) > 1 and message.command[1].lower() in ["groups", "للمجموعات"]:
        broadcast_mode = "groups"

    json_file = "id.json" if broadcast_mode == "users" else "group.json"

    
    if not os.path.exists(json_file):
        return await sent.edit_text(
            f"❌ **خطأ في الإذاعة**\n\nلم أتمكن من العثور على الملف `{json_file}`."
        )

    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            chats = [int(uid) for uid in data if str(uid).lstrip('-').isdigit()]
        else:
            return await sent.edit_text(
                f"❌ **خطأ في الإذاعة**\n\nالمحتوى داخل ملف `{json_file}` ليس بصيغة قائمة (list)."
            )
    
    except json.JSONDecodeError:
        return await sent.edit_text(
            f"❌ **خطأ في الإذاعة**\n\nملف `{json_file}` يحتوي على خطأ في صيغة JSON."
        )
    except Exception as e:
        return await sent.edit_text(f"❌ **خطأ في الإذاعة**\n\nفشل قراءة الملف: `{e}`")

    if not chats:
            return await sent.edit_text(
                f"⚠️ **إذاعة فارغة**\n\nملف `{json_file}` موجود ولكنه لا يحتوي على أي آيدي (ID) صالح."
            )

    
    text_content = msg.text or msg.caption or ""
    original_reply_markup = msg.reply_markup
    
    button_found = False
    new_keyboard = []
    lines_to_delete = []

    
    button_pattern = r"(.*?)\s-\s(https?://[^\s]+)"
    
    if text_content:
        lines = text_content.split('\n')
        
        
        for i, line in reversed(list(enumerate(lines))):
            line = line.strip()
            
            matches = re.findall(button_pattern, line)
            
            if matches:
                
                button_row = []
                for (button_text, button_url) in matches:
                    button_row.append(
                        InlineKeyboardButton(button_text.strip(), url=button_url.strip())
                    )
                
                if button_row:
                    new_keyboard.append(button_row)
                    lines_to_delete.append(i) 
            else:
                
                break
    
    final_reply_markup = original_reply_markup
    
    if new_keyboard:
        button_found = True
        

        text_content = "\n".join(
            [line for i, line in enumerate(lines) if i not in lines_to_delete]
        ).strip()
        

        new_keyboard.reverse()
        
        original_keyboard = []
        if original_reply_markup and original_reply_markup.inline_keyboard:
            original_keyboard = original_reply_markup.inline_keyboard
            

        final_keyboard = original_keyboard + new_keyboard
        final_reply_markup = InlineKeyboardMarkup(final_keyboard)
    



    broadcasting = True

    await msg.forward(app.logger)
    await (await app.send_message(
        chat_id=app.logger, 
        text=message.lang["gcast_log"].format(
            message.from_user.id,
            message.from_user.mention,
            message.text,
        ) + f"\n**الوجهة:** `{json_file}`"
    )).pin(disable_notification=False)
    await asyncio.sleep(5)

    for chat in chats:
        if not broadcasting:
            await sent.edit_text(message.lang["gcast_stopped"].format(count, ucount))
            break

        try:

            
            if button_found:

                if msg.photo:
                    await app.send_photo(chat, photo=msg.photo.file_id, caption=text_content, reply_markup=final_reply_markup)
                elif msg.video:
                    await app.send_video(chat, video=msg.video.file_id, caption=text_content, reply_markup=final_reply_markup)
                elif msg.audio:
                    await app.send_audio(chat, audio=msg.audio.file_id, caption=text_content, reply_markup=final_reply_markup)
                elif msg.animation:
                     await app.send_animation(chat, animation=msg.animation.file_id, caption=text_content, reply_markup=final_reply_markup)
                elif msg.document:
                    await app.send_document(chat, document=msg.document.file_id, caption=text_content, reply_markup=final_reply_markup)
                elif msg.voice:
                    await app.send_voice(chat, voice=msg.voice.file_id, caption=text_content, reply_markup=final_reply_markup)
                elif msg.sticker:

                    await app.send_sticker(chat, sticker=msg.sticker.file_id)

                    if not text_content: 
                        await app.send_message(chat, " ", reply_markup=final_reply_markup)
                else: 

                    await app.send_message(
                        chat,
                        text=text_content, 
                        reply_markup=final_reply_markup, 
                        disable_web_page_preview=True
                    )
            else:

                await msg.copy(chat, reply_markup=original_reply_markup)
            



            if broadcast_mode == "users":
                ucount += 1
            else:
                count += 1
            await asyncio.sleep(0.1)
            
        except errors.FloodWait as fw:
            await asyncio.sleep(fw.value + 30)
        except Exception as e:

            print(f"[Broadcast Error] Chat {chat}: {e}")
            continue

    broadcasting = False
    await sent.edit_text(message.lang["gcast_end"].format(count, ucount))



@app.on_message(filters.command(["stop_gcast", "stop_broadcast", "ايقاف الاذاعه", "ايقاف الاذاعة"], prefixes=["", "/", "!", "."]) & app.sudoers)
@lang.language()
async def _stop_gcast(_, message: types.Message):
    global broadcasting
    if not broadcasting:
        return await message.reply_text(message.lang["gcast_inactive"])

    broadcasting = False
    await (await app.send_message(
        chat_id=app.logger,
        text=message.lang["gcast_stop_log"].format(
            message.from_user.id,
            message.from_user.mention
        )
    )).pin(disable_notification=False)
    await message.reply_text(message.lang["gcast_stop"])
