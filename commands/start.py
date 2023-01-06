from utils.decorators import block_group
from telegram.constants import ParseMode


# ==========================
# start - welcome message
# ==========================
@block_group
async def execute(update, context):
    """
    'start' provides the start message

    :param update: bot update
    :param context: CallbackContext
    :return: None
    """
    msg = "*Welcome to SpicePyBot*.\n\n"
    msg += "It allows you to solve linear:\n"
    msg += "  \* DC networks (.op)\n"
    msg += "  \* AC networks (.ac)\n"
    msg += "  \* dynamic networks (.tran)\n\n"
    msg += "Run the code:\n"
    msg += "`/help`:  to have a short guide.\n\n"
    msg += "or\n\n"
    msg += "Read the full [tutorial](https://github.com/giaccone/SpicePyBot/wiki) if "
    msg += "you are completely new to this subject."

    await context.bot.send_message(chat_id=update.message.chat_id,
                     text=msg,
                     parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

    fname = './users/' + str(update.message.chat_id) + '.cnf'
    fid = open(fname, 'w')
    fid.write('False\n')  # this is for the node potential
    fid.write('False\n')  # this is for the polar flag
    fid.write('False')    # this is for the decibel flag
    fid.close()
