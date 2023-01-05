import os
from utils.decorators import block_group


# =========================================
# complex_repr - toggle polar/cartesian
# =========================================
@block_group
def execute(update, context):
    """
    'complex_repr' switch from cartesian to polar representation for a complex number

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

        # keep nodal pot and toggle polar
        fname = './users/' + str(update.message.chat_id) + '.cnf'
        fid = open(fname, 'w')
        fid.write(str(nodal_pot) + '\n')
        fid.write(str(not polar) + '\n')
        fid.write(str(dB))
        fid.close()
    else:
        polar = False
        # Initialize config file with polar = True (everything else False)
        fname = './users/' + str(update.message.chat_id) + '.cnf'
        fid = open(fname, 'w')
        fid.write('False\n')  # this is for the node potential
        fid.write(str(not polar) + '\n')  # this is for the polar flag
        fid.write('False')  # this is for the decibel flag
        fid.close()

    # notify user
    if polar:
        context.bot.send_message(chat_id=update.message.chat_id, text="Switched to cartesian representation")
    else:
        context.bot.send_message(chat_id=update.message.chat_id, text="Switched to polar representation")
