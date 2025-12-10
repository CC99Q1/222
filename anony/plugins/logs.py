import os
from pyrogram import filters, types
from anony import app, db, lang


@app.on_message(filters.command(["logs"]) & app.sudoers)
@lang.language()
async def _logs(_, m: types.Message):
    sent = await m.reply_text(m.lang["log_fetch"])
    if not os.path.exists("log.txt"):
        return await sent.edit_text(m.lang["log_not_found"])
    await sent.edit_media(
        media=types.InputMediaDocument(
            media="log.txt",
            caption=m.lang["log_sent"].format(app.name),
        )
    )


@app.on_message(filters.regex("^تفعيل السجل$") & app.sudoers)
@lang.language()
async def logger_on_hndlr(_, m: types.Message):

    await db.set_logger(True)
    await m.reply_text(m.lang["logger_on"])


@app.on_message(filters.regex("^تعطيل السجل$") & app.sudoers)
@lang.language()
async def logger_off_hndlr(_, m: types.Message):

    await db.set_logger(False)
    await m.reply_text(m.lang["logger_off"])
