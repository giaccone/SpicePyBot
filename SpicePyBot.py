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
# global variables initialization
# ===============================
polar = False

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

# stat log
logINFO = logging.getLogger('logINFO')
h1 = logging.FileHandler('StatBot.log')
h1.setFormatter(fmt)
logINFO.addHandler(h1)
logINFO.setLevel(logging.INFO)
logINFO.addFilter(MyFilter(logging.INFO))

# standard log >= WARNING
std_log = logging.getLogger('std_log')
h2 = logging.FileHandler('SpicePyBot.log')
h2.setFormatter(fmt)
std_log.addHandler(h2)

# ==========================
# useful functions
# ==========================
# The following function reads the TOKEN from a file.
# This file is not incuded in the github-repo for obvious reasons
def read_token(filename):
    with open(filename) as f:
        token = f.readline().replace('\n', '')
    return token


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
        global polar

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
            if net.analysis[0] == '.tran':
                Nsamples = float(net.analysis[2]) / float(net.analysis[1])
                if Nsamples > 2000:
                    step = float(net.analysis[2])/1999
                    net.analysis[1] = '{:.3e}'.format(step)

                    mex = "Your netlits defines a '.tran' analysis with *{:d}* samples\n".format(int(Nsamples))
                    mex += "Since this bot runs on a limited hardware shared by many users\n"
                    mex += "The analysis has been limited to *2000* samples:\n"
                    mex += "`.tran " + net.analysis[1] + " " + net.analysis[-1] + "`"


                    bot.send_message(chat_id=update.message.chat_id,
                                     text=mex,
                                     parse_mode=telegram.ParseMode.MARKDOWN)
            # solve the network
            net_solve(net)

            # excluding transient analysis, compute branch quantities
            if net.analysis[0].lower() != '.tran':
                net.branch_voltage()
                net.branch_current()
                net.branch_power()

            # get configurations for '.ac' problems
            if net.analysis[0] == '.ac':
                fname = './users/' + str(update.message.chat_id) + '.cnf'
                fid = open(fname, 'r')
                flag = fid.readline()
                polar = flag == 'True'
            else:
                polar = False

            # excluding transient analysis, prepare mex to be printed
            if net.analysis[0].lower() != '.tran':
                mex = net.print(polar=polar, message=True)
                mex = mex.replace('==============================================\n'
                                  '               branch quantities'
                                  '\n==============================================\n', '*branch quantities*\n`')
                mex = mex.replace('----------------------------------------------', '')
                mex += '`'
            elif net.analysis[0].lower() == '.tran':
                hf = net.plot(to_file=True, filename='./users/tran_plot_' + str(update.message.chat_id) + '.png',dpi_value=150)
                mex = None
                plt.close(hf)

            # Log every time a network is solved
            # To make stat it is saved the type of network and the UserID
            logINFO.info('Analysis: ' + net.analysis[0] + ' - UserID: ' + str(update.effective_user.id))

        return mex

    except:
        std_log.error('Netlist_Error - UserID: ' + str(update.effective_user.id))
        return "*Something went wrong with your netlist*.\nPlease check the netlist format."


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
# start - welcome message
# ==========================
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
    fid.write('False')
    fid.close()


# =========================================
# catch netlist from a file sent to the bot
# =========================================
def catch_netlist(bot, update):

    # if current user don't have cnf file create it
    if not os.path.exists('./users/' + str(update.message.chat_id) + '.cnf'):
        fname = './users/' + str(update.message.chat_id) + '.cnf'
        fid = open(fname, 'w')
        fid.write('False')
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
    mex = get_solution(fname, bot, update)

    # typing
    bot.send_chat_action(chat_id=update.message.chat_id, action=telegram.ChatAction.TYPING)

    if mex is None:    # in case of .tran mex is none, hence send the plot
        bot.send_photo(chat_id=update.message.chat_id,
                       photo=open('./users/tran_plot_' + str(update.message.chat_id) + '.png', 'rb'))

    else:    # otherwise print results
        mex = 'This is the circuit solution:\n\n' + mex
        bot.send_message(chat_id=update.message.chat_id, text=mex,
                         parse_mode=telegram.ParseMode.MARKDOWN, disable_web_page_preview=True)


# ==========================
# help - short guide
# ==========================
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
def netlist(bot, update):

    # if current user don't have cnf file create it
    if not os.path.exists('./users/' + str(update.message.chat_id) + '.cnf'):
        fname = './users/' + str(update.message.chat_id) + '.cnf'
        fid = open(fname, 'w')
        fid.write('False')
        fid.close()

    open("./users/" + str(update.message.chat_id) + "_waitnetlist", 'w').close()
    bot.send_message(chat_id=update.message.chat_id, text="Please write the netlist\nAll in one message.")


# =========================================
# reply - catch any message and reply to it
# =========================================
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
        mex = get_solution(fname, bot, update)

        # typing
        bot.send_chat_action(chat_id=update.message.chat_id, action=telegram.ChatAction.TYPING)

        if mex is None:    # in case of .tran mex is none, hence send the plot
            bot.send_photo(chat_id=update.message.chat_id, photo=open('./users/tran_plot_' + str(update.message.chat_id) + '.png', 'rb'))

        else:    # otherwise print results
            mex = 'Please consider that all components are analyzed with *passive sign convention* reading' \
                  '*the circuit solution*.\n\n' + mex
            bot.send_message(chat_id=update.message.chat_id, text=mex,
                             parse_mode=telegram.ParseMode.MARKDOWN)

    else:    # ironic answer if the user send a random mesage to the Bot
        update.message.reply_text("Come on! We are here to solve circuits and not to chat! 😀\n"
                                  "Please provide me a netlist.", quote=True)


# =========================================
# unknown - catch any wrong command
# =========================================
def complex_repr(bot, update):
    global polar
    if polar is True:
        polar = False
        bot.send_message(chat_id=update.message.chat_id, text="Switched to cartesian representation")
        fname = './users/' + str(update.message.chat_id) + '.cnf'
        fid = open(fname, 'w')
        fid.write('False')
        fid.close()
    else:
        polar = True
        bot.send_message(chat_id=update.message.chat_id, text="Switched to polar representation")
        fname = './users/' + str(update.message.chat_id) + '.cnf'
        fid = open(fname, 'w')
        fid.write('True')
        fid.close()


# =========================================
# restart - restart the BOT
# =========================================
@restricted
def restart(bot, update):
    bot.send_message(update.message.chat_id, "Bot is restarting...")
    time.sleep(0.2)
    os.execl(sys.executable, sys.executable, *sys.argv)


# =========================================
# log - get log
# =========================================
@restricted
def log(bot, update):
    bot.send_document(chat_id=update.message.chat_id, document=open('./SpicePyBot.log', 'rb'))


# =========================================
# stat - get stat
# =========================================
@restricted
def stat(bot, update):
    bot.send_document(chat_id=update.message.chat_id, document=open('./StatBot.log', 'rb'))


# =========================================
# unknown - catch any wrong command
# =========================================
def unknown(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Sorry, I didn't understand that command.")


def main():
    # set TOKEN and initialization
    fname = './admin_only/SpicePyBot_token.txt'
    updater = Updater(token=read_token(fname))
    dispatcher = updater.dispatcher

    # /start handler
    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)

    # chatch netlist when sent to the BOT
    dispatcher.add_handler(MessageHandler(Filters.document, catch_netlist))

    # /help handler
    help_handler = CommandHandler('help', help)
    dispatcher.add_handler(help_handler)

    # /netlist handler
    netlist_handler = CommandHandler('netlist', netlist)
    dispatcher.add_handler(netlist_handler)

    # reply to random message
    reply_handler = MessageHandler(Filters.text, reply)
    dispatcher.add_handler(reply_handler)

    # /complex_repr handler
    complex_repr_handler = CommandHandler('complex_repr', complex_repr)
    dispatcher.add_handler(complex_repr_handler)

    # /r - restart the bot
    dispatcher.add_handler(CommandHandler('r', restart))

    # /log - get log file
    dispatcher.add_handler(CommandHandler('log', log))

    # /log - get stat file
    dispatcher.add_handler(CommandHandler('stat', stat))

    # reply to unknown commands
    unknown_handler = MessageHandler(Filters.command, unknown)
    dispatcher.add_handler(unknown_handler)

    # start the BOT
    updater.start_polling()
    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()
