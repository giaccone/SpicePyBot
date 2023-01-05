from utils.decorators import block_group
import os
from telegram import ParseMode, ChatAction
from utils.functions import get_solution


# =========================================
# reply - catch any message and reply to it
# =========================================
@block_group
def execute(update, context):
    """
    'reply' provides the result to a netlist send via text message. If /netlist is not
    used before sending the netlist, a funny message is sent.

    :param update: bot update
    :param context: CallbackContext
    :return: None
    """
    # check call to /netlist
    if os.path.exists("./users/" + str(update.message.chat_id) + "_waitnetlist"):
        # write the netlist
        fname = "./users/" + str(update.message.chat_id) + ".txt"
        fid = open(fname, "w")
        fid.write(str(update.message.text) + '\n')
        fid.close()

        # remove waitnetlist file for this user
        os.remove("./users/" + str(update.message.chat_id) + "_waitnetlist")

        # send the netlist for double check to user
        mex = 'This is your netlist:\n\n'
        with open(fname) as f:
            for line in f:
                mex += line
        context.bot.send_message(chat_id=update.message.chat_id, text=mex)

        # compute solution
        net, mex = get_solution(fname, update, context)

        # typing
        context.bot.send_chat_action(chat_id=update.message.chat_id, action=ChatAction.TYPING)

        if mex is None:  # in case of .tran or .ac-multi-freq mex is none, hence send the plot
            if net.analysis[0].lower() == '.tran':
                context.bot.send_photo(chat_id=update.message.chat_id,
                               photo=open('./users/tran_plot_' + str(update.message.chat_id) + '.png', 'rb'))
            elif net.analysis[0].lower() == '.ac':
                N = int(len(net.tf_cmd.split()[1:]) / 2)
                if N == 1:
                    context.bot.send_photo(chat_id=update.message.chat_id,
                                   photo=open('./users/bode_plot_' + str(update.message.chat_id) + '.png', 'rb'))
                else:
                    for k in range(N):
                        context.bot.send_photo(chat_id=update.message.chat_id,
                                       photo=open(
                                           './users/bode_plot_' + str(update.message.chat_id) + '_' + str(k) + '.png',
                                           'rb'))

        else:    # otherwise print results
            mex = 'Please remember that all components are analyzed with *passive sign convention*.\nHere you have  ' \
                  '*the circuit solution*.\n\n' + mex
            context.bot.send_message(chat_id=update.message.chat_id, text=mex,
                             parse_mode=ParseMode.MARKDOWN)

    else:    # ironic answer if the user send a random mesage to the Bot
        update.message.reply_text("Come on! We are here to solve circuits and not to chat! 😀\n"
                                  "Please provide me a netlist.", quote=True)