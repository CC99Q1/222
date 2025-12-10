from pyrogram import filters, types, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
import asyncio
try:
    from anony import app, config
except ImportError:
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from anony import app, config


def get_main_text(user_id: int, user_first_name: str) -> str:
    user_mention_html = f'<a href="tg://user?id={user_id}">{user_first_name}</a>'
    return f"» مرحبا {user_mention_html}!\n\n» اتبع الازرار بالاسفل لمعرفة طريقة التشغيل ⚡</b>:"

def build_main_custom_keyboard(bot_username: str, owner_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("• اوامر التشغيل •", callback_data=f'custom_btn_1_{owner_id}')
        ],
        [
            InlineKeyboardButton("• اوامر الادمن •", callback_data=f'custom_btn_2_{owner_id}'),
            InlineKeyboardButton("• اوامر القناة •", callback_data=f'custom_btn_3_{owner_id}')
        ],
        [
            InlineKeyboardButton(
                " اضفني لمجموعتك ",
                url=f"https://t.me/{bot_username}?startgroup=true"
            )
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def build_back_custom_keyboard(owner_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🔙 رجوع", callback_data=f'custom_main_menu_{owner_id}')]
    ]
    return InlineKeyboardMarkup(keyboard)


# --- الكود الجديد: عند إضافة البوت لمجموعة جديدة ---
@app.on_message(filters.new_chat_members)
async def welcome_bot_to_group(_, message: types.Message):
    """
    يتم تنفيذ هذه الدالة تلقائياً عند إضافة عضو جديد للمجموعة.
    يتم التحقق مما إذا كان العضو الجديد هو البوت نفسه، وحينها يتم إرسال الأوامر.
    """
    try:
        bot = await app.get_me()
        
        for member in message.new_chat_members:
           
            if member.id == bot.id:

                owner_id = message.from_user.id
                owner_first_name = message.from_user.first_name
                
                main_text = get_main_text(owner_id, owner_first_name)
                
                await message.reply_text(
                    main_text,
                    reply_markup=build_main_custom_keyboard(bot.username, owner_id),
                    parse_mode=enums.ParseMode.HTML
                )
                return 
    except Exception as e:
        print(f"[ERROR] حدث خطأ في الترحيب عند الانضمام: {e}")
# ---------------------------------------------------


@app.on_message(filters.regex(r"^(الاوامر|buttons)(@\w+)?$") & filters.group)
async def show_custom_buttons_in_group(_, message: types.Message):
    try:
        bot_username = (await app.get_me()).username
    except Exception as e:
        print(f"[ERROR] لم يتمكن من جلب اسم مستخدم البوت: {e}")
        bot_username = "eunnbot" 

    owner_id = message.from_user.id
    owner_first_name = message.from_user.first_name
    main_text = get_main_text(owner_id, owner_first_name)

    await message.reply_text(
        main_text,
        reply_markup=build_main_custom_keyboard(bot_username, owner_id),
        quote=True,
        parse_mode=enums.ParseMode.HTML
    )


@app.on_callback_query(filters.regex(r"^custom_([a-zA-Z0-9_]+)_(\d+)$"))
async def custom_button_callback(_, query: types.CallbackQuery):
    clicker_id = query.from_user.id
    
    try:
        match = query.matches[0]
        action = match.group(1)
        owner_id = int(match.group(2))
    except (IndexError, TypeError):
        return await query.answer("حدث خطأ في بيانات الزر.", show_alert=True)

    if clicker_id != owner_id:
        return await query.answer("عذراً، هذه الأزرار خاصة بصاحب الأمر فقط.", show_alert=True)
    
    await query.answer() 

    if action == 'main_menu':
        bot_username = (await app.get_me()).username
        main_text = get_main_text(query.from_user.id, query.from_user.first_name)
        try:
            await query.edit_message_text(
                text=main_text,
                reply_markup=build_main_custom_keyboard(bot_username, owner_id),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception:
            pass 
        
    elif action == 'btn_1':
        try:
            await query.edit_message_text(
                text="""<b>● قائمــة اوامــر الـتشغـيـل و التحميل :
⋆┄─┄─┄─┄─┄─┄─┄─┄⋆

تشغيل + (اسم الاغنية  رابط الاغنية)
- لــ تـشـغـيل اغـنـيـة فـي الـمكـالـمـة الـصـوتـيـة

شغل فيديو  +  (اسم المقـطـع  رابط المقـطـع)
- لــ تـشـغـيل فيـديـو فـي الـمكـالـمـة المـرئيـة

فيد + الاسم
- لــ تحميل فيـديـو من اليوتيـوب        

يوت + الاسـم
- لـ تحميـل الاغانـي والمقـاطـع الصوتيـه مـن اليوتيـوب</b>""",
                reply_markup=build_back_custom_keyboard(owner_id),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception:
            pass
        
    elif action == 'btn_2':
        try:
            await query.edit_message_text(
                text="""<b>● قائمــة اوامــر الادمــن :
⋆┄─┄─┄─┄─┄─┄─┄─┄⋆

الاعدادات
- لـ عـرض إعـدادات اوضـاع التشغيـل

ايقاف  انهاء  اسكت
- لـ إيقـاف تـشغـيـل الـمـوسـيـقـى فـي المكـالمـة

وقف، توقف
- لـ إيقـاف تشغيـل الموسيـقـى فـي المكالمـة مـؤقتـاً

كمل ، كملي
- لـ إسـتـئـنـاف تـشغـيـل الـمـوسـيـقـى فـي المكـالمـة

تكرار + العدد
- لـ تكرار الاغنية لـ العدد المحدد


رفع ادمن / تنزيل ادمن
- لـ رفـع/تنزيـل ادمـن فـي البـوت

الادمنيه
- لـ عـرض قائمـة ادمنيـة البـوت</b>""",
                reply_markup=build_back_custom_keyboard(owner_id),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception:
            pass
        
    elif action == 'btn_3':
        try:
            await query.edit_message_text(
                text="""<b>● قائمــة اوامــر التشغيــل فـي القنــاة :
⋆┄─┄─┄─┄─┄─┄─┄─┄⋆
- ارفـع البـوت إشـراف في القنـاة و شغـل مباشـر
-  استخـدم الاوامــر بالاسفـل لـ التشغيـل
⋆┄─┄─┄─┄─┄─┄─┄─┄⋆

تشغيل + اسم الاغنية
- لــ تـشـغـيل اغـنـيـة فـي الـمكـالـمـة الـصـوتـيـة

شغل فيديو + اسم المقـطـع
- لــ تـشـغـيل فيـديـو فـي الـمكـالـمـة المـرئيـة

ايقاف / انهاء / اسكت / كافي
- لـ إيقـاف تـشغـيـل الـمـوسـيـقـى فـي المكـالمـة

وقف / توقف
- لـ إيقـاف تشغيـل الموسيـقـى فـي المكالمـة مـؤقتـاً

كمل / استئناف
- لـ إسـتـئـنـاف تـشغـيـل الـمـوسـيـقـى فـي المكـالمـة

تخطي
- لـ تخطـي الاغنيـة وتشغيـل الاغنيـة التاليـه
⋆┄─┄─┄─┄─┄─┄─┄─┄⋆

تقديم + عـدد الثـوانـي
- لـ تقديـم الاغنيـه لـ الامـام

رجوع + عـدد الثـوانـي
- لـ إرجـاع الاغنيـه لـ الخـلف</b>""",
                reply_markup=build_back_custom_keyboard(owner_id),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception:
            pass


@app.on_message(filters.regex(r"^(المطور|sudo)(@\w+)?$") & filters.group)
async def show_developer_info(_, message: types.Message):
    """
    يستجيب لكلمة "المطور" ويعرض معلومات المالك (SUDO) مع زر لمراسلته.
    """
    
    if not hasattr(config, 'OWNER_ID') or not config.OWNER_ID:
        return await message.reply_text("لم يتم تحديد `OWNER_ID` في ملف الكونفج.", quote=True)

    owner_id = config.OWNER_ID
    
    try:
        
        sudo_user = await app.get_users(owner_id) 
        
        
        sudo_chat = await app.get_chat(owner_id) 
        
       
        photo_file_id = None
        try:
            async for photo in app.get_chat_photos(owner_id, limit=1):
                photo_file_id = photo.file_id
                break
        except Exception:
            pass 

        
        name = sudo_user.first_name + (f" {sudo_user.last_name}" if sudo_user.last_name else "")
        name_clean = name.replace("<", "&lt;").replace(">", "&gt;") 
        
        username = f"@{sudo_user.username}" if sudo_user.username else "ماكو يوزر"
        user_id_code = f"<code>{sudo_user.id}</code>" 
        
        
        bio = sudo_chat.bio if sudo_chat.bio else "لا يوجد بايو" 
        bio_clean = bio.replace("<", "&lt;").replace(">", "&gt;")

        
        caption_text = (
            f"<b>✧ : NAME SUDO :</b> {name_clean}\n"
            f"<b>✧ : USERNAME SUDO :</b> {username}\n"
            f"<b>✧ : ID SUDO :</b> {user_id_code}\n"
            f"<b>✧ : BIO SUDO :</b> {bio_clean}"
        )

        
        developer_button = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text=f"{name}",       
                        user_id=owner_id      
                    )
                ]
            ]
        )

        if photo_file_id:
           
            await message.reply_photo(
                photo=photo_file_id,
                caption=caption_text,
                parse_mode=enums.ParseMode.HTML,
                quote=True,
                reply_markup=developer_button 
            )
        else:
            
            await message.reply_text(
                text=caption_text,
                parse_mode=enums.ParseMode.HTML,
                quote=True,
                disable_web_page_preview=True,
                reply_markup=developer_button 
            )

    except FloodWait as e:
        print(f"[FLOOD WAIT]: {e.x} seconds")
        await asyncio.sleep(e.x)
        await message.reply_text("حدث ضغط، يرجى المحاولة مرة أخرى بعد قليل.", quote=True)
    except Exception as e:
        print(f"[ERROR in المطور command]: {e}")
        await message.reply_text(
            f"حدث خطأ: <code>{e}</code>\n\nتأكد من أن <code>OWNER_ID</code> صحيح.",
            quote=True,
            parse_mode=enums.ParseMode.HTML
        )