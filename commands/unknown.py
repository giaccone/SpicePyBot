from utils.decorators import block_group


# =========================================
# unknown - catch any wrong command
# =========================================
@block_group
async def execute(update, context):
    """
    'unknown' catch unknown commands

    :param update: bot update
    :param context: CallbackContext
    :return: None
    """
    await context.bot.send_message(chat_id=update.message.chat_id, text="Sorry, I didn't understand that command.")