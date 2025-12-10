import json
import os
from pyrogram import enums, filters, types
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from anony import app, config, db, lang 
from anony.helpers import buttons, utils
from anony.helpers.fsub import check_force_sub

ID_FILE = "id.json"
GROUP_ID_FILE = "group.json" 
OWNER_ID = config.OWNER_ID


def read_ids_from_json() -> list:
    if os.path.exists(ID_FILE):
        try:
            with open(ID_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    return []

async def save_id_to_json(user_id: int):
    data = read_ids_from_json()
    if user_id not in data:
        data.append(user_id)
    with open(ID_FILE, "w") as f:
        json.dump(data, f, indent=4)


def read_group_ids_from_json() -> list:

    if os.path.exists(GROUP_ID_FILE):
        try:
            with open(GROUP_ID_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    return []

async def save_group_id_to_json(chat_id: int):

    data = read_group_ids_from_json()
    if chat_id not in data:
        data.append(chat_id)
    with open(GROUP_ID_FILE, "w") as f:
        json.dump(data, f, indent=4)

async def remove_group_id_from_json(chat_id: int):

    data = read_group_ids_from_json()
    if chat_id in data:
        data.remove(chat_id)
    with open(GROUP_ID_FILE, "w") as f:
        json.dump(data, f, indent=4)


@app.on_message(filters.command(["start"]))
@lang.language()
@check_force_sub  
async def start(_, message: types.Message):
    
    if message.chat.type != enums.ChatType.PRIVATE:
        
        await message.reply_text(
            "أهلاً بك، أنا بوت تشغيل الموسيقى 🎵\n\nاضغط على الزر أدناه لبدء محادثة معي في الخاص.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(app.name, url=f"https://t.me/{app.me.username}?start=true")]]
            )
        )
        return
    
    if message.from_user.id in app.bl_users and message.from_user.id not in db.notified:
        return await message.reply_text(message.lang["bl_user_notify"])

    private = True 
    _text = (
        message.lang["start_pm"].format(message.from_user.first_name, app.name)
    )

    key = await buttons.start_key(message.lang, private)

    photo_file_id = None
    try:
        
        async for photo in app.get_chat_photos(app.me.id, limit=1):
            photo_file_id = photo.file_id
            break
    except Exception:
      
        photo_file_id = config.START_IMG

    if photo_file_id:
        await message.reply_photo(
            photo=photo_file_id,
            caption=_text,
            reply_markup=key,
            quote=not private,
            has_spoiler=True  
        )
    else:
        await message.reply_text(
            text=_text,
            reply_markup=key,
            quote=not private, 
            disable_web_page_preview=True,
        )

    if private: 
        user_id = message.from_user.id
        
        is_new_to_json = user_id not in read_ids_from_json()
        
        if is_new_to_json:
            await save_id_to_json(user_id)
            total_members_count = len(read_ids_from_json())

            user_name_full = message.from_user.first_name + (f" {message.from_user.last_name}" if message.from_user.last_name else "")
            user_mention = f"[{user_name_full}](tg://user?id={user_id})" 
            user_username = f"@{message.from_user.username}" if message.from_user.username else "لا يوجد"
            
            notification_text = (
                f"**👤 عضو جديد انضم!**\n"
                f"ـــــــــــــــــــــــــــــــــــــــــــــ\n"
                f"- **المنشن:** {user_mention}\n" 
                f"- **المعرّف:** {user_username}\n"
                f"- **الأيدي:** `{user_id}`"
            )
            
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton(f"العدد الكلي : {total_members_count}", callback_data="total_users_count")]]
            )
            
            try:
                if OWNER_ID:
                    await app.send_message(
                        chat_id=OWNER_ID, 
                        text=notification_text, 
                        reply_markup=keyboard,
                        parse_mode=enums.ParseMode.MARKDOWN 
                    )
            except Exception:
                pass
        
        if await db.is_user(user_id):
            return
            
        return await db.add_user(user_id)


@app.on_message(
    filters.regex(r"^(playmode|settings|الاعدادات|وضع التشغيل)(@w+)?$") 
    & filters.group 
    & ~app.bl_users
)
@lang.language()
@check_force_sub  
async def settings(_, message: types.Message):
    admin_only = await db.get_play_mode(message.chat.id)
    _language = await db.get_lang(message.chat.id)
    await message.reply_text(
        text=message.lang["start_settings"].format(message.chat.title),
        reply_markup=buttons.settings_markup(
            message.lang, admin_only, _language, message.chat.id
        ),
        quote=True,
    )


@app.on_chat_member_updated(group=7)
async def chat_member_update_handler(_, update: types.ChatMemberUpdated):
    
    user_concerned = None
    if update.new_chat_member and update.new_chat_member.user:
        user_concerned = update.new_chat_member.user
    elif update.old_chat_member and update.old_chat_member.user:
        user_concerned = update.old_chat_member.user

    
    if not user_concerned or user_concerned.id != app.id:
        return

    chat = update.chat
    
    
    if chat.type not in [enums.ChatType.SUPERGROUP, enums.ChatType.CHANNEL]:
        
        try:
            await chat.leave()
        except Exception:
            pass
        return


    old_status = update.old_chat_member.status if update.old_chat_member else None
    new_status = update.new_chat_member.status if update.new_chat_member else None 

    
    chat_type = "مجموعة"
    chat_type_name_link = "المجموعة" 
    if chat.type == enums.ChatType.CHANNEL:
        chat_type = "قناة"
        chat_type_name_link = "القناة"



    if new_status in [enums.ChatMemberStatus.MEMBER, enums.ChatMemberStatus.ADMINISTRATOR] and \
       (old_status in [enums.ChatMemberStatus.LEFT, enums.ChatMemberStatus.BANNED] or old_status is None):
        
        chat_id = chat.id
        
        if chat_id in read_group_ids_from_json():
            return 
        
        await save_group_id_to_json(chat_id)
        
        
        adder = update.from_user 
        adder_mention = "غير معروف"
        adder_username = "غير معروف"
        adder_id = "غير معروف"

        if adder:
            adder_name = adder.first_name + (f" {adder.last_name}" if adder.last_name else "")
            adder_mention = f"[{adder_name}](tg://user?id={adder.id})"
            adder_username = f"@{adder.username}" if adder.username else "لا يوجد"
            adder_id = f"`{adder.id}`"

        chat_link = "لا يوجد"
        chat_link_url = None 
        try:
            if chat.username:
                chat_link_url = f"https://t.me/{chat.username}"
            else:
                chat_link_url = await chat.export_invite_link()
            
            if chat_link_url:
                chat_link = f"[{chat.title}]({chat_link_url})"
        except Exception:
            pass  

        member_count = 0
        try:
            member_count = await app.get_chat_members_count(chat.id)
        except Exception:
            pass 

        notification_text = (
            f"**➕ تم تفعيل البوت في {chat_type} جديدة!**\n"
            f"ـــــــــــــــــــــــــــــــــــــــــــــ\n"
            f"**تمت الإضافة بواسطة:**\n"
            f"⇜ من「 {adder_mention} 」\n"
            f"⇜ يوزره : {adder_username}\n"
            f"⇜ ايديه: {adder_id}\n"
            f"ـــــــــــــــــــــــــــــــــــــــــــــ\n"
            f"**معلومات ال{chat_type}:**\n"
            f"⇜ اسم ال{chat_type} : {chat.title}\n"
            f"⇜ رابط ال{chat_type} : {chat_link}\n" 
            f"⇜ ايدي ال{chat_type} : `{chat.id}`\n"
            f"⇜ عدد اعضاء ال{chat_type}: {member_count}"
        )
        
        keyboard = None
        if chat_link_url: 
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton(f"🔗 رابط ال{chat_type_name_link}", url=chat_link_url)]]
            )
        
        try:
            if OWNER_ID:
                await app.send_message(
                    chat_id=OWNER_ID,
                    text=notification_text,
                    reply_markup=keyboard,
                    parse_mode=enums.ParseMode.MARKDOWN,
                    disable_web_page_preview=True 
                )
        except Exception:
            pass 


    elif (new_status in [enums.ChatMemberStatus.LEFT, enums.ChatMemberStatus.BANNED] or new_status is None) and \
         (old_status in [enums.ChatMemberStatus.MEMBER, enums.ChatMemberStatus.ADMINISTRATOR]):
        
        chat_id = chat.id

        if chat_id not in read_group_ids_from_json():
            return
            
        await remove_group_id_from_json(chat.id)
        total_chats_count = len(read_group_ids_from_json())

        
        kicker = update.from_user 
        kicker_mention = "غير معروف"
        kicker_username = "غير معروف"
        kicker_id = "غير معروف"

        if kicker:
            kicker_name = kicker.first_name + (f" {kicker.last_name}" if kicker.last_name else "")
            kicker_mention = f"[{kicker_name}](tg://user?id={kicker.id})"
            kicker_username = f"@{kicker.username}" if kicker.username else "لا يوجد"
            kicker_id = f"`{kicker.id}`"

        chat_link = "لا يوجد"
        chat_link_url = None
        try:
            if chat.username:
                chat_link_url = f"https://t.me/{chat.username}"
            
            if chat_link_url:
                chat_link = f"[{chat.title}]({chat_link_url})"
            elif chat.title:
                 chat_link = chat.title 
        except Exception:
            pass 

        notification_text = (
            f"**➖ قام أحد بإزالة البوت من {chat_type}!**\n"
            f"ـــــــــــــــــــــــــــــــــــــــــــــ\n"
            f"**تمت الإزالة بواسطة:**\n"
            f"⇜ من「 {kicker_mention} 」\n"
            f"⇜ يوزره : {kicker_username}\n"
            f"⇜ ايديه : {kicker_id}\n"
            f"ـــــــــــــــــــــــــــــــــــــــــــــ\n"
            f"**معلومات ال{chat_type}:**\n"
            f"⇜ اسم ال{chat_type} : {chat.title}\n"
            f"⇜ رابط ال{chat_type} : {chat_link}\n" 
            f"⇜ ايدي ال{chat_type}: `{chat.id}`\n"
            f"ـــــــــــــــــــــــــــــــــــــــــــــ\n"
            f"⇜ عدد المجموعات/القنوات الآن : {total_chats_count}\n"
            f"⇜ تم حذف ال{chat_type} من ملف التخزين"
        )
        
        try:
            if OWNER_ID:
                await app.send_message(
                    chat_id=OWNER_ID,
                    text=notification_text,
                    parse_mode=enums.ParseMode.MARKDOWN,
                    disable_web_page_preview=True
                )
        except Exception:
            pass