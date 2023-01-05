from utils.decorators import block_group, restricted
import numpy as np
from telegram.error import TelegramError
from telegram import ParseMode
from config import LIST_OF_ADMINS
import os


# =========================================
# send2all - send message to all users
# =========================================
@block_group
@restricted
def execute(update, context):
    """
    'send2all' sends a message to all users

    :param update: bot update
    :param context: CallbackContext
    :return: None
    """

    # read all users from StatBot.log
    user = []
    with open('./StatBot.log') as fid:
        for line in fid:
            ele = line.split(' - ')
            user.append(int(ele[4].replace('UserID: ', '')))

    # convert to numpy array
    user = np.unique(np.array(user))

    # merge them with the user database
    if os.path.exists('./users/users_database.db'):
        user_db = []
        with open('./users/users_database.db', 'r') as fid:
            for line in fid:
                user_db.append(int(line))

        user_db = np.unique(np.array(user_db))
        user = np.unique(np.concatenate((user, user_db)))
        np.savetxt('./users/users_database.db', user, fmt="%s")
    else:
        np.savetxt('./users/users_database.db', user, fmt="%s")

    # get the message to be sent
    fid = open('./admin_only/message.txt')
    msg = fid.read()
    fid.close()

    # send to all user
    cnt_sent = 0
    cnt_not_sent = 0
    for id in user:
        chat_id = int(id)
        # try to send the message
        try:
            context.bot.send_message(chat_id=chat_id,
                             text=msg,
                             parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
            cnt_sent += 1

        # if the user closed the bot, cacth exception and update cnt_not_sent
        except TelegramError:
            cnt_not_sent += 1

    # print on screen
    msg = "*{} users* notified with the above message.\n".format(cnt_sent)
    msg += "*{} users* not notified (bot is inactive).".format(cnt_not_sent)

    # send to all admins stat about message sent
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