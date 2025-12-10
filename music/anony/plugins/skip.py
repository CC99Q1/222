from pyrogram import filters, types, enums 
from anony import anon, app, db, lang
from anony.helpers.fsub import check_force_sub 


@app.on_message(
    filters.regex(r"^(تخطي|التالي)$")
    & (filters.group | filters.channel)
    & ~app.bl_users
)
@lang.language()
@check_force_sub  

async def _skip(_, m: types.Message):
    

    is_admin = False 
    

    if m.sender_chat:
        is_admin = True
   
    elif m.from_user:
       
        if m.from_user.id in app.sudoers:
            is_admin = True
        
        else:
            try:
                member = await _.get_chat_member(m.chat.id, m.from_user.id)
                if member.status in (enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER):
                    is_admin = True
            except Exception:
                is_admin = False

    
    if not is_admin:
        return await m.reply_text(m.lang["not_admin"]) 


    if not await db.get_call(m.chat.id):
        return await m.reply_text(m.lang["not_playing"])


    if m.from_user: 
        user = m.from_user.mention
    elif m.sender_chat:
        user = m.sender_chat.title
    else:
        user = "Anonymous Admin"
   

    await anon.play_next(m.chat.id)
    await m.reply_text(m.lang["play_skipped"].format(user))