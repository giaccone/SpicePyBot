from utils.decorators import block_group, restricted
from config import LIST_OF_ADMINS
import os
from telegram.error import TelegramError


# =========================================
# who - retrieve user info from user id
# =========================================
@block_group
@restricted
async def execute(update, context):
    """
    'who' retreive user info from user id

    :param update: bot update
    :param context: CallbackContext
    :return: None
    """

    # get user id provided with the command
    userID = int(update.message.text.replace('/who ', '').strip())

    # get and send data
    try:
        # try to get data
        chat = await context.bot.get_chat(chat_id=userID)
        # build messagge
        msg = "results for userID {}:\n  * username: @{}\n  * first name: {}\n  * last name: {}\n\n".format(userID,
                                                                                                            chat.username,
                                                                                                            chat.first_name,
                                                                                                            chat.last_name)
        # check if user has profile picture
        if hasattr(chat.photo, 'small_file_id'):
            photo = True
        else:
            photo = False
            msg += "\n\n The user has no profile picture."

        # send information
        for admin in LIST_OF_ADMINS:
            admin_id = int(admin)
            await context.bot.send_message(chat_id=admin_id, text=msg)
            if photo:
                file = await context.bot.getFile(chat.photo.small_file_id)
                fname = './users/propic.png'
                await file.download_to_drive(fname)
                await context.bot.send_photo(chat_id=admin_id, photo=open('./users/propic.png', 'rb'))
                os.remove('./users/propic.png')

                # send message when user if not found
    except TelegramError:
        msg += "\n\nuser {} not found".format(userID)
        for admin in LIST_OF_ADMINS:
            admin_id = int(admin)
            await context.bot.send_message(chat_id=admin_id, text=msg)
