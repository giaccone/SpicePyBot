# ======================
# general python modules
# ======================
import time
import logging
from functools import wraps
import os
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# ===================
# module from SpicePy
# ===================
import netlist as ntl
from netsolve import net_solve

# ==========================
# python-temegam-bot modules
# ==========================
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import telegram as telegram

# ===============================
# create necessary folders
# ===============================
if not os.path.exists('users'):
    os.makedirs('users')

# ===============================
# admin list
# ===============================
fid = open('./admin_only/admin_list.txt', 'r')
LIST_OF_ADMINS = [int(adm) for adm in fid.readline().split()]
fid.close()


# ==========================
# Logging
# ==========================
# define filter to log only one level
class MyFilter(object):
    def __init__(self, level):
        self.__level = level

    def filter(self, logRecord):
        return logRecord.levelno <= self.__level


# formatter
fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# StatLog: log how the log is used (only INFO)
StatLog = logging.getLogger('StatLog')
h1 = logging.FileHandler('StatBot.log')
h1.setFormatter(fmt)
StatLog.addHandler(h1)
StatLog.setLevel(logging.INFO)
StatLog.addFilter(MyFilter(logging.INFO))

# SolverLog: catch error in the netlist (>= WARNING)
SolverLog = logging.getLogger('SolverLog')
h2 = logging.FileHandler('SolverLog.log')
h2.setFormatter(fmt)
SolverLog.addHandler(h2)

# OtherLog: catch all other error using the dispatcher (>= WARNING)
OtherLog = logging.getLogger('OtherLog')
h3 = logging.FileHandler('OtherLog.log')
h3.setFormatter(fmt)
OtherLog.addHandler(h3)


# ==========================
# useful functions
# ==========================
# The following function reads the TOKEN from a file.
# This file is not incuded in the github-repo for obvious reasons
def read_token(filename):
    with open(filename) as f:
        token = f.readline().replace('\n', '')
    return token


# error_callback to log uncaught error
def error_callback(bot, update, error):
    OtherLog.error("Update {} caused error {}".format(update, error))


# compute the solution
def get_solution(fname, bot, update):
    """
    'get_solution' computes the solution of a network using SpicePy

    :param fname: filename with the netlist
    :param update: Bot updater
    :return:
        * mex:  solution formatted in a string
    """
    try:
        # create network and solve it
        net = ntl.Network(fname)

        # check if number of nodes exceeds the limit
        NMAX = 40
        if net.node_num > NMAX:
            mex = "Your netlist includes more than {:d} nodes.\n".format(net.node_num)
            mex += "*The maximum allowed number on this bot is {:d}.*\n".format(NMAX)
            mex += "Please reduce the number of nodes or take a look to the computational core of this bot "
            mex += "that does not have this limitation:\n"
            mex += "[SpicePy project](https://github.com/giaccone/SpicePy)"

        else:

            # limit sample for .tran to 2000 (max)
            if net.analysis[0].lower() == '.tran':
                Nsamples = float(net.convert_unit(net.analysis[2])) / float(net.convert_unit(net.analysis[1]))
                if Nsamples > 2000:
                    step = float(net.convert_unit(net.analysis[2]))/1999
                    net.analysis[1] = '{:.3e}'.format(step)

                    mex = "Your netlits defines a '.tran' analysis with *{:d}* samples\n".format(int(Nsamples))
                    mex += "Since this bot runs on a limited hardware shared by many users\n"
                    mex += "The analysis has been limited to *2000* samples:\n"
                    mex += "`.tran " + net.analysis[1] + " " + net.analysis[-1] + "`"


                    bot.send_message(chat_id=update.message.chat_id,
                                     text=mex,
                                     parse_mode=telegram.ParseMode.MARKDOWN)

            # limit sample for .ac to 2000 (max)
            elif net.analysis[0].lower() == '.ac':
                # get frequencies
                net.frequency_span()

                if not np.isscalar(net.f):
                    # get Nsamples
                    Nsamples = len(net.f)
                    # limit di 2000 max
                    if Nsamples > 2000:
                        scale = 2000 / Nsamples
                        old_analysys = "`" + " ".join(net.analysis) + "`"
                        net.analysis[2] = str(int(np.ceil(scale * float(net.convert_unit(net.analysis[2])))))
                        new_analysys = "`" + " ".join(net.analysis) + "`"

                        mex = "Your netlits defines a '.tran' analysis with *{:d}* samples\n".format(int(Nsamples))
                        mex += "Since this bot runs on a limited hardware shared by many users\n"
                        mex += "The analysis has been limited to *2000* samples:\n"
                        mex += "original analysis: " + old_analysys + "\n"
                        mex += "ner analysis: " + new_analysys + "\n"

                        bot.send_message(chat_id=update.message.chat_id,
                                         text=mex,
                                         parse_mode=telegram.ParseMode.MARKDOWN)

            # get configurations
            fname = './users/' + str(update.message.chat_id) + '.cnf'
            fid = open(fname, 'r')
            flag = fid.readline()[:-1]  # read nodal_pot conf
            nodal_pot = flag == 'True'
            flag = fid.readline()[:-1]  # read polar conf
            polar = flag == 'True'
            flag = fid.readline()  # read dB conf
            dB = flag == 'True'

            if net.analysis[0] == '.op':
                # forcepolar to False for .op problems
                polar = False

            # solve the network
            net_solve(net)

            # .op and .ac (single-frequency): prepare mex to be printed
            if (net.analysis[0].lower() == '.op') | ((net.analysis[0].lower() == '.ac') & (np.isscalar(net.f))):
                # get branch quantities
                net.branch_voltage()
                net.branch_current()
                net.branch_power()

                # prepare message
                mex = net.print(polar=polar, message=True)
                mex = mex.replace('==============================================\n'
                                  '               branch quantities'
                                  '\n==============================================\n', '*branch quantities*\n`')
                mex = mex.replace('----------------------------------------------', '')
                mex += '`'

                # if the user wants node potentials add it to mex
                if nodal_pot:
                    # create local dictionary node-number 2 node-label
                    num2node_label = {num: name for name, num in net.node_label2num.items() if name != '0'}

                    # compute the node potentials
                    mex0 = '*node potentials*\n`'
                    for num in num2node_label:
                        voltage = net.get_voltage('(' + num2node_label[num] + ')')[0]
                        if polar:
                            mex0 += 'v(' + num2node_label[num] + ') = {:10.4f} V < {:10.4f}°\n'.format(np.abs(voltage),np.angle(voltage) * 180 / np.pi)
                        else:
                            mex0 += 'v(' + num2node_label[num] + ') = {:10.4f} V\n'.format(voltage)


                    # add newline
                    mex0 += '`\n\n'

                    # add node potentials before branch quantities
                    mex = mex0 + mex

            elif net.analysis[0].lower() == '.tran':
                hf = net.plot(to_file=True, filename='./users/tran_plot_' + str(update.message.chat_id) + '.png',dpi_value=150)
                mex = None
                plt.close(hf)

            elif net.analysis[0].lower() == '.ac':
                hf = net.bode(to_file=True, decibel=dB, filename='./users/bode_plot_' + str(update.message.chat_id) + '.png', dpi_value=150)
                mex = None
                if isinstance(hf, list):
                    for fig in hf:
                        plt.close(fig)
                else:
                    plt.close(hf)

            # Log every time a network is solved
            # To make stat it is saved the type of network and the UserID
            StatLog.info('Analysis: ' + net.analysis[0] + ' - UserID: ' + str(update.effective_user.id))

        return net, mex

    except:
        # set network to None
        net = None
        # read network with issues
        wrong_net = ''
        with open(fname) as f:
            for line in f:
                wrong_net += line
        wrong_net = wrong_net.replace('\n', '  /  ')

        # log error
        SolverLog.error('UserID: ' + str(update.effective_user.id) + ' - Netlist error: ' + wrong_net)
        return net, "*Something went wrong with your netlist*.\nPlease check the netlist format."


# ==========================
# restriction decorator
# ==========================
def restricted(func):
    @wraps(func)
    def wrapped(bot, update, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in LIST_OF_ADMINS:
            print("Unauthorized access denied for {}.".format(user_id))
            bot.send_message(chat_id=update.message.chat_id, text="You are not authorized to run this command")
            return
        return func(bot, update, *args, **kwargs)
    return wrapped


# ==========================
# block group decorator
# ==========================
def block_group(func):
    @wraps(func)
    def wrapped(bot, update, *args, **kwargs):
        # skip requests from groups
        if update.message.chat_id < 0:
            mex = "This bot is for personal use only.\n"
            mex += "*Please remove it from this group*\n"
            bot.send_message(chat_id=update.message.chat_id, text=mex,
                             parse_mode=telegram.ParseMode.MARKDOWN, disable_web_page_preview=True)
            return
        return func(bot, update, *args, **kwargs)
    return wrapped


# ==========================
# start - welcome message
# ==========================
@block_group
def start(bot, update):
    msg = "*Welcome to SpicePyBot*.\n\n"
    msg += "It allows you to solve linear:\n"
    msg += "  \* DC networks (.op)\n"
    msg += "  \* AC networks (.ac)\n"
    msg += "  \* dynamic networks (.tran)\n\n"
    msg += "Run the code:\n"
    msg += "`/help`:  to have a short guide.\n\n"
    msg += "or\n\n"
    msg += "Read the full [tutorial](https://github.com/giaccone/SpicePyBot/wiki) if "
    msg += "you are completely new to this subject."

    bot.send_message(chat_id=update.message.chat_id,
                     text=msg,
                     parse_mode=telegram.ParseMode.MARKDOWN, disable_web_page_preview=True)
    fname = './users/' + str(update.message.chat_id) + '.cnf'
    fid = open(fname, 'w')
    fid.write('False\n')  # this is for the node potential
    fid.write('False\n')  # this is for the polar flag
    fid.write('False')    # this is for the decibel flag
    fid.close()


# =========================================
# catch netlist from a file sent to the bot
# =========================================
@block_group
def catch_netlist(bot, update):

    # if current user don't have cnf file create it
    if not os.path.exists('./users/' + str(update.message.chat_id) + '.cnf'):
        fname = './users/' + str(update.message.chat_id) + '.cnf'
        fid = open(fname, 'w')
        fid.write('False\n')  # this is for the node potential
        fid.write('False\n')  # this is for the polar flag
        fid.write('False')    # this is for the decibel flag
        fid.close()

    # catch the netlist from file
    file = bot.getFile(update.message.document.file_id)
    fname = './users/' + str(update.message.chat_id) + '.txt'
    file.download(fname)

    # send the netlist for double check to user
    mex = 'This is your netlist:\n\n'
    with open(fname) as f:
        for line in f:
            mex += line
    bot.send_message(chat_id=update.message.chat_id, text=mex)

    # compute solution
    net, mex = get_solution(fname, bot, update)

    # typing
    bot.send_chat_action(chat_id=update.message.chat_id, action=telegram.ChatAction.TYPING)

    if mex is None:    # in case of .tran or .ac-multi-freq mex is none, hence send the plot
        if net.analysis[0].lower() == '.tran':
            bot.send_photo(chat_id=update.message.chat_id,
                           photo=open('./users/tran_plot_' + str(update.message.chat_id) + '.png', 'rb'))
        elif net.analysis[0].lower() == '.ac':
            N = int(len(net.tf_cmd.split()[1:]) / 2)
            if N == 1:
                bot.send_photo(chat_id=update.message.chat_id,
                               photo=open('./users/bode_plot_' + str(update.message.chat_id) + '.png', 'rb'))
            else:
                for k in range(N):
                    bot.send_photo(chat_id=update.message.chat_id,
                                   photo=open(
                                       './users/bode_plot_' + str(update.message.chat_id) + '_' + str(k) + '.png',
                                       'rb'))

    else:    # otherwise print results
        mex = 'Please remember that all components are analyzed with *passive sign convention*.\nHere you have  ' \
              '*the circuit solution*.\n\n' + mex
        bot.send_message(chat_id=update.message.chat_id, text=mex,
                         parse_mode=telegram.ParseMode.MARKDOWN, disable_web_page_preview=True)


# ==========================
# help - short guide
# ==========================
@block_group
def help(bot, update):
    msg = "*Very short guide*.\n\n" #1)upload a file with the netlist (don't know what a netlist is? Run `/tutorial` in the bot)\n2) enjoy\n\n\n*If you need a more detailed guide*\nRun `/tutorial` in the bot"
    msg += "The Bot makes use of netlists to describe circuits. If you do not know what "
    msg += "a netlist is, please refer to  SpicePy "
    msg += "[documentation](https://github.com/giaccone/SpicePy/wiki/User's-guide)"
    msg += " and [examples](https://github.com/giaccone/SpicePy/wiki/Examples).\n\n"
    msg += "Assuming that you know how to describe a circuit by means of a netlist, you can either:\n\n"
    msg += "1) use the command `/netlist` and write the netlist directly to the Bot (i.e. chatting with the BOT)\n\n"
    msg += "or\n\n"
    msg += "2) send a text file to the Bot including the netlist. The Bot will catch it and it'll solve it.\n\n"
    msg += "*Finally*\n"
    msg += "read the full [tutorial](https://github.com/giaccone/SpicePyBot/wiki) if "
    msg += "you are completely new to this subject."
    bot.send_message(chat_id=update.message.chat_id,
                     text=msg,
                     parse_mode=telegram.ParseMode.MARKDOWN, disable_web_page_preview=True)


# =========================================
# netlist - write te netlist in the BOT
# =========================================
@block_group
def netlist(bot, update):

    # if current user don't have cnf file create it
    if not os.path.exists('./users/' + str(update.message.chat_id) + '.cnf'):
        fname = './users/' + str(update.message.chat_id) + '.cnf'
        fid = open(fname, 'w')
        fid.write('False\n')  # this is for the node potential
        fid.write('False\n')  # this is for the polar flag
        fid.write('False')    # this is for the decibel flag
        fid.close()

    open("./users/" + str(update.message.chat_id) + "_waitnetlist", 'w').close()
    bot.send_message(chat_id=update.message.chat_id, text="Please write the netlist\nAll in one message.")


# =========================================
# reply - catch any message and reply to it
# =========================================
@block_group
def reply(bot, update):
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
        bot.send_message(chat_id=update.message.chat_id, text=mex)

        # compute solution
        net, mex = get_solution(fname, bot, update)

        # typing
        bot.send_chat_action(chat_id=update.message.chat_id, action=telegram.ChatAction.TYPING)

        if mex is None:  # in case of .tran or .ac-multi-freq mex is none, hence send the plot
            if net.analysis[0].lower() == '.tran':
                bot.send_photo(chat_id=update.message.chat_id,
                               photo=open('./users/tran_plot_' + str(update.message.chat_id) + '.png', 'rb'))
            elif net.analysis[0].lower() == '.ac':
                N = int(len(net.tf_cmd.split()[1:]) / 2)
                if N == 1:
                    bot.send_photo(chat_id=update.message.chat_id,
                                   photo=open('./users/bode_plot_' + str(update.message.chat_id) + '.png', 'rb'))
                else:
                    for k in range(N):
                        bot.send_photo(chat_id=update.message.chat_id,
                                       photo=open(
                                           './users/bode_plot_' + str(update.message.chat_id) + '_' + str(k) + '.png',
                                           'rb'))

        else:    # otherwise print results
            mex = 'Please remember that all components are analyzed with *passive sign convention*.\nHere you have  ' \
                  '*the circuit solution*.\n\n' + mex
            bot.send_message(chat_id=update.message.chat_id, text=mex,
                             parse_mode=telegram.ParseMode.MARKDOWN)

    else:    # ironic answer if the user send a random mesage to the Bot
        update.message.reply_text("Come on! We are here to solve circuits and not to chat! 😀\n"
                                  "Please provide me a netlist.", quote=True)


# =========================================
# complex_repr - toggle polar/cartesian
# =========================================
@block_group
def complex_repr(bot, update):
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
        bot.send_message(chat_id=update.message.chat_id, text="Switched to cartesian representation")
    else:
        bot.send_message(chat_id=update.message.chat_id, text="Switched to polar representation")


# =========================================
# nodal_pot - toggle node potentials in output
# =========================================
@block_group
def nodal_pot(bot, update):

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
        bot.send_message(chat_id=update.message.chat_id, text="Node potentials removed from results")
    else:
        bot.send_message(chat_id=update.message.chat_id, text="Node potentials included in results")


# =========================================
# decibel - toggle decibel in bode plot
# =========================================
@block_group
def decibel(bot, update):

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
        bot.send_message(chat_id=update.message.chat_id, text="bode plot: decibel disabled")
    else:
        bot.send_message(chat_id=update.message.chat_id, text="bode plot: decibel enabled")


# =========================================
# restart - restart the BOT
# =========================================
@block_group
@restricted
def restart(bot, update):
    bot.send_message(update.message.chat_id, "Bot is restarting...")
    time.sleep(0.2)
    os.execl(sys.executable, sys.executable, *sys.argv)


# =========================================
# log - get log
# =========================================
@block_group
@restricted
def log(bot, update):
    bot.send_document(chat_id=update.message.chat_id, document=open('./SolverLog.log', 'rb'))
    bot.send_document(chat_id=update.message.chat_id, document=open('./OtherLog.log', 'rb'))


# =========================================
# stat - get stat
# =========================================
@block_group
@restricted
def stat(bot, update):
    bot.send_document(chat_id=update.message.chat_id, document=open('./StatBot.log', 'rb'))

    # initialize list
    analysis = []
    user = []

    fid = open('./admin_only/admin_list.txt', 'r')
    ADMIN_LIST = [int(adm) for adm in fid.readline().split()]
    fid.close()

    with open('./StatBot.log') as fid:
        for line in fid:
            ele = line.split(' - ')

            if int(ele[-1].replace('UserID: ','')) not in ADMIN_LIST:
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

    bot.send_message(chat_id=update.message.chat_id, text=mex,
                     parse_mode=telegram.ParseMode.MARKDOWN)


# =========================================
# send2all - send message to all users
# =========================================
@block_group
@restricted
def send2all(bot, update):

    # read all users from StatBot.log
    user = []
    with open('./StatBot.log') as fid:
        for line in fid:
            ele = line.split(' - ')
            user.append(int(ele[4].replace('UserID: ', '')))

    # convert to numpy array
    user = np.unique(np.array(user))

    # merge them with the user database
    if os.path.exists('./users/users_database.db'):
        user_db = []
        with open('./users/users_database.db', 'r') as fid:
            for line in fid:
                user_db.append(int(line))

        user_db = np.unique(np.array(user_db))
        user = np.unique(np.concatenate((user, user_db)))
        np.savetxt('./users/users_database.db', user, fmt="%s")
    else:
        np.savetxt('./users/users_database.db', user, fmt="%s")

    # get the message to be sent
    fid = open('./admin_only/message.txt')
    msg = fid.read()
    fid.close()

    # send to all user
    cnt_sent = 0
    cnt_not_sent = 0
    for id in user:
        chat_id = int(id)
        # try to send the message
        try:
            bot.send_message(chat_id=chat_id,
                             text=msg,
                             parse_mode=telegram.ParseMode.MARKDOWN, disable_web_page_preview=True)
            cnt_sent += 1

        # if the user closed the bot, cacth exception and update cnt_not_sent
        except telegram.error.TelegramError:
            cnt_not_sent += 1

    # print on screen
    msg = "*{} users* notified with the above message.\n".format(cnt_sent)
    msg += "*{} users* not notified (bot is inactive).".format(cnt_not_sent)

    # get admin list
    fid = open('./admin_only/admin_list.txt', 'r')
    ADMIN_LIST = [int(adm) for adm in fid.readline().split()]
    fid.close()

    # send to all admins stat about message sent
    for id in ADMIN_LIST:
        chat_id = int(id)

        # try to send the message
        try:
            bot.send_message(chat_id=chat_id,
                             text=msg,
                             parse_mode=telegram.ParseMode.MARKDOWN, disable_web_page_preview=True)

        # if the admin closed the bot don't care about the exception
        except telegram.error.TelegramError:
            pass


# =========================================
# send2admin - send message to all admins
# =========================================
@block_group
@restricted
def send2admin(bot, update):

    # get admin list
    fid = open('./admin_only/admin_list.txt', 'r')
    ADMIN_LIST = [int(adm) for adm in fid.readline().split()]
    fid.close()

    # get the message to be sent
    fid = open('./admin_only/message.txt')
    msg = fid.read()
    fid.close()

    # send to all admins
    for id in ADMIN_LIST:
        chat_id = int(id)
        # try to send the message
        try:
            bot.send_message(chat_id=chat_id,
                             text=msg,
                             parse_mode=telegram.ParseMode.MARKDOWN, disable_web_page_preview=True)

        # if the admin closed the bot don't care about the exception
        except telegram.error.TelegramError:
            pass


# =========================================
# unknown - catch any wrong command
# =========================================
@block_group
def unknown(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Sorry, I didn't understand that command.")


# =========================================
# bot - main
# =========================================
def main():
    # set TOKEN and initialization
    fname = './admin_only/SpicePyBot_token.txt'
    updater = Updater(token=read_token(fname))
    dispatcher = updater.dispatcher

    # /start handler
    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)

    # catch netlist when sent to the BOT
    dispatcher.add_handler(MessageHandler(Filters.document, catch_netlist))

    # /help handler
    help_handler = CommandHandler('help', help)
    dispatcher.add_handler(help_handler)

    # /netlist handler
    netlist_handler = CommandHandler('netlist', netlist)
    dispatcher.add_handler(netlist_handler)

    # reply to random message or get netlist after /netlist
    reply_handler = MessageHandler(Filters.text, reply)
    dispatcher.add_handler(reply_handler)

    # /complex_repr handler
    complex_repr_handler = CommandHandler('complex_repr', complex_repr)
    dispatcher.add_handler(complex_repr_handler)

    # /nodal_pot handler
    nodal_pot_handler = CommandHandler('nodal_pot', nodal_pot)
    dispatcher.add_handler(nodal_pot_handler)

    # /decibel handler
    decibel_handler = CommandHandler('decibel', decibel)
    dispatcher.add_handler(decibel_handler)

    # /r - restart the bot
    dispatcher.add_handler(CommandHandler('r', restart))

    # /log - get log file
    dispatcher.add_handler(CommandHandler('log', log))

    # /stat - get stat file
    dispatcher.add_handler(CommandHandler('stat', stat))

    # /send2all - send message to all users
    dispatcher.add_handler(CommandHandler('send2all', send2all))

    # /send2admin - send message to all admins
    dispatcher.add_handler(CommandHandler('send2admin', send2admin))

    # reply to unknown commands
    unknown_handler = MessageHandler(Filters.command, unknown)
    dispatcher.add_handler(unknown_handler)

    # log every uncaught error with error handler
    dispatcher.add_error_handler(error_callback)

    # start the BOT
    updater.start_polling()
    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
