from utils.decorators import block_group, restricted
from config import LIST_OF_ADMINS
from telegram import ParseMode
from telegram.error import TelegramError


# =========================================
# send2admin - send message to all admins
# =========================================
@block_group
@restricted
def execute(update, context):
    """
    'send2admin' sends a message to all admins

    :param update: bot update
    :param context: CallbackContext
    :return: None
    """

    # get the message to be sent
    fid = open('./admin_only/message.txt')
    msg = fid.read()
    fid.close()

    # send to all admins
    for id in LIST_OF_ADMINS:
        chat_id = int(id)
        # try to send the message
        try:
            context.bot.send_message(chat_id=chat_id,
                             text=msg,
                             parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

        # if the admin closed the bot don't care about the exception
        except TelegramError:
            pass