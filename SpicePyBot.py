# ======================
# general python modules
# ======================
import time
import logging
from functools import wraps
import os
import sys

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
# standard logging
# ==========================
logging.basicConfig(filename='SpicePyBot.log', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',level=logging.INFO)


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
def get_solution(fname, update):
    """
    'get_solution' computes the solution of a network using SpicePy

    :param fname: filename with the netlist
    :param update: Bot updater
    :return:
        * mex:  solution formatted in a string
    """
    try:
        global polar

        net = ntl.Network(fname)
        net_solve(net)
        net.branch_voltage()
        net.branch_current()

        if net.analysis[0] == '.ac':
            fname = './users/' + str(update.message.chat_id) + '.cnf'
            fid = open(fname, 'r')
            flag = fid.readline()
            polar = flag == 'True'
        else:
            polar = False

        mex = net.print(polar=polar, message=True)
        mex = mex.replace('==============================================\n'
                          '               branch quantities'
                          '\n==============================================\n', '*branch quantities*\n`')
        mex = mex.replace('----------------------------------------------', '')
        mex += '`'

        # Log every time a network is solved
        # To make stat it is saved the type of network and the UserID
        logging.info('Analysis: ' + net.analysis[0] + ' - UserID: ' + str(update.effective_user.id))

        return mex

    except:
        logging.error('Netlist_Error - UserID: ' + str(update.effective_user.id))
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
    msg += "  \* DC networks\n"
    msg += "  \* AC networks\n\n"
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

    file = bot.getFile(update.message.document.file_id)
    fname = './users/' + str(update.message.chat_id) + '.txt'
    file.download(fname)
    mex = 'This is your netlist:\n\n'
    with open(fname) as f:
        for line in f:
            mex += line
    bot.send_message(chat_id=update.message.chat_id, text=mex)

    mex = get_solution(fname, update)
    mex = 'This is the circuit solution:\n\n' + mex

    bot.send_message(chat_id=update.message.chat_id, text=mex, parse_mode=telegram.ParseMode.MARKDOWN)


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
    if os.path.exists("./users/" + str(update.message.chat_id) + "_waitnetlist"):
        # write the netlist
        fid = open("./users/" + str(update.message.chat_id) + ".txt", "w")
        fid.write(str(update.message.text) + '\n')
        fid.close()

        # remove waitnetlist file for this user
        os.remove("./users/" + str(update.message.chat_id) + "_waitnetlist")

        fname = "./users/" + str(update.message.chat_id) + ".txt"
        mex = 'This is your netlist:\n\n'
        with open(fname) as f:
            for line in f:
                mex += line
        bot.send_message(chat_id=update.message.chat_id, text=mex)

        mex = get_solution(fname, update)
        mex = 'This is the circuit solution:\n\n' + mex
        bot.send_message(chat_id=update.message.chat_id, text=mex,
                         parse_mode=telegram.ParseMode.MARKDOWN)
    else:
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
# log - restart the BOT
# =========================================
@restricted
def log(bot, update):
    bot.send_document(chat_id=update.message.chat_id, document=open('./SpicePyBot.log', 'rb'))


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
