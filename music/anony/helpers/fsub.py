import functools
from pyrogram import errors, types
from pyrogram.errors import exceptions
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from anony import app, config 



FSUB_ERROR_MSG = """
<b>• يجب عليك الاشتراك في قناة المطور أولا</b>
<b>•اشترك ثم أرسل الأمر مجدياً.</b>
"""

FSUB_DEFAULT_BUTTON_TEXT = "اضغط هنا للاشتراك"
FSUB_ADMIN_ERROR_MSG = "<b>خطأ إداري في الاشتراك الإجباري.\n\nلم أتمكن من فحص عضوية القناة. يرجى إبلاغ المطور.</b>"


print("="*50)
print("      [فحص الاشتراك الإجباري عند بدء التشغيل]      ")
if config.FORCE_SUB_CHANNEL:
    print(f"الحالة: مفعل ✅")
    print(f"القناة: {config.FORCE_SUB_CHANNEL}")
else:
    print("الحالة: معطل ❌")
    print("المتغير FORCE_SUB_CHANNEL غير موجود أو فارغ في ملف .env")
print("="*50)



if not hasattr(app, "force_sub_channel_title"):
    app.force_sub_channel_title = None
if not hasattr(app, "force_sub_generated_link"):
    app.force_sub_generated_link = None 

def check_force_sub(func):

    @functools.wraps(func)
    async def wrapper(client, message: types.Message, *args, **kwargs):
        
        
        if not config.FORCE_SUB_CHANNEL:
            return await func(client, message, *args, **kwargs)

       
        if not message.from_user:
            return await func(client, message, *args, **kwargs)


        user_id = message.from_user.id
        channel_input = config.FORCE_SUB_CHANNEL
        
        try:
            
            channel_id = int(channel_input)
        except ValueError:
            
            channel_id = channel_input

        
        if (hasattr(app, "sudo_users") and user_id in app.sudo_users) or (user_id == config.OWNER_ID):
            return await func(client, message, *args, **kwargs)

        
        if app.force_sub_channel_title is None or app.force_sub_generated_link is None:
            try:
                chat = await client.get_chat(channel_id) 
                app.force_sub_channel_title = chat.title
                
                
                if chat.username:
                    app.force_sub_generated_link = f"https://t.me/{chat.username}"
                else:
                    str_id = str(chat.id)
                    if str_id.startswith("-100"):
                        link_id = str_id[4:] 
                        app.force_sub_generated_link = f"https://t.me/c/{link_id}"
                    else:

                        raise Exception("Link generation failed for private chat.")
                
            except Exception as e:
                print(f"!!! خطأ فادح في توليد رابط الاشتراك الإجباري: {e}")

                await message.reply_text(FSUB_ADMIN_ERROR_MSG)
                return 


        try:

            member = await client.get_chat_member(chat_id=channel_id, user_id=user_id)
            if member.status in ("left", "kicked"):
                raise errors.UserNotParticipant

        except errors.UserNotParticipant:
            
            fsub_msg = FSUB_ERROR_MSG.format(channel=channel_input)
            
            button_text = app.force_sub_channel_title
            fsub_link = app.force_sub_generated_link
            
            markup = InlineKeyboardMarkup(
                [[InlineKeyboardButton(button_text, url=fsub_link)]]
            )
            
            await message.reply_text(fsub_msg, reply_markup=markup, disable_web_page_preview=True)
            return

        except (exceptions.BadRequest, exceptions.Forbidden, errors.PeerIdInvalid):
            
            print(f"خطأ في الاشتراك الإجباري: البوت ليس عضواً/مشرفاً في القناة '{channel_id}'.")
            await message.reply_text(FSUB_ADMIN_ERROR_MSG)
            return 
            
        except Exception as e:
           
            print(f"خطأ غير معروف في الاشتراك الإجباري للمستخدم {user_id}: {e}")
            return 

        
        return await func(client, message, *args, **kwargs)

    return wrapper