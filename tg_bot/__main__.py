import importlib
import re
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import Unauthorized, BadRequest, TimedOut, NetworkError, ChatMigrated, TelegramError
from telegram.ext import CommandHandler, Filters, MessageHandler, CallbackQueryHandler
from telegram.ext.dispatcher import run_async, DispatcherHandlerStop
from telegram.utils.helpers import escape_markdown

from tg_bot import dispatcher, updater, TOKEN, WEBHOOK, OWNER_ID, DONATION_LINK, CERT_PATH, PORT, URL, LOGGER, \
    ALLOW_EXCL
# needed to dynamically load modules
# NOTE: Module order is not guaranteed, specify that in the config file!
from tg_bot.modules import ALL_MODULES
from tg_bot.modules.helper_funcs.chat_status import is_user_admin
from tg_bot.modules.helper_funcs.misc import paginate_modules

PM_START_TEXT = """
hoi {}, my name is {}! if you have any questions about how to use me please give me /help... 

im a group manager bot maintained by  [this person](tg://user?id={}).

My future updates will be put into This Channel - @MarieChechi & My Support Group @InFoTelGroup.

This is my [Deploy Code](https://heroku.com/deploy?template=https://github.com/TGExplore/Marie-2.0-English),
you can create clone same like me..

For more commands click /help...

**Keep in mind that any changes you DO do to the source have to be on github, as per the license.**

"""

HELP_STRINGS = """

Hello! my name *{}*.

*Main* available commands:
 - /start: Start the bot...
 - /help: help....
 - /donate: To find out more about donating!
 - /settings:
   - in PM: To find out what SETTINGS you have set....
   - in a group:

{}
And the following:
""".format(dispatcher.bot.first_name, "" if not ALLOW_EXCL else "\nAll of the following commands  / or ! can  be used...\n")

DONATE_STRING = """Heya, glad to hear you want to donate!
It took lots of work for [my creator](t.me/SonOfLars) to get me to where I am now, and every donation helps \
motivate him to make me even better. All the donation money will go to a better VPS to host me, and/or beer \
(see his bio!). He's just a poor student, so every little helps!
There are two ways of paying him; [PayPal](paypal.me/PaulSonOfLars), or [Monzo](monzo.me/paulnionvestergaardlarsen)."""

IMPORTED = {}
MIGRATEABLE = []
HELPABLE = {}
STATS = []
USER_INFO = []
DATA_IMPORT = []
DATA_EXPORT = []

CHAT_SETTINGS = {}
USER_SETTINGS = {}

for module_name in ALL_MODULES:
    imported_module = importlib.import_module("tg_bot.modules." + module_name)
    if not hasattr(imported_module, "__mod_name__"):
        imported_module.__mod_name__ = imported_module.__name__

    if not imported_module.__mod_name__.lower() in IMPORTED:
        IMPORTED[imported_module.__mod_name__.lower()] = imported_module
    else:
        raise Exception("Can't have two modules with the same name! Please change one")

    if hasattr(imported_module, "__help__") and imported_module.__help__:
        HELPABLE[imported_module.__mod_name__.lower()] = imported_module

    # Chats to migrate on chat_migrated events
    if hasattr(imported_module, "__migrate__"):
        MIGRATEABLE.append(imported_module)

    if hasattr(imported_module, "__stats__"):
        STATS.append(imported_module)

    if hasattr(imported_module, "__user_info__"):
        USER_INFO.append(imported_module)

    if hasattr(imported_module, "__import_data__"):
        DATA_IMPORT.append(imported_module)

    if hasattr(imported_module, "__export_data__"):
        DATA_EXPORT.append(imported_module)

    if hasattr(imported_module, "__chat_settings__"):
        CHAT_SETTINGS[imported_module.__mod_name__.lower()] = imported_module

    if hasattr(imported_module, "__user_settings__"):
        USER_SETTINGS[imported_module.__mod_name__.lower()] = imported_module


# do not async
def send_help(chat_id, text, keyboard=None):
    if not keyboard:
        keyboard = InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help"))
    dispatcher.bot.send_message(chat_id=chat_id,
                                text=text,
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=keyboard)


@run_async
def test(bot: Bot, update: Update):
    # pprint(eval(str(update)))
    # update.effective_message.reply_text("Hola tester! _I_ *have* `markdown`", parse_mode=ParseMode.MARKDOWN)
    update.effective_message.reply_text("This person edited a message")
    print(update.effective_message)


@run_async
def start(bot: Bot, update: Update, args: List[str]):
    if update.effective_chat.type == "private":
        if len(args) >= 1:
            if args[0].lower() == "help":
                send_help(update.effective_chat.id, HELP_STRINGS)

            elif args[0].lower().startswith("stngs_"):
                match = re.match("stngs_(.*)", args[0].lower())
                chat = dispatcher.bot.getChat(match.group(1))

                if is_user_admin(chat, update.effective_user.id):
                    send_settings(match.group(1), update.effective_user.id, False)
                else:
                    send_settings(match.group(1), update.effective_user.id, True)

            elif args[0][1:].isdigit() and "rules" in IMPORTED:
                IMPORTED["rules"].send_rules(update, args[0], from_pm=True)

        else:
            first_name = update.effective_user.first_name
            update.effective_message.reply_text(
                PM_START_TEXT.format(escape_markdown(first_name), escape_markdown(bot.first_name), OWNER_ID),
                parse_mode=ParseMode.MARKDOWN)
    else:
        update.effective_message.reply_text("waked up😏😏😏")


# for test purposes
def error_callback(bot, update, error):
    try:
        raise error
    except Unauthorized:
        print("no nono1")
        print(error)
        # remove update.message.chat_id from conversation list
    except BadRequest:
        print("no nono2")
        print("BadRequest caught")
        print(error)

        # handle malformed requests - read more below!
    except TimedOut:
        print("no nono3")
        # handle slow connection problems
    except NetworkError:
        print("no nono4")
        # handle other connection problems
    except ChatMigrated as err:
        print("no nono5")
        print(err)
        # the chat_id of a group has changed, use e.new_chat_id instead
    except TelegramError:
        print(error)
        # handle all other telegram related errors


@run_async
def help_button(bot: Bot, update: Update):
    query = update.callback_query
    mod_match = re.match(r"help_module\((.+?)\)", query.data)
    prev_match = re.match(r"help_prev\((.+?)\)", query.data)
    next_match = re.match(r"help_next\((.+?)\)", query.data)
    back_match = re.match(r"help_back", query.data)
    try:
        if mod_match:
            module = mod_match.group(1)
            text = "Here is the help for the *{}* module:\n".format(HELPABLE[module].__mod_name__) \
                   + HELPABLE[module].__help__
            query.message.reply_text(text=text,
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(
                                         [[InlineKeyboardButton(text="Back", callback_data="help_back")]]))

        elif prev_match:
            curr_page = int(prev_match.group(1))
            query.message.reply_text(HELP_STRINGS,
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(
                                         paginate_modules(curr_page - 1, HELPABLE, "help")))

        elif next_match:
            next_page = int(next_match.group(1))
            query.message.reply_text(HELP_STRINGS,
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(
                                         paginate_modules(next_page + 1, HELPABLE, "help")))

        elif back_match:
            query.message.reply_text(text=HELP_STRINGS,
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help")))

        # ensure no spinny white circle
        bot.answer_callback_query(query.id)
        query.message.delete()
    except BadRequest as excp:
        if excp.message == "Message is not modified":
            pass
        elif excp.message == "Query_id_invalid":
            pass
        elif excp.message == "Message can't be deleted":
            pass
        else:
            LOGGER.exception("Exception in help buttons. %s", str(query.data))


@run_async
def get_help(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    args = update.effective_message.text.split(None, 1)

    # ONLY send help in PM
    if chat.type != chat.PRIVATE:

        update.effective_message.reply_text("Contact me in PM to get the list of possible commands.",
                                            reply_markup=InlineKeyboardMarkup(
                                                [[InlineKeyboardButton(text="Help",
                                                                       url="t.me/{}?start=help".format(
                                                                           bot.username))]]))
        return

    elif len(args) >= 2 and any(args[1].lower() == x for x in HELPABLE):
        module = args[1].lower()
        text = "Here is the available help for the *{}* module:\n".format(HELPABLE[module].__mod_name__) \
               + HELPABLE[module].__help__
        send_help(chat.id, text, InlineKeyboardMarkup([[InlineKeyboardButton(text="Back", callback_data="help_back")]]))

    else:
        send_help(chat.id, HELP_STRINGS)


def send_settings(chat_id, user_id, user=False):
    if user:
        if USER_SETTINGS:
            settings = "\n\n".join(
                "*{}*:\n{}".format(mod.__mod_name__, mod.__user_settings__(user_id)) for mod in USER_SETTINGS.values())
            dispatcher.bot.send_message(user_id, "These are your current settings:" + "\n\n" + settings,
                                        parse_mode=ParseMode.MARKDOWN)

        else:
            dispatcher.bot.send_message(user_id, "Seems like there aren't any user specific settings available :'(",
                                        parse_mode=ParseMode.MARKDOWN)

    else:
        if CHAT_SETTINGS:
            chat_name = dispatcher.bot.getChat(chat_id).title
            dispatcher.bot.send_message(user_id,
                                        text="Which module would you like to check {}'s settings for?".format(
                                            chat_name),
                                        reply_markup=InlineKeyboardMarkup(
                                            paginate_modules(0, CHAT_SETTINGS, "stngs", chat=chat_id)))
        else:
            dispatcher.bot.send_message(user_id, "Seems like there aren't any chat settings available :'(\nSend this "
                                                 "in a group chat you're admin in to find its current settings!",
                                        parse_mode=ParseMode.MARKDOWN)


@run_async
def settings_button(bot: Bot, update: Update):
    query = update.callback_query
    user = update.effective_user
    mod_match = re.match(r"stngs_module\((.+?),(.+?)\)", query.data)
    prev_match = re.match(r"stngs_prev\((.+?),(.+?)\)", query.data)
    next_match = re.match(r"stngs_next\((.+?),(.+?)\)", query.data)
    back_match = re.match(r"stngs_back\((.+?)\)", query.data)
    try:
        if mod_match:
            chat_id = mod_match.group(1)
            module = mod_match.group(2)
            chat = bot.get_chat(chat_id)
            text = "*{}* has the following settings for the *{}* module:\n\n".format(escape_markdown(chat.title),
                                                                                     CHAT_SETTINGS[module].__mod_name__) + \
                   CHAT_SETTINGS[module].__chat_settings__(chat_id, user.id)
            query.message.reply_text(text=text,
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(
                                         [[InlineKeyboardButton(text="Back",
                                                                callback_data="stngs_back({})".format(chat_id))]]))

        elif prev_match:
            chat_id = prev_match.group(1)
            curr_page = int(prev_match.group(2))
            chat = bot.get_chat(chat_id)
            query.message.reply_text("Hi there! There are quite a few settings for {} - go ahead and pick what "
                                     "you're interested in.".format(chat.title),
                                     reply_markup=InlineKeyboardMarkup(
                                         paginate_modules(curr_page - 1, CHAT_SETTINGS, "stngs",
                                                          chat=chat_id)))

        elif next_match:
            chat_id = next_match.group(1)
            next_page = int(next_match.group(2))
            chat = bot.get_chat(chat_id)
            query.message.reply_text("Hi there! There are quite a few settings for {} - go ahead and pick what "
                                     "you're interested in.".format(chat.title),
                                     reply_markup=InlineKeyboardMarkup(
                                         paginate_modules(next_page + 1, CHAT_SETTINGS, "stngs",
                                                          chat=chat_id)))

        elif back_match:
            chat_id = back_match.group(1)
            chat = bot.get_chat(chat_id)
            query.message.reply_text(text="Hi there! There are quite a few settings for {} - go ahead and pick what "
                                          "you're interested in.".format(escape_markdown(chat.title)),
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(paginate_modules(0, CHAT_SETTINGS, "stngs",
                                                                                        chat=chat_id)))

        # ensure no spinny white circle
        bot.answer_callback_query(query.id)
        query.message.delete()
    except BadRequest as excp:
        if excp.message == "Message is not modified":
            pass
        elif excp.message == "Query_id_invalid":
            pass
        elif excp.message == "Message can't be deleted":
            pass
        else:
            LOGGER.exception("Exception in settings buttons. %s", str(query.data))


@run_async
def get_settings(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    args = msg.text.split(None, 1)

    # ONLY send settings in PM
    if chat.type != chat.PRIVATE:
        if is_user_admin(chat, user.id):
            text = "Click here to get this chat's settings, as well as yours."
            msg.reply_text(text,
                           reply_markup=InlineKeyboardMarkup(
                               [[InlineKeyboardButton(text="Settings",
                                                      url="t.me/{}?start=stngs_{}".format(
                                                          bot.username, chat.id))]]))
        else:
            text = "Click here to check your settings."

    else:
        send_settings(chat.id, user.id, True)


@run_async
def donate(bot: Bot, update: Update):
    user = update.effective_message.from_user
    chat = update.effective_chat  # type: Optional[Chat]

    if chat.type == "private":
        update.effective_message.reply_text(DONATE_STRING, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

        if OWNER_ID != 254318997 and DONATION_LINK:
            update.effective_message.reply_text("You can also donate to the person currently running me "
                                                "[here]({})".format(DONATION_LINK),
                                                parse_mode=ParseMode.MARKDOWN)

    else:
        try:
            bot.send_message(user.id, DONATE_STRING, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

            update.effective_message.reply_text("I've PM'ed you about donating to my creator!")
        except Unauthorized:
            update.effective_message.reply_text("Contact me in PM first to get donation information.")


def migrate_chats(bot: Bot, update: Update):
    msg = update.effective_message  # type: Optional[Message]
    if msg.migrate_to_chat_id:
        old_chat = update.effective_chat.id
        new_chat = msg.migrate_to_chat_id
    elif msg.migrate_from_chat_id:
        old_chat = msg.migrate_from_chat_id
        new_chat = update.effective_chat.id
    else:
        return

    LOGGER.info("Migrating from %s, to %s", str(old_chat), str(new_chat))
    for mod in MIGRATEABLE:
        mod.__migrate__(old_chat, new_chat)

    LOGGER.info("Successfully migrated!")
    raise DispatcherHandlerStop


def main():
    test_handler = CommandHandler("test", test)
    start_handler = CommandHandler("start", start, pass_args=True)

    help_handler = CommandHandler("help", get_help)
    help_callback_handler = CallbackQueryHandler(help_button, pattern=r"help_")

    settings_handler = CommandHandler("settings", get_settings)
    settings_callback_handler = CallbackQueryHandler(settings_button, pattern=r"stngs_")

    donate_handler = CommandHandler("donate", donate)
    migrate_handler = MessageHandler(Filters.status_update.migrate, migrate_chats)

    # dispatcher.add_handler(test_handler)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(settings_handler)
    dispatcher.add_handler(help_callback_handler)
    dispatcher.add_handler(settings_callback_handler)
    dispatcher.add_handler(migrate_handler)
    dispatcher.add_handler(donate_handler)

    # dispatcher.add_error_handler(error_callback)

    if WEBHOOK:
        LOGGER.info("Using webhooks.")
        updater.start_webhook(listen="0.0.0.0",
                              port=PORT,
                              url_path=TOKEN)

        if CERT_PATH:
            updater.bot.set_webhook(url=URL + TOKEN,
                                    certificate=open(CERT_PATH, 'rb'))
        else:
            updater.bot.set_webhook(url=URL + TOKEN)

    else:
        LOGGER.info("Using long polling.")
        updater.start_polling(timeout=15, read_latency=4)

    updater.idle()


if __name__ == '__main__':
    LOGGER.info("Successfully loaded modules: " + str(ALL_MODULES))
    main()

  
import requests
import DeadlyBot.modules.hentai as hemtai
from PIL import Image
import os

from telegram import Message, Chat, Update, Bot, MessageEntity
from telegram import ParseMode
from telegram.ext import CommandHandler, run_async

from DeadlyBot import dispatcher, updater


def is_user_in_chat(chat: Chat, user_id: int) -> bool:
    member = chat.get_member(user_id)
    return member.status not in ("left", "kicked")


@run_async
def neko(update, context):
    msg = update.effective_message
    target = "neko"
    msg.reply_photo(nekos.img(target))


@run_async
def feet(update, context):
    msg = update.effective_message
    target = "feet"
    msg.reply_photo(nekos.img(target))


@run_async
def yuri(update, context):
    msg = update.effective_message
    target = "yuri"
    msg.reply_photo(nekos.img(target))


@run_async
def trap(update, context):
    msg = update.effective_message
    target = "trap"
    msg.reply_photo(nekos.img(target))


@run_async
def futanari(update, context):
    msg = update.effective_message
    target = "futanari"
    msg.reply_photo(nekos.img(target))


@run_async
def hololewd(update, context):
    msg = update.effective_message
    target = "hololewd"
    msg.reply_photo(nekos.img(target))


@run_async
def lewdkemo(update, context):
    msg = update.effective_message
    target = "lewdkemo"
    msg.reply_photo(nekos.img(target))


@run_async
def sologif(update, context):
    msg = update.effective_message
    target = "solog"
    msg.reply_video(nekos.img(target))


@run_async
def feetgif(update, context):
    msg = update.effective_message
    target = "feetg"
    msg.reply_video(nekos.img(target))


@run_async
def cumgif(update, context):
    msg = update.effective_message
    target = "cum"
    msg.reply_video(nekos.img(target))


@run_async
def erokemo(update, context):
    msg = update.effective_message
    target = "erokemo"
    msg.reply_photo(nekos.img(target))


@run_async
def lesbian(update, context):
    msg = update.effective_message
    target = "les"
    msg.reply_video(nekos.img(target))


@run_async
def wallpaper(update, context):
    msg = update.effective_message
    target = "wallpaper"
    msg.reply_photo(nekos.img(target))


@run_async
def lewdk(update, context):
    msg = update.effective_message
    target = "lewdk"
    msg.reply_photo(nekos.img(target))


@run_async
def ngif(update, context):
    msg = update.effective_message
    target = "ngif"
    msg.reply_video(nekos.img(target))


@run_async
def tickle(update, context):
    msg = update.effective_message
    target = "tickle"
    msg.reply_video(nekos.img(target))


@run_async
def lewd(update, context):
    msg = update.effective_message
    target = "lewd"
    msg.reply_photo(nekos.img(target))


@run_async
def feed(update, context):
    msg = update.effective_message
    target = "feed"
    msg.reply_video(nekos.img(target))


@run_async
def eroyuri(update, context):
    msg = update.effective_message
    target = "eroyuri"
    msg.reply_photo(nekos.img(target))


@run_async
def eron(update, context):
    msg = update.effective_message
    target = "eron"
    msg.reply_photo(nekos.img(target))


@run_async
def cum(update, context):
    msg = update.effective_message
    target = "cum_jpg"
    msg.reply_photo(nekos.img(target))


@run_async
def bjgif(update, context):
    msg = update.effective_message
    target = "bj"
    msg.reply_video(nekos.img(target))


@run_async
def bj(update, context):
    msg = update.effective_message
    target = "blowjob"
    msg.reply_photo(nekos.img(target))


@run_async
def nekonsfw(update, context):
    msg = update.effective_message
    target = "nsfw_neko_gif"
    msg.reply_video(nekos.img(target))


@run_async
def solo(update, context):
    msg = update.effective_message
    target = "solo"
    msg.reply_photo(nekos.img(target))


@run_async
def kemonomimi(update, context):
    msg = update.effective_message
    target = "kemonomimi"
    msg.reply_photo(nekos.img(target))


@run_async
def avatarlewd(update, context):
    msg = update.effective_message
    target = "nsfw_avatar"
    with open("temp.png", "wb") as f:
        f.write(requests.get(nekos.img(target)).content)
    img = Image.open("temp.png")
    img.save("temp.webp", "webp")
    msg.reply_document(open("temp.webp", "rb"))
    os.remove("temp.webp")


@run_async
def gasm(update, context):
    msg = update.effective_message
    target = "gasm"
    with open("temp.png", "wb") as f:
        f.write(requests.get(nekos.img(target)).content)
    img = Image.open("temp.png")
    img.save("temp.webp", "webp")
    msg.reply_document(open("temp.webp", "rb"))
    os.remove("temp.webp")


@run_async
def poke(update, context):
    msg = update.effective_message
    target = "poke"
    msg.reply_video(nekos.img(target))


@run_async
def anal(update, context):
    msg = update.effective_message
    target = "anal"
    msg.reply_video(nekos.img(target))


@run_async
def hentai(update, context):
    msg = update.effective_message
    target = "hentai"
    msg.reply_photo(nekos.img(target))


@run_async
def avatar(update, context):
    msg = update.effective_message
    target = "nsfw_avatar"
    with open("temp.png", "wb") as f:
        f.write(requests.get(nekos.img(target)).content)
    img = Image.open("temp.png")
    img.save("temp.webp", "webp")
    msg.reply_document(open("temp.webp", "rb"))
    os.remove("temp.webp")


@run_async
def erofeet(update, context):
    msg = update.effective_message
    target = "erofeet"
    msg.reply_photo(nekos.img(target))


@run_async
def holo(update, context):
    msg = update.effective_message
    target = "holo"
    msg.reply_photo(nekos.img(target))


# def keta(update, context):
#     msg = update.effective_message
#     target = 'keta'
#     if not target:
#         msg.reply_text("No URL was received from the API!")
#         return
#     msg.reply_photo(nekos.img(target))


@run_async
def pussygif(update, context):
    msg = update.effective_message
    target = "pussy"
    msg.reply_video(nekos.img(target))


@run_async
def tits(update, context):
    msg = update.effective_message
    target = "tits"
    msg.reply_photo(nekos.img(target))


@run_async
def holoero(update, context):
    msg = update.effective_message
    target = "holoero"
    msg.reply_photo(nekos.img(target))


@run_async
def pussy(update, context):
    msg = update.effective_message
    target = "pussy_jpg"
    msg.reply_photo(nekos.img(target))


@run_async
def hentaigif(update, context):
    msg = update.effective_message
    target = "random_hentai_gif"
    msg.reply_video(nekos.img(target))


@run_async
def classic(update, context):
    msg = update.effective_message
    target = "classic"
    msg.reply_video(nekos.img(target))


@run_async
def kuni(update, context):
    msg = update.effective_message
    target = "kuni"
    msg.reply_video(nekos.img(target))


@run_async
def waifu(update, context):
    msg = update.effective_message
    target = "waifu"
    with open("temp.png", "wb") as f:
        f.write(requests.get(nekos.img(target)).content)
    img = Image.open("temp.png")
    img.save("temp.webp", "webp")
    msg.reply_document(open("temp.webp", "rb"))
    os.remove("temp.webp")


@run_async
def kiss(update, context):
    msg = update.effective_message
    target = "kiss"
    msg.reply_video(nekos.img(target))


@run_async
def femdom(update, context):
    msg = update.effective_message
    target = "femdom"
    msg.reply_photo(nekos.img(target))


@run_async
def cuddle(update, context):
    msg = update.effective_message
    target = "cuddle"
    msg.reply_video(nekos.img(target))


@run_async
def erok(update, context):
    msg = update.effective_message
    target = "erok"
    msg.reply_photo(nekos.img(target))


@run_async
def foxgirl(update, context):
    msg = update.effective_message
    target = "fox_girl"
    msg.reply_photo(nekos.img(target))


@run_async
def titsgif(update, context):
    msg = update.effective_message
    target = "boobs"
    msg.reply_video(nekos.img(target))


@run_async
def ero(update, context):
    msg = update.effective_message
    target = "ero"
    msg.reply_photo(nekos.img(target))


@run_async
def smug(update, context):
    msg = update.effective_message
    target = "smug"
    msg.reply_video(nekos.img(target))


@run_async
def baka(update, context):
    msg = update.effective_message
    target = "baka"
    msg.reply_video(nekos.img(target))


@run_async
def dva(update, context):
    msg = update.effective_message
    nsfw = requests.get("https://api.computerfreaker.cf/v1/dva").json()
    url = nsfw.get("url")
    # do shit with url if you want to
    if not url:
        msg.reply_text("No URL was received from the API!")
        return
    msg.reply_photo(url)

__mod_name__ = "Lewd"

__help__ = """
 - /neko: Sends Random SFW Neko source Images.
 - /feet: Sends Random Anime Feet Images.
 - /yuri: Sends Random Yuri source Images.
 - /trap: Sends Random Trap source Images.
 - /futanari: Sends Random Futanari source Images.
 - /hololewd: Sends Random Holo Lewds.
 - /lewdkemo: Sends Random Kemo Lewds.
 - /sologif: Sends Random Solo GIFs.
 - /cumgif: Sends Random Cum GIFs.
 - /erokemo: Sends Random Ero-Kemo Images.
 - /lesbian: Sends Random Les Source Images.
 - /wallpaper: Sends Random Wallpapers.
 - /lewdk: Sends Random Kitsune Lewds.
 - /ngif: Sends Random Neko GIFs.
 - /tickle: Sends Random Tickle GIFs.
 - /lewd: Sends Random Lewds.
 - /feed: Sends Random Feeding GIFs.
 - /eroyuri: Sends Random Ero-Yuri source Images.
 - /eron: Sends Random Ero-Neko source Images.
 - /cum: Sends Random Cum Images.
 - /bjgif: Sends Random Blow Job GIFs.
 - /bj: Sends Random Blow Job source Images.
 - /nekonsfw: Sends Random NSFW Neko source Images.
 - /solo: Sends Random NSFW Neko GIFs.
 - /kemonomimi: Sends Random KemonoMimi source Images.
 - /avatarlewd: Sends Random Avater Lewd Stickers.
 - /gasm: Sends Random Orgasm Stickers.
 - /poke: Sends Random Poke GIFs.
 - /anal: Sends Random Anal GIFs.
 - /hentai: Sends Random Hentai source Images.
 - /avatar: Sends Random Avatar Stickers.
 - /erofeet: Sends Random Ero-Feet source Images.
 - /holo: Sends Random Holo source Images.
 - /tits: Sends Random Tits source Images.
 - /pussygif: Sends Random Pussy GIFs.
 - /holoero: Sends Random Ero-Holo source Images.
 - /pussy: Sends Random Pussy source Images.
 - /hentaigif: Sends Random Hentai GIFs.
 - /classic: Sends Random Classic Hentai GIFs.
 - /kuni: Sends Random Pussy Lick GIFs.
 - /waifu: Sends Random Waifu Stickers.
 - /kiss: Sends Random Kissing GIFs.
 - /femdom: Sends Random Femdom source Images.
 - /cuddle: Sends Random Cuddle GIFs.
 - /erok: Sends Random Ero-Kitsune source Images.
 - /foxgirl: Sends Random FoxGirl source Images.
 - /titsgif: Sends Random Tits GIFs.
 - /ero: Sends Random Ero source Images.
 - /smug: Sends Random Smug GIFs.
 - /baka: Sends Random Baka Shout GIFs.
 - /dva: Sends Random D.VA source Images.
"""

LEWDKEMO_HANDLER = CommandHandler("lewdkemo", lewdkemo)
NEKO_HANDLER = CommandHandler("neko", neko)
FEET_HANDLER = CommandHandler("feet", feet)
YURI_HANDLER = CommandHandler("yuri", yuri)
TRAP_HANDLER = CommandHandler("trap", trap)
FUTANARI_HANDLER = CommandHandler("futanari", futanari)
HOLOLEWD_HANDLER = CommandHandler("hololewd", hololewd)
SOLOGIF_HANDLER = CommandHandler("sologif", sologif)
CUMGIF_HANDLER = CommandHandler("cumgif", cumgif)
EROKEMO_HANDLER = CommandHandler("erokemo", erokemo)
LESBIAN_HANDLER = CommandHandler("lesbian", lesbian)
WALLPAPER_HANDLER = CommandHandler("wallpaper", wallpaper)
LEWDK_HANDLER = CommandHandler("lewdk", lewdk)
NGIF_HANDLER = CommandHandler("ngif", ngif)
TICKLE_HANDLER = CommandHandler("tickle", tickle)
LEWD_HANDLER = CommandHandler("lewd", lewd)
FEED_HANDLER = CommandHandler("feed", feed)
EROYURI_HANDLER = CommandHandler("eroyuri", eroyuri)
ERON_HANDLER = CommandHandler("eron", eron)
CUM_HANDLER = CommandHandler("cum", cum)
BJGIF_HANDLER = CommandHandler("bjgif", bjgif)
BJ_HANDLER = CommandHandler("bj", bj)
NEKONSFW_HANDLER = CommandHandler("nekonsfw", nekonsfw)
SOLO_HANDLER = CommandHandler("solo", solo)
KEMONOMIMI_HANDLER = CommandHandler("kemonomimi", kemonomimi)
AVATARLEWD_HANDLER = CommandHandler("avatarlewd", avatarlewd)
GASM_HANDLER = CommandHandler("gasm", gasm)
POKE_HANDLER = CommandHandler("poke", poke)
ANAL_HANDLER = CommandHandler("anal", anal)
HENTAI_HANDLER = CommandHandler("hentai", hentai)
AVATAR_HANDLER = CommandHandler("avatar", avatar)
EROFEET_HANDLER = CommandHandler("erofeet", erofeet)
HOLO_HANDLER = CommandHandler("holo", holo)
TITS_HANDLER = CommandHandler("tits", tits)
PUSSYGIF_HANDLER = CommandHandler("pussygif", pussygif)
HOLOERO_HANDLER = CommandHandler("holoero", holoero)
PUSSY_HANDLER = CommandHandler("pussy", pussy)
HENTAIGIF_HANDLER = CommandHandler("hentaigif", hentaigif)
CLASSIC_HANDLER = CommandHandler("classic", classic)
KUNI_HANDLER = CommandHandler("kuni", kuni)
WAIFU_HANDLER = CommandHandler("waifu", waifu)
LEWD_HANDLER = CommandHandler("lewd", lewd)
KISS_HANDLER = CommandHandler("kiss", kiss)
FEMDOM_HANDLER = CommandHandler("femdom", femdom)
CUDDLE_HANDLER = CommandHandler("cuddle", cuddle)
EROK_HANDLER = CommandHandler("erok", erok)
FOXGIRL_HANDLER = CommandHandler("foxgirl", foxgirl)
TITSGIF_HANDLER = CommandHandler("titsgif", titsgif)
ERO_HANDLER = CommandHandler("ero", ero)
SMUG_HANDLER = CommandHandler("smug", smug)
BAKA_HANDLER = CommandHandler("baka", baka)
DVA_HANDLER = CommandHandler("dva", dva)

dispatcher.add_handler(LEWDKEMO_HANDLER)
dispatcher.add_handler(NEKO_HANDLER)
dispatcher.add_handler(FEET_HANDLER)
dispatcher.add_handler(YURI_HANDLER)
dispatcher.add_handler(TRAP_HANDLER)
dispatcher.add_handler(FUTANARI_HANDLER)
dispatcher.add_handler(HOLOLEWD_HANDLER)
dispatcher.add_handler(SOLOGIF_HANDLER)
dispatcher.add_handler(CUMGIF_HANDLER)
dispatcher.add_handler(EROKEMO_HANDLER)
dispatcher.add_handler(LESBIAN_HANDLER)
dispatcher.add_handler(WALLPAPER_HANDLER)
dispatcher.add_handler(LEWDK_HANDLER)
dispatcher.add_handler(NGIF_HANDLER)
dispatcher.add_handler(TICKLE_HANDLER)
dispatcher.add_handler(LEWD_HANDLER)
dispatcher.add_handler(FEED_HANDLER)
dispatcher.add_handler(EROYURI_HANDLER)
dispatcher.add_handler(ERON_HANDLER)
dispatcher.add_handler(CUM_HANDLER)
dispatcher.add_handler(BJGIF_HANDLER)
dispatcher.add_handler(BJ_HANDLER)
dispatcher.add_handler(NEKONSFW_HANDLER)
dispatcher.add_handler(SOLO_HANDLER)
dispatcher.add_handler(KEMONOMIMI_HANDLER)
dispatcher.add_handler(AVATARLEWD_HANDLER)
dispatcher.add_handler(GASM_HANDLER)
dispatcher.add_handler(POKE_HANDLER)
dispatcher.add_handler(ANAL_HANDLER)
dispatcher.add_handler(HENTAI_HANDLER)
dispatcher.add_handler(AVATAR_HANDLER)
dispatcher.add_handler(EROFEET_HANDLER)
dispatcher.add_handler(HOLO_HANDLER)
dispatcher.add_handler(TITS_HANDLER)
dispatcher.add_handler(PUSSYGIF_HANDLER)
dispatcher.add_handler(HOLOERO_HANDLER)
dispatcher.add_handler(PUSSY_HANDLER)
dispatcher.add_handler(HENTAIGIF_HANDLER)
dispatcher.add_handler(CLASSIC_HANDLER)
dispatcher.add_handler(KUNI_HANDLER)
dispatcher.add_handler(WAIFU_HANDLER)
dispatcher.add_handler(LEWD_HANDLER)
dispatcher.add_handler(KISS_HANDLER)
dispatcher.add_handler(FEMDOM_HANDLER)
dispatcher.add_handler(CUDDLE_HANDLER)
dispatcher.add_handler(EROK_HANDLER)
dispatcher.add_handler(FOXGIRL_HANDLER)
dispatcher.add_handler(TITSGIF_HANDLER)
dispatcher.add_handler(ERO_HANDLER)
dispatcher.add_handler(SMUG_HANDLER)
dispatcher.add_handler(BAKA_HANDLER)
dispatcher.add_handler(DVA_HANDLER)

__handlers__ = [
    NEKO_HANDLER,
    FEET_HANDLER,
    YURI_HANDLER,
    TRAP_HANDLER,
    FUTANARI_HANDLER,
    HOLOLEWD_HANDLER,
    SOLOGIF_HANDLER,
    CUMGIF_HANDLER,
    EROKEMO_HANDLER,
    LESBIAN_HANDLER,
    WALLPAPER_HANDLER,
    LEWDK_HANDLER,
    NGIF_HANDLER,
    TICKLE_HANDLER,
    LEWD_HANDLER,
    FEED_HANDLER,
    EROYURI_HANDLER,
    ERON_HANDLER,
    CUM_HANDLER,
    BJGIF_HANDLER,
    BJ_HANDLER,
    NEKONSFW_HANDLER,
    SOLO_HANDLER,
    KEMONOMIMI_HANDLER,
    AVATARLEWD_HANDLER,
    GASM_HANDLER,
    POKE_HANDLER,
    ANAL_HANDLER,
    HENTAI_HANDLER,
    AVATAR_HANDLER,
    EROFEET_HANDLER,
    HOLO_HANDLER,
    TITS_HANDLER,
    PUSSYGIF_HANDLER,
    HOLOERO_HANDLER,
    PUSSY_HANDLER,
    HENTAIGIF_HANDLER,
    CLASSIC_HANDLER,
    KUNI_HANDLER,
    WAIFU_HANDLER,
    LEWD_HANDLER,
    KISS_HANDLER,
    FEMDOM_HANDLER,
    LEWDKEMO_HANDLER,
    CUDDLE_HANDLER,
    EROK_HANDLER,
    FOXGIRL_HANDLER,
    TITSGIF_HANDLER,
    ERO_HANDLER,
    SMUG_HANDLER,
    BAKA_HANDLER,
    DVA_HANDLER,
]
