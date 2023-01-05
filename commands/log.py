from utils.decorators import block_group, restricted

# =========================================
# log - get log
# =========================================
@block_group
@restricted
def execute(update, context):
    """
    'log' sends log files in the chat

    :param update: bot update
    :param context: CallbackContext
    :return: None
    """

    context.bot.send_document(chat_id=update.message.chat_id, document=open('./SolverLog.log', 'rb'))
    context.bot.send_document(chat_id=update.message.chat_id, document=open('./OtherLog.log', 'rb'))