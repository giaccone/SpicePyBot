from utils.decorators import block_group
import os
from utils.functions import get_solution
from telegram.constants import ParseMode, ChatAction


# =========================================
# catch netlist from a file sent to the bot
# =========================================
@block_group
async def execute(update, context):
    """
    'catch_netlist' get a netlist in a text file and provide the results.

    :param update: bot update
    :param context: CallbackContext
    :return: None
    """

    # if current user don't have cnf file create it
    if not os.path.exists('./users/' + str(update.message.chat_id) + '.cnf'):
        fname = './users/' + str(update.message.chat_id) + '.cnf'
        fid = open(fname, 'w')
        fid.write('False\n')  # this is for the node potential
        fid.write('False\n')  # this is for the polar flag
        fid.write('False')    # this is for the decibel flag
        fid.close()

    # catch the netlist from file
    file = await context.bot.getFile(update.message.document.file_id)
    fname = './users/' + str(update.message.chat_id) + '.txt'
    await file.download_to_drive(fname)

    # send the netlist for double check to user
    mex = 'This is your netlist:\n\n'
    with open(fname) as f:
        for line in f:
            mex += line
    await context.bot.send_message(chat_id=update.message.chat_id, text=mex)

    # compute solution
    net, mex = await get_solution(fname, update, context)

    # typing
    await context.bot.send_chat_action(chat_id=update.message.chat_id, action=ChatAction.TYPING)

    if mex is None:    # in case of .tran or .ac-multi-freq mex is none, hence send the plot
        if net.analysis[0].lower() == '.tran':
            await context.bot.send_photo(chat_id=update.message.chat_id,
                           photo=open('./users/tran_plot_' + str(update.message.chat_id) + '.png', 'rb'))
        elif net.analysis[0].lower() == '.ac':
            N = int(len(net.tf_cmd.split()[1:]) / 2)
            if N == 1:
                await context.bot.send_photo(chat_id=update.message.chat_id,
                               photo=open('./users/bode_plot_' + str(update.message.chat_id) + '.png', 'rb'))
            else:
                for k in range(N):
                    await context.bot.send_photo(chat_id=update.message.chat_id,
                                   photo=open(
                                       './users/bode_plot_' + str(update.message.chat_id) + '_' + str(k) + '.png',
                                       'rb'))

    else:    # otherwise print results
        mex = 'Please remember that all components are analyzed with *passive sign convention*.\nHere you have  ' \
              '*the circuit solution*.\n\n' + mex
        await context.bot.send_message(chat_id=update.message.chat_id, text=mex,
                         parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
