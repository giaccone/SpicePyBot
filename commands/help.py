from utils.decorators import block_group
from telegram.constants import ParseMode

# ==========================
# help - short guide
# ==========================
@block_group
async def execute(update, context):
    """
    'help' provides information about the use of the bot

    :param update: bot update
    :param context: CallbackContext
    :return: None
    """
    msg = "*Very short guide*.\n\n" #1)upload a file with the netlist (don't know what a netlist is? Run `/tutorial` in the bot)\n2) enjoy\n\n\n*If you need a more detailed guide*\nRun `/tutorial` in the bot"
    msg += "The Bot makes use of netlists to describe circuits. If you do not know what "
    msg += "a netlist is, please refer to  SpicePy "
    msg += "[documentation](https://github.com/giaccone/SpicePy/wiki/User's-guide)"
    msg += " and [examples](https://github.com/giaccone/SpicePy/wiki/Examples).\n\n"
    msg += "Assuming that you know how to describe a circuit by means of a netlist, you can either:\n\n"
    msg += "1) use the command `/netlist` and write the netlist directly to the Bot (i.e. chatting with the BOT)\n\n"
    msg += "or\n\n"
    msg += "2) send a text file to the Bot including the netlist. The Bot will catch it and it'll solve it.\n\n"
    msg += "*Finally*\n"
    msg += "read the full [tutorial](https://github.com/giaccone/SpicePyBot/wiki) if "
    msg += "you are completely new to this subject."
    await context.bot.send_message(chat_id=update.message.chat_id,
                     text=msg,
                     parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
