import math
import os
import urllib.request as urllib
from html import escape
import logging
import requests
from bs4 import BeautifulSoup
from cloudscraper import CloudScraper
from PIL import Image
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup, ParseMode,
                      TelegramError, Update, constants)
from telegram.ext import CallbackContext, CommandHandler, run_async, Updater, Handler, InlineQueryHandler, CallbackQueryHandler
from telegram.utils.helpers import mention_html
from misc import convert_gif
import telegram
import telegram.ext
from urllib.parse import quote as urlquote
from io import BytesIO

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
API_KEY = "1567235277:AAFk5Pql27cbeME2qatGLxZ8VO_zBne1YsM"
updater = telegram.ext.Updater(API_KEY)
dispatcher = updater.dispatcher
REDIS = ""
combot_stickers_url = "https://combot.org/telegram/stickers?q="
scraper = CloudScraper()

__help__  = """
‣ /stickers: دۆزینەوەی ستیکەرەکان بۆ واژەی دراوە لەسەر کەتەلۆگی لکێنەری کۆمبۆت 
‣ /create: وەڵام بدەوە بۆ ستیکەرێک بۆ زیادکردنی بۆ پاکەتەکەت.
‣ /delsticker: بۆ سڕینەوەی ستیکەرەکەت لە ڕیپڵەی بنوسە.
‣ /stickerid: لە ڕیپڵەی ستیکەر بنوسە بۆ بینینی ئایدی ستیکەرەکەت.
‣ /getsticker: لە ڕیپڵەی ستیکەر یان وێنە بنوسە بۆ وەرگرتنی فایڵی png.
‣ /addfsticker <ناو بنوسە>:یان لە ڕیپڵەی ستیکەرێک بنوسە بۆ زیاکردنی ستیکەر بۆ لیستی دڵخوازەکان.
‣ /myfsticker: بۆ بینینی لیستی دڵخوازەکانت.
‣ /removefsticke <ناوی ستیکەرەکەت>: یان لە ڕیپڵەی ستیکەرێکت بنوسە.
"""

def start(update: Update, context: CallbackContext):
    args = context.args
    bot = context.bot
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    first_name = update.effective_user.first_name
    update.effective_message.reply_text(__help__,
                                               reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="Start", url=f"t.me/{context.bot.username}",
                            ),
                        ],
                    ],
                ),
                                        
              )


        
def stickerid(update: Update, context: CallbackContext):
    msg = update.effective_message
    if msg.reply_to_message and msg.reply_to_message.sticker:
        update.effective_message.reply_text(
            "سلاو "
            + f"{mention_html(msg.from_user.id, msg.from_user.first_name)}"
            + ", ئەو ئایدی ستیکەرەی کە تۆ وەڵامت داوەتەوە ئەوەیە :\n <code>"
            + escape(msg.reply_to_message.sticker.file_id)
            + "</code>",
            parse_mode=ParseMode.HTML,
        )
    else:
        update.effective_message.reply_text(
            f"{mention_html(msg.from_user.id, msg.from_user.first_name)}"
            + ", تکایە لە ڕیپڵەی ستیکەرێک بنوسە",
            parse_mode=ParseMode.HTML,
        )

def get_cbs_data(query, page, user_id):
    # returns (text, buttons)
    text = scraper.get(
        f'{combot_stickers_url}{urlquote(query)}&page={page}').text
    soup = BeautifulSoup(text, 'lxml')
    div = soup.find('div', class_='page__container')
    packs = div.find_all('a', class_='sticker-pack__btn')
    titles = div.find_all('div', 'sticker-pack__title')
    has_prev_page = has_next_page = None
    highlighted_page = div.find('a', class_='pagination__link is-active')
    if highlighted_page is not None and user_id is not None:
        highlighted_page = highlighted_page.parent
        has_prev_page = highlighted_page.previous_sibling.previous_sibling is not None
        has_next_page = highlighted_page.next_sibling.next_sibling is not None
    buttons = []
    if has_prev_page:
        buttons.append(InlineKeyboardButton(
            text='⬅️', callback_data=f'cbs_{page - 1}_{user_id}'))
    if has_next_page:
        buttons.append(InlineKeyboardButton(
            text='➡️', callback_data=f'cbs_{page + 1}_{user_id}'))
    buttons = InlineKeyboardMarkup([buttons]) if buttons else None
    text = f'لکێنەرەکان بۆ <code>{escape(query)}</code>:\nPage: {page}'
    if packs and titles:
        for pack, title in zip(packs, titles):
            link = pack['href']
            text += f"\n• <a href='{link}'>{escape(title.get_text())}</a>"
    elif page == 1:
        text = 'هیچ ئەنجامێک نەدۆزرایەوە، ناوێکی جیاواز تاقی بکەوە'
    else:
        text += "\n\nسەرنج ڕاکێشە، لێرە هیچ شتێک نییە."
    return text, buttons


def cb_sticker(update: Update, context: CallbackContext):
    msg = update.effective_message
    query = ' '.join(msg.text.split()[1:])
    if not query:
        msg.reply_text("ناوێک نوسە بۆ گەڕان بەدوای ستیکەر.")
        return
    if len(query) > 50:
        msg.reply_text("دابینکردنی پرسیاری گەڕان لەژێر 50 نووسە")
        return
    if msg.from_user:
        user_id = msg.from_user.id
    else:
        user_id = None
    text, buttons = get_cbs_data(query, 1, user_id)
    msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=buttons)


def cbs_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    _, page, user_id = query.data.split('_', 2)
    if int(user_id) != query.from_user.id:
        query.answer('بۆتۆ نیە', cache_time=60 * 60)
        return
    search_query = query.message.text.split(
        '\n', 1)[0].split(maxsplit=2)[2][:-1]
    text, buttons = get_cbs_data(search_query, int(page), query.from_user.id)
    query.edit_message_text(
        text, parse_mode=ParseMode.HTML, reply_markup=buttons)
    query.answer()
    
    
    #new
def getsticker(update: Update, context: CallbackContext):
    bot = context.bot
    msg = update.effective_message
    chat_id = update.effective_chat.id
    if msg.reply_to_message and msg.reply_to_message.sticker:
        file_id = msg.reply_to_message.sticker.file_id
        new_file = bot.get_file(file_id)
        new_file.download("sticker.png")
        bot.send_document(chat_id, document=open("sticker.png", "rb"))
        os.remove("sticker.png")
    else:
        update.effective_message.reply_text(
            "تکایە وەڵامی ستیکەرێک بدەوە بۆ من بۆ بارکردنی PNG.",
        )

def getsticker(update, context):
    msg = update.effective_message
    chat_id = update.effective_chat.id
    if msg.reply_to_message and msg.reply_to_message.sticker:
        context.bot.sendChatAction(chat_id, "typing")
        update.effective_message.reply_text(
            f"{mention_html(msg.from_user.id, msg.from_user.first_name)}"
            + ", تکایە ئەو فایلە بپشکنە کە لە خوارەوە داوات کردووە."
            "\nتکایە ئەم تایبەتمەندیە بە ژیرانە بەکاربێنە!",
            parse_mode=ParseMode.HTML,
        )
        context.bot.sendChatAction(chat_id, "upload_document")
        file_id = msg.reply_to_message.sticker.file_id
        newFile = context.bot.get_file(file_id)
        newFile.download("sticker.png")
        context.bot.sendDocument(chat_id, document=open("sticker.png", "rb"))
        context.bot.sendChatAction(chat_id, "upload_photo")
        context.bot.send_photo(chat_id, photo=open("sticker.png", "rb"))
        

    else:
        context.bot.sendChatAction(chat_id, "typing")
        update.effective_message.reply_text(
            f"{mention_html(msg.from_user.id, msg.from_user.first_name)}"
            + ", تکایە وەڵامی نامەی لکێنەر بدەوە بۆ بەدەستهێنانی وێنەی لکێنەر",
            parse_mode=ParseMode.HTML,
        )
def kang(update: Update, context: CallbackContext):
    msg = update.effective_message
    user = update.effective_user
    args = context.args
    packnum = 0
    packname = "k" + str(user.id) + "_by_" + context.bot.username
    packname_found = 0
    max_stickers = 120
    while packname_found == 0:
        try:
            stickerset = context.bot.get_sticker_set(packname)
            if len(stickerset.stickers) >= max_stickers:
                packnum += 1
                packname = (
                    "k"
                    + str(packnum)
                    + "_"
                    + str(user.id)
                    + "_by_"
                    + context.bot.username
                )
            else:
                packname_found = 1
        except TelegramError as e:
            if e.message == "Stickerset_invalid":
                packname_found = 1
    kangsticker = "kangsticker.png"
    is_animated = False
    is_video = False
    is_gif = False
    file_id = ""

    if msg.reply_to_message:
        if msg.reply_to_message.sticker:
            if msg.reply_to_message.sticker.is_animated:
                is_animated = True
            elif msg.reply_to_message.sticker.is_video:
                is_video = True
            file_id = msg.reply_to_message.sticker.file_id

        elif msg.reply_to_message.photo:
            file_id = msg.reply_to_message.photo[-1].file_id
        elif msg.reply_to_message.document and not msg.reply_to_message.document.mime_type == "video/mp4":
            file_id = msg.reply_to_message.document.file_id
        elif msg.reply_to_message.animation:
            file_id = msg.reply_to_message.animation.file_id
            is_gif = True
        else:
            msg.reply_text("بەڵێ، ناتوانم ئەوە کۆ بکەمەوە.")

        kang_file = context.bot.get_file(file_id)
        if not is_animated and not (is_video or is_gif):
            kang_file.download("kangsticker.png")
        elif is_animated:
            kang_file.download("kangsticker.tgs")
        elif is_video and not is_gif:
            kang_file.download("kangsticker.webm")
        elif is_gif:
            kang_file.download("kang.mp4")
            convert_gif("kang.mp4")

        if args:
            sticker_emoji = str(args[0])
        elif msg.reply_to_message.sticker and msg.reply_to_message.sticker.emoji:
            sticker_emoji = msg.reply_to_message.sticker.emoji
        else:
            sticker_emoji = "🖤"

        if not is_animated and not (is_video or is_gif):
            try:
                im = Image.open(kangsticker)
                maxsize = (512, 512)
                if (im.width and im.height) < 512:
                    size1 = im.width
                    size2 = im.height
                    if im.width > im.height:
                        scale = 512 / size1
                        size1new = 512
                        size2new = size2 * scale
                    else:
                        scale = 512 / size2
                        size1new = size1 * scale
                        size2new = 512
                    size1new = math.floor(size1new)
                    size2new = math.floor(size2new)
                    sizenew = (size1new, size2new)
                    im = im.resize(sizenew)
                else:
                    im.thumbnail(maxsize)
                if not msg.reply_to_message.sticker:
                    im.save(kangsticker, "PNG")
                context.bot.add_sticker_to_set(
                    user_id=user.id,
                    name=packname,
                    png_sticker=open("kangsticker.png", "rb"),
                    emojis=sticker_emoji,
                )
                msg.reply_text(
                    f"ستیکەر بەسەرکەوتوویی زیادی کرد بۆ [ستیکەرەکەت](t.me/addstickers/{packname})"
                    + f"\nئیمۆجی: {sticker_emoji}",
                    parse_mode=ParseMode.MARKDOWN,
                )

            except OSError as e:
                msg.reply_text("من تەنها دەتوانم وێنەکانی دروستبکەم کە MB 8.")
                print(e)
                return

            except TelegramError as e:
                if e.message == "Stickerset_invalid":
                    makepack_internal(
                        update,
                        context,
                        msg,
                        user,
                        sticker_emoji,
                        packname,
                        packnum,
                        png_sticker=open("kangsticker.png", "rb"),
                    )
                elif e.message == "Sticker_png_dimensions":
                    im.save(kangsticker, "PNG")
                    context.bot.add_sticker_to_set(
                        user_id=user.id,
                        name=packname,
                        png_sticker=open("kangsticker.png", "rb"),
                        emojis=sticker_emoji,
                    )
                    msg.reply_text(
                        f"ستیکەر بەسەرکەوتوویی زیادی کرد بۆ [ستیکەرەکەکەت](t.me/addstickers/{packname})"
                        + f"\nئیمۆجی: {sticker_emoji}",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    
                    msg.reply_document(chat_id, file = "kangsticker.png" , force_document=True)
                elif e.message == "Invalid sticker emojis":
                    msg.reply_text("ئیمۆجی نادروستە.")
                elif e.message == "Stickers_too_much":
                    msg.reply_text("قەبارەی پاکەتی ماکس گەیشت. پەنجە بنێ بە F بۆ ڕێزگرتن.")
                elif e.message == "Internal Server Error: sticker set not found (500)":
                    msg.reply_text(
                        "ستیکەر بەسەرکەوتوویی زیادی کرد بۆ [pack](t.me/addstickers/%s)"
                        % packname
                        + "\n"
                        "ئیمۆجی:" + " " + sticker_emoji,
                        parse_mode=ParseMode.MARKDOWN,
                    )
                print(e)

        elif is_animated:
            packname = "tt" + str(user.id) + "_by_" + context.bot.username
            packname_found = 0
            max_stickers = 50
            while packname_found == 0:
                try:
                    stickerset = context.bot.get_sticker_set(packname)
                    if len(stickerset.stickers) >= max_stickers:
                        packnum += 1
                        packname = (
                            "tt"
                            + str(packnum)
                            + "_"
                            + str(user.id)
                            + "_by_"
                            + context.bot.username
                        )
                    else:
                        packname_found = 1
                except TelegramError as e:
                    if e.message == "Stickerset_invalid":
                        packname_found = 1
            try:
                context.bot.add_sticker_to_set(
                    user_id=user.id,
                    name=packname,
                    tgs_sticker=open("kangsticker.tgs", "rb"),
                    emojis=sticker_emoji,
                )
                msg.reply_text(
                    f"ستیکەر بەسەرکەوتوویی زیادی کرد بۆ [pack](t.me/addstickers/{packname})"
                    + f"\nئیمۆجی: {sticker_emoji}",
                    parse_mode=ParseMode.MARKDOWN,
                )
                msg.reply_document(chat_id, file = "kangsticker.tgs" , force_document=True)
            except TelegramError as e:
                if e.message == "Stickerset_invalid":
                    makepack_internal(
                        update,
                        context,
                        msg,
                        user,
                        sticker_emoji,
                        packname,
                        packnum,
                        tgs_sticker=open("kangsticker.tgs", "rb"),
                    )
                elif e.message == "Invalid sticker emojis":
                    msg.reply_text("ئیمۆجی نادروستە.")
                elif e.message == "Internal Server Error: sticker set not found (500)":
                    msg.reply_text(
                        "ستیکەر بەسەرکەوتوویی زیادی کرد بۆ [pack](t.me/addstickers/%s)"
                        % packname
                        + "\n"
                        "ئیمۆجی:" + " " + sticker_emoji,
                        parse_mode=ParseMode.MARKDOWN,
                    )
                print(e)

        elif is_video or is_gif:
            packname = "vv" + str(user.id) + "_by_" + context.bot.username
            packname_found = 0
            max_stickers = 120

            while packname_found == 0:
                try:
                    stickerset = context.bot.get_sticker_set(packname)
                    if len(stickerset.stickers) >= max_stickers:
                        packnum += 1
                        packname = (
                            "vv"
                            + str(packnum)
                            + "_"
                            + str(user.id)
                            +"_by_"
                            + context.bot.username
                        )

                    else:
                        packname_found = 1
                except TelegramError as e:
                    if e.message == "Stickerset_invalid":
                        packname_found = 1
                    
            try:
                context.bot.add_sticker_to_set(
                    user_id=user.id,
                    name=packname,
                    webm_sticker=open("kangsticker.webm", "rb"),
                    emojis=sticker_emoji,
                )
                msg.reply_text(
                    f"ستیکەر بەسەرکەوتوویی زیادی کرد بۆ [pack](t.me/addstickers/{packname})"
                    + f"\nئیمۆجی: {sticker_emoji}",
                    parse_mode=ParseMode.MARKDOWN
                )
                msg.reply_document(chat_id, file = "kangsticker.webm" , force_document=True)

            except TelegramError as e:
                if e.message == "Stickerset_invalid":
                    makepack_internal(
                        update,
                        context,
                        msg,
                        user,
                        sticker_emoji,
                        packname,
                        packnum,
                        webm_sticker=open("kangsticker.webm", "rb"),
                    )
                elif e.message == "Invalid sticker emojis":
                    msg.reply_text("ئیمۆجی نادروستە")
                elif e.message == "Internal Server Error: sticker set not found (500)":
                    msg.reply_text(
                        f"ستیکەر بەسەرکەوتوویی زیادی کرد بۆ [pack](t.me/addsticker/{packname})",
                        + "\n"
                        f"ئیمۆجی: {sticker_emoji}",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    msg.reply_document("kangsticker.webm" ,parse_mode=ParseMode.MARKDOWN,)

    elif args:
        try:
            try:
                urlemoji = msg.text.split(" ")
                png_sticker = urlemoji[1]
                sticker_emoji = urlemoji[2]
            except IndexError:
                sticker_emoji = "🖤"
            urllib.urlretrieve(png_sticker, kangsticker)
            im = Image.open(kangsticker)
            maxsize = (512, 512)
            if (im.width and im.height) < 512:
                size1 = im.width
                size2 = im.height
                if im.width > im.height:
                    scale = 512 / size1
                    size1new = 512
                    size2new = size2 * scale
                else:
                    scale = 512 / size2
                    size1new = size1 * scale
                    size2new = 512
                size1new = math.floor(size1new)
                size2new = math.floor(size2new)
                sizenew = (size1new, size2new)
                im = im.resize(sizenew)
            else:
                im.thumbnail(maxsize)
            im.save(kangsticker, "PNG")
            msg.reply_photo(photo=open("kangsticker.png", "rb"))
            context.bot.add_sticker_to_set(
                user_id=user.id,
                name=packname,
                png_sticker=open("kangsticker.png", "rb"),
                emojis=sticker_emoji,
            )
            msg.reply_text(
                f"ستیکەر بەسەرکەوتوویی زیادی کرد بۆ [pack](t.me/addstickers/{packname})"
                + f"\nئیمۆجی: {sticker_emoji}",
                parse_mode=ParseMode.MARKDOWN,
            )
        except OSError as e:
            msg.reply_text("من تەنها دەتوانم وێنەکانی دروستبکەم کە MB 8.")
            print(e)
            return
        except TelegramError as e:
            if e.message == "Stickerset_invalid":
                makepack_internal(
                    update,
                    context,
                    msg,
                    user,
                    sticker_emoji,
                    packname,
                    packnum,
                    png_sticker=open("kangsticker.png", "rb"),
                )
            elif e.message == "Sticker_png_dimensions":
                im.save(kangsticker, "PNG")
                context.bot.add_sticker_to_set(
                    user_id=user.id,
                    name=packname,
                    png_sticker=open("kangsticker.png", "rb"),
                    emojis=sticker_emoji,
                )
                msg.reply_text(
                    "ستیکەر بەسەرکەوتوویی زیادی کرد بۆ [pack](t.me/addstickers/%s)"
                    % packname
                    + "\n"
                    + "ئیمۆجی:"
                    + " "
                    + sticker_emoji,
                    parse_mode=ParseMode.MARKDOWN,
                )
                msg.reply_document("kangsticker.webm" ,parse_mode=ParseMode.MARKDOWN,)
            elif e.message == "Invalid sticker emojis":
                msg.reply_text("ئیمۆجی نادروستە.")
            elif e.message == "Stickers_too_much":
                msg.reply_text("بەستنەوەی ماکس گەیشت. پەنجە بنێ بە F بۆ ڕێزگرتن.")
            elif e.message == "Internal Server Error: sticker set not found : (500)":
                msg.reply_text(
                    "ستیکەر بەسەرکەوتوویی زیادی کرد بۆ [pack](t.me/addstickers/%s)"
                    % packname
                    + "\n"
                    "ئیمۆجی:" + " " + sticker_emoji,
                    parse_mode=ParseMode.MARKDOWN,
                )
            print(e)
    else:
        packs = "تکایە وەڵامی ستیکەرێک بدەوە، یان وێنە یان گیف بۆ ئەوەی کەنگ بکات!\nئۆه، هەرچۆنێک بێت لێرە پاکەتەکانتن:\n"
        if packnum > 0:
            firstpackname = "k" + str(user.id) + "_by_" + context.bot.username
            for i in range(0, packnum + 1):
                if i == 0:
                    packs += f"[pack](t.me/addstickers/{firstpackname})\n"
                else:
                    packs += f"[pack{i}](t.me/addstickers/{packname})\n"
        else:
            packs += f"[pack](t.me/addstickers/{packname})"
        msg.reply_text(packs, parse_mode=ParseMode.MARKDOWN)
    try:
        if os.path.isfile("kangsticker.png"):
            os.remove("kangsticker.png")
        elif os.path.isfile("kangsticker.tgs"):
            os.remove("kangsticker.tgs")
        elif os.path.isfile("kangsticker.webm"):
            os.remove("kangsticker.webm")
        elif os.path.isfile("kang.mp4"):
            os.remove("kang.mp4")
    except:
        pass


def makepack_internal(
    update,
    context,
    msg,
    user,
    emoji,
    packname,
    packnum,
    png_sticker=None,
    tgs_sticker=None,
    webm_sticker=None,
):
    name = user.first_name
    name = name[:50]
    try:
        extra_version = ""
        if packnum > 0:
            extra_version = " " + str(packnum)
        if png_sticker:
            success = context.bot.create_new_sticker_set(
                user.id,
                packname,
                f"{name}" + extra_version,
                png_sticker=png_sticker,
                emojis=emoji,
            )
        if tgs_sticker:
            success = context.bot.create_new_sticker_set(
                user.id,
                packname,
                f"{name}" + extra_version,
                tgs_sticker=tgs_sticker,
                emojis=emoji,
            )
        if webm_sticker:
            success = context.bot.create_new_sticker_set(
                user.id,
                packname,
                f"{name}" + extra_version,
                webm_sticker=webm_sticker,
                emojis=emoji,
            )

    except TelegramError as e:
        print(e)
        if e.message == "Sticker set name is already occupied":
            msg.reply_text(
                "پێچەکەت دەدۆزرێتەوە [here](t.me/addstickers/%s)" % packname,
                parse_mode=ParseMode.MARKDOWN,
            )
        elif e.message in ("Peer_id_invalid", "bot was blocked by the user"):
            msg.reply_text(
                "یەکەم جار پەیوەندیم پێوە بکە لە تایبەت.",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="Start", url=f"t.me/{context.bot.username}",
                            ),
                        ],
                    ],
                ),
            )
        elif e.message == "Internal Server Error: sticker set not found : (500)":
            msg.reply_text(
                "پاکەتی ستەیکەر سەرکەوتووانە دروست کراوە. وەربگرە [here](t.me/addstickers/%s)"
                % packname,
                parse_mode=ParseMode.MARKDOWN,
            )
        return

    if success:
        msg.reply_text(
            "پاکەتی ستەیکەر سەرکەوتووانە دروست کراوە. وەربگرە [here](t.me/addstickers/%s)"
            % packname,
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        msg.reply_text("سەرکەوتوو نەبوو لە دروستکردنی پاکەتی ستیکەر. لەوانەیە بەهۆی میجیک.")
#new 
def delsticker(update, context):
    msg = update.effective_message
    if msg.reply_to_message and msg.reply_to_message.sticker:
        file_id = msg.reply_to_message.sticker.file_id
        context.bot.delete_sticker_from_set(file_id)
        msg.reply_text(
            "سڕایەوە!"
        )
    else:
        update.effective_message.reply_text(
            "تکایە وەڵامی نامەی لکێنەر بدەوە بۆ سڕینەوەی لکێنەر"
        )

def add_fvrtsticker(update, context):
    bot = context.bot
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    args = context.args
    query = " ".join(args)
    if message.reply_to_message and message.reply_to_message.sticker:
        get_s_name = message.reply_to_message.sticker.set_name
        if not query:
            get_s_name_title = get_s_name
        else:
            get_s_name_title = query
        if get_s_name is None:
            message.reply_text(
                "ستیکەر نادروستە!"
            )
        sticker_url = f"https://t.me/addstickers/{get_s_name}"
        sticker_m = "<a href='{}'>{}</a>".format(sticker_url, get_s_name_title)
        check_pack = REDIS.hexists(
            f'fvrt_stickers2_{user.id}', get_s_name_title)
        if check_pack == False:
            REDIS.hset(f'fvrt_stickers2_{user.id}',
                       get_s_name_title, sticker_m)
            message.reply_text(
                f"<code>{sticker_m}</code> بە سەرکەوتوویی زیادکرا بۆ ناو لیستی پاکەتی ستیکەرە دڵخوازەکانت!",
                parse_mode=ParseMode.HTML
            )
        else:
            message.reply_text(
                f"<code>{sticker_m}</code> پێشتر لە لیستی پێچەکانی بەستەرە دڵخوازەکەتدا بوونی هەیە!",
                parse_mode=ParseMode.HTML
            )

    else:
        message.reply_text(
            'وەڵامی هەر لکێنەرێک بدەوە!'
        )

def list_fvrtsticker(update, context):
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    fvrt_stickers_list = REDIS.hvals(f'fvrt_stickers2_{user.id}')
    fvrt_stickers_list.sort()
    fvrt_stickers_list = "\n• ".join(fvrt_stickers_list)
    if fvrt_stickers_list:
        message.reply_text(
            "{} پاکەتەکانی ستەیکەر:\n• {}".format(user.first_name,
                                                        fvrt_stickers_list),
            parse_mode=ParseMode.HTML
        )
    else:
        message.reply_text(
            "هێشتا هیچ ستیکەرێکت زیاد نەکردووە."
        )
        
def remove_fvrtsticker(update, context):
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    args = context.args
    del_stick = " ".join(args)
    if not del_stick:
        message.reply_text(
            "تکایە ناوی پاکەتێکی ستەیکەری دڵخوازت بدە بۆ لابردنی لە لیستەکەت.")
        return
    del_check = REDIS.hexists(f'fvrt_stickers2_{user.id}', del_stick)
    if not del_check == False:
        REDIS.hdel(f'fvrt_stickers2_{user.id}', del_stick)
        message.reply_text(
            f"<code>{del_stick}</code> بەسەرکەوتوویی لە لیستەکەت سڕایەوە.",
            parse_mode=ParseMode.HTML
        )
    else:
        message.reply_text(
            f"<code>{del_stick}</code> لە لیستی پاکەتی ستەیکەرەکەتدا بوونی نییە.",
            parse_mode=ParseMode.HTML
        )
        
STICKERID_HANDLER = CommandHandler("stickerid", stickerid, run_async=True)
GETSTICKER_HANDLER = CommandHandler("getsticker", getsticker)
KANG_HANDLER = CommandHandler("create", kang, run_async=True)
STICKERS_HANDLER = CommandHandler("stickers", cb_sticker, run_async=True)
CBSCALLBACK_HANDLER = CallbackQueryHandler(cbs_callback, pattern='cbs_', run_async=True)
MY_FSTICKERS_HANDLER = CommandHandler("myfsticker", list_fvrtsticker, run_async=True)
REMOVE_FSTICKER_HANDLER = CommandHandler("removefsticker", remove_fvrtsticker, pass_args=True, run_async=True)
start_handler = CommandHandler("start", start, pass_args=True, run_async=True)
DEL_HANDLER = CommandHandler("delsticker", delsticker, run_async=True)
ADD_FSTICKER_HANDLER = CommandHandler("addfsticker", add_fvrtsticker, pass_args=True, run_async=True)

dispatcher.add_handler(ADD_FSTICKER_HANDLER)
dispatcher.add_handler(DEL_HANDLER)
dispatcher.add_handler(REMOVE_FSTICKER_HANDLER)
dispatcher.add_handler(STICKERS_HANDLER)
dispatcher.add_handler(STICKERID_HANDLER)
dispatcher.add_handler(GETSTICKER_HANDLER)
dispatcher.add_handler(KANG_HANDLER)
dispatcher.add_handler(start_handler)
dispatcher.add_handler(CBSCALLBACK_HANDLER)
dispatcher.add_handler(MY_FSTICKERS_HANDLER)
    
# start polling for updates from telegram
updater.start_polling()
# block until a signal is sent
updater.idle()
