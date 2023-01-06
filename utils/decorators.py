from functools import wraps
from telegram.constants import ParseMode
from config import LIST_OF_ADMINS


# ==========================
# restriction decorator
# ==========================
def restricted(func):
    """
    'restricted' decorates a function so that it can be used only to allowed users

    :param func: function to be decorated
    :return: function wrapper
    """
    @wraps(func)
    async def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in LIST_OF_ADMINS:
            print("Unauthorized access denied for {}.".format(user_id))
            await context.bot.send_message(chat_id=update.message.chat_id, text="You are not authorized to run this command")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped


# ==========================
# block group decorator
# ==========================
def block_group(func):
    """
    'block_group' decorates functions so that they can't be used in telegram groups

    :param func: function to be decorated
    :return: function wrapper
    """
    @wraps(func)
    async def wrapped(update, context, *args, **kwargs):
        # skip requests from groups
        if update.message.chat_id < 0:
            mex = "This bot is for personal use only.\n"
            mex += "*Please remove it from this group*\n"
            await context.bot.send_message(chat_id=update.message.chat_id, text=mex,
                             parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
            return
        return await func(update, context, *args, **kwargs)
    return wrapped
