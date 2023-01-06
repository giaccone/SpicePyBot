import os
from utils.decorators import block_group


# =========================================
# nodal_pot - toggle node potentials in output
# =========================================
@block_group
async def execute(update, context):
    """
    'nodal_pot' enable/disable node potentials in the results

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
        fid.write(str(not nodal_pot) + '\n')
        fid.write(str(polar) + '\n')
        fid.write(str(dB))
        fid.close()
    else:
        nodal_pot = False

        # Initialize config file with nodal_pot = True (everything else False)
        fname = './users/' + str(update.message.chat_id) + '.cnf'
        fid = open(fname, 'w')
        fid.write(str(not nodal_pot) + '\n')   # this is for the node potential
        fid.write('False\n')   # this is for the polar flag
        fid.write('False')  # this is for the decibel flag
        fid.close()

    # notify user
    if nodal_pot:
        await context.bot.send_message(chat_id=update.message.chat_id, text="Node potentials removed from results")
    else:
        await context.bot.send_message(chat_id=update.message.chat_id, text="Node potentials included in results")
