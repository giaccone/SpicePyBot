import os
from utils.decorators import block_group

# =========================================
# netlist - write te netlist in the BOT
# =========================================
@block_group
def execute(update, context):
    """
    'netlist' tell to the bot that the used intend to send a netlist via text message

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

    open("./users/" + str(update.message.chat_id) + "_waitnetlist", 'w').close()
    context.bot.send_message(chat_id=update.message.chat_id, text="Please write the netlist\nAll in one message.")