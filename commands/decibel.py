import os
from utils.decorators import block_group


# =========================================
# decibel - toggle decibel in bode plot
# =========================================
@block_group
def execute(update, context):
    """
    'decibel' enable/disable decibel representation in Bode plots

    :param update: bot update
    :param context: CallbackContext
    :return: None
    """

    if os.path.exists('./users/' + str(update.message.chat_id) + '.cnf'):
        # get configurations
        fname = './users/' + str(update.message.chat_id) + '.cnf'
        fid = open(fname, 'r')
        flag = fid.readline()[:-1]  # read nodal_pot conf
        nodal_pot = flag == 'True'
        flag = fid.readline()[:-1]  # read polar conf
        polar = flag == 'True'
        flag = fid.readline()  # read dB conf
        dB = flag == 'True'

        # switch nodal pot keep polar
        fname = './users/' + str(update.message.chat_id) + '.cnf'
        fid = open(fname, 'w')
        fid.write(str(nodal_pot) + '\n')
        fid.write(str(polar) + '\n')
        fid.write(str(not dB))
        fid.close()
    else:
        dB = False

        # Initialize config file with dB = True (everything else False)
        fname = './users/' + str(update.message.chat_id) + '.cnf'
        fid = open(fname, 'w')
        fid.write('False\n')   # this is for the node potential
        fid.write('False\n')   # this is for the polar flag
        fid.write(str(not dB))  # this is for the decibel flag
        fid.close()

    # notify user
    if dB:
        context.bot.send_message(chat_id=update.message.chat_id, text="bode plot: decibel disabled")
    else:
        context.bot.send_message(chat_id=update.message.chat_id, text="bode plot: decibel enabled")