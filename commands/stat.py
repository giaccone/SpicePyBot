from utils.decorators import block_group, restricted
import numpy as np
from config import LIST_OF_ADMINS
from telegram.constants import ParseMode

# =========================================
# stat - get stat
# =========================================
@block_group
@restricted
async def execute(update, context):
    """
    'stat' computes statistical information about the bot use

    :param update: bot update
    :param context: CallbackContext
    :return: None
    """
    await context.bot.send_document(chat_id=update.message.chat_id, document=open('./StatBot.log', 'rb'))

    # initialize list
    analysis = []
    user = []

    with open('./StatBot.log') as fid:
        for line in fid:
            ele = line.split(' - ')

            if int(ele[-1].replace('UserID: ','')) not in LIST_OF_ADMINS:
                analysis.append(ele[3].replace('Analysis: ', '').lower())
                user.append(int(ele[4].replace('UserID: ', '')))

    # convert to numpy array
    analysis = np.array(analysis)
    user = np.array(user)

    # percentages
    x = []
    labels = '.op', '.ac', '.tran'
    x.append(np.sum(analysis == labels[0]))
    x.append(np.sum(analysis == labels[1]))
    x.append(np.sum(analysis == labels[2]))

    # create mex
    mex = ''
    mex += '*# of Users*: {}\n'.format(np.unique(user).size)
    mex += '*# of Analyses*: {}\n'.format(analysis.size)
    mex += '    *.op*: {:.2f} %\n'.format(x[0]/np.sum(x)*100)
    mex += '    *.ac*: {:.2f} %\n'.format(x[1] / np.sum(x) * 100)
    mex += '    *.tran*: {:.2f} %\n'.format(x[2] / np.sum(x) * 100)

    await context.bot.send_message(chat_id=update.message.chat_id, text=mex,
                     parse_mode=ParseMode.MARKDOWN)
