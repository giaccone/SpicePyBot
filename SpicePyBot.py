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
from threading import Thread
# token and list of admin
from config import LIST_OF_ADMINS, TOKEN
# import commands
import commands as cmd
# to be removed
from utils.decorators import restricted, block_group

# ===================
# module from SpicePy
# ===================
import spicepy.netlist as ntl
from spicepy.netsolve import net_solve

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


# error_callback to log uncaught error
def error_callback(update, context):
    """
    'error_callback' log uncaught error

    :param update: bot update
    :param context: CallbackContext
    :return: None
    """
    OtherLog.error("Update {} caused error {}".format(update, context.error))


# compute the solution
def get_solution(fname, update, context):
    """
    'get_solution' computes the solution of a network using SpicePy

    :param fname: filename with the netlist
    :param update: bot update
    :param context: CallbackContext
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


                    context.bot.send_message(chat_id=update.message.chat_id,
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

                        context.bot.send_message(chat_id=update.message.chat_id,
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


# =========================================
# catch netlist from a file sent to the bot
# =========================================
@block_group
def catch_netlist(update, context):
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
    file = context.bot.getFile(update.message.document.file_id)
    fname = './users/' + str(update.message.chat_id) + '.txt'
    file.download(fname)

    # send the netlist for double check to user
    mex = 'This is your netlist:\n\n'
    with open(fname) as f:
        for line in f:
            mex += line
    context.bot.send_message(chat_id=update.message.chat_id, text=mex)

    # compute solution
    net, mex = get_solution(fname, update, context)

    # typing
    context.bot.send_chat_action(chat_id=update.message.chat_id, action=telegram.ChatAction.TYPING)

    if mex is None:    # in case of .tran or .ac-multi-freq mex is none, hence send the plot
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
                         parse_mode=telegram.ParseMode.MARKDOWN, disable_web_page_preview=True)


# =========================================
# reply - catch any message and reply to it
# =========================================
@block_group
def reply(update, context):
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
        context.bot.send_chat_action(chat_id=update.message.chat_id, action=telegram.ChatAction.TYPING)

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
                             parse_mode=telegram.ParseMode.MARKDOWN)

    else:    # ironic answer if the user send a random mesage to the Bot
        update.message.reply_text("Come on! We are here to solve circuits and not to chat! 😀\n"
                                  "Please provide me a netlist.", quote=True)



# =========================================
# log - get log
# =========================================
@block_group
@restricted
def log(update, context):
    """
    'log' sends log files in the chat

    :param update: bot update
    :param context: CallbackContext
    :return: None
    """

    context.bot.send_document(chat_id=update.message.chat_id, document=open('./SolverLog.log', 'rb'))
    context.bot.send_document(chat_id=update.message.chat_id, document=open('./OtherLog.log', 'rb'))


# =========================================
# stat - get stat
# =========================================
@block_group
@restricted
def stat(update, context):
    """
    'stat' computes statistical information about the bot use

    :param update: bot update
    :param context: CallbackContext
    :return: None
    """
    context.bot.send_document(chat_id=update.message.chat_id, document=open('./StatBot.log', 'rb'))

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

    context.bot.send_message(chat_id=update.message.chat_id, text=mex,
                     parse_mode=telegram.ParseMode.MARKDOWN)


# =========================================
# send2all - send message to all users
# =========================================
@block_group
@restricted
def send2all(update, context):
    """
    'send2all' sends a message to all users

    :param update: bot update
    :param context: CallbackContext
    :return: None
    """

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
            context.bot.send_message(chat_id=chat_id,
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
            context.bot.send_message(chat_id=chat_id,
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
def send2admin(update, context):
    """
    'send2admin' sends a message to all admins

    :param update: bot update
    :param context: CallbackContext
    :return: None
    """

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
            context.bot.send_message(chat_id=chat_id,
                             text=msg,
                             parse_mode=telegram.ParseMode.MARKDOWN, disable_web_page_preview=True)

        # if the admin closed the bot don't care about the exception
        except telegram.error.TelegramError:
            pass

# =========================================
# who - retrieve user info from user id
# =========================================
@block_group
@restricted
def who(update, context):
    """
    'who' retreive user info from user id

    :param update: bot update
    :param context: CallbackContext
    :return: None
    """
    # get admin list (to send them user info)
    fid = open('./admin_only/admin_list.txt', 'r')
    ADMIN_LIST = [int(adm) for adm in fid.readline().split()]
    fid.close()
    
    # get user id provided with the command
    userID = int(update.message.text.replace('/who ','').strip())

    # get and send data
    try:
        # try to get data
        chat = context.bot.get_chat(chat_id=userID)
        # build messagge                                                                                                       update.message.from_user.last_name)
        msg = "results for userID {}:\n  * username: @{}\n  * first name: {}\n  * last name: {}\n\n".format(userID,
                                                                                        chat.username,
                                                                                        chat.first_name,
                                                                                        chat.last_name)
        # check if user has profile picture
        if hasattr(chat.photo, 'small_file_id'):
            photo = True
        else:
            photo = False
            msg += "\n\n The user has no profile picture."

        # send information
        for admin in ADMIN_LIST:
            admin_id = int(admin)
            context.bot.send_message(chat_id=admin_id, text=msg)
            if photo:
                file = context.bot.getFile(chat.photo.small_file_id)
                fname = './users/propic.png'
                file.download(fname)
                context.bot.send_photo(chat_id=admin_id, photo=open('./users/propic.png', 'rb'))
                os.remove('./users/propic.png')    
            

    # send message when user if not found
    except telegram.TelegramError:
        msg += "\n\nuser {} not found".format(userID)
        for admin in ADMIN_LIST:
            admin_id = int(admin)
            context.bot.send_message(chat_id=admin_id, text=msg)

# =========================================
# unknown - catch any wrong command
# =========================================
@block_group
def unknown(update, context):
    """
    'unknown' catch unknown commands

    :param update: bot update
    :param context: CallbackContext
    :return: None
    """
    context.bot.send_message(chat_id=update.message.chat_id, text="Sorry, I didn't understand that command.")


# =========================================
# bot - main
# =========================================
def main():
    # set TOKEN and initialization
    updater = Updater(token=TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # restart - restart the BOT
    # -------------------------
    def stop_and_restart():
        """Gracefully stop the Updater and replace the current process with a new one"""
        updater.stop()
        os.execl(sys.executable, sys.executable, *sys.argv)

    @block_group
    @restricted
    def restart(update, context):
        update.message.reply_text('Bot is restarting...')
        Thread(target=stop_and_restart).start()

    # /r - restart the bot
    dispatcher.add_handler(CommandHandler('r', restart))

    # /start handler
    start_handler = CommandHandler('start', cmd.start.execute)
    dispatcher.add_handler(start_handler)

    # catch netlist when sent to the BOT
    dispatcher.add_handler(MessageHandler(Filters.document, catch_netlist))

    # /help handler
    help_handler = CommandHandler('help', cmd.help.execute)
    dispatcher.add_handler(help_handler)

    # /netlist handler
    netlist_handler = CommandHandler('netlist', cmd.netlist.execute)
    dispatcher.add_handler(netlist_handler)

    # /complex_repr handler
    complex_repr_handler = CommandHandler('complex_repr', cmd.complex_repr.execute)
    dispatcher.add_handler(complex_repr_handler)

    # /nodal_pot handler
    nodal_pot_handler = CommandHandler('nodal_pot', cmd.nodal_pot.execute)
    dispatcher.add_handler(nodal_pot_handler)

    # /decibel handler
    decibel_handler = CommandHandler('decibel', cmd.decibel.execute)
    dispatcher.add_handler(decibel_handler)

    # /log - get log file
    dispatcher.add_handler(CommandHandler('log', log))

    # /stat - get stat file
    dispatcher.add_handler(CommandHandler('stat', stat))

    # /send2all - send message to all users
    dispatcher.add_handler(CommandHandler('send2all', send2all))

    # /send2admin - send message to all admins
    dispatcher.add_handler(CommandHandler('send2admin', send2admin))

    # /who - retrieve user info from id
    dispatcher.add_handler(CommandHandler('who', who))

    # reply to unknown commands
    unknown_handler = MessageHandler(Filters.command, unknown)
    dispatcher.add_handler(unknown_handler)

    # reply to random message or get netlist after /netlist
    reply_handler = MessageHandler(Filters.text, reply)
    dispatcher.add_handler(reply_handler)

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
