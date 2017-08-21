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

# ==========================
# TOKEN section
# ==========================
# The following function reads the TOKEN from a file.
# This file is not incuded in the github-repo for obvious reasons
def read_token(filename):
    with open(filename) as f:
        token = f.readline().replace('\n','')
    return token

# ===============================
# global variables initialization
# ===============================
netlist_writing = 0
fid = None
polar = False

# ===============================
# admin list
# ===============================
fid = open('./admin_olny/admin_list.txt', 'r')
LIST_OF_ADMINS = [int(adm) for adm in fid.readline().split()]

# ==========================
# standard logging
# ==========================
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',level=logging.INFO)


# ==========================
# useful functions
# ==========================
def get_solution(fname, update):
    global polar

    net = ntl.Network(fname)
    net_solve(net)
    net.branch_voltage()
    net.branch_current()

    if net.analysis[0] == '.ac':
        fname = str(update.message.chat_id) + '.cnf'
        fid = open(fname, 'r')
        flag = fid.readline()
        polar = flag == 'True'
    else:
        polar = False

    mex = net.print(polar=polar, message=True).replace('==','=')

    return mex


# ==========================
# restriction decorator
# ==========================
def restricted(func):
    @wraps(func)
    def wrapped(bot, update, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in LIST_OF_ADMINS:
            print("Unauthorized access denied for {}.".format(user_id))
            return
        return func(bot, update, *args, **kwargs)
    return wrapped

# ==========================
# start - welcome message
# ==========================
def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id,
                     text="*Welcome to SpycePyBot*.\n\nIt allows you to solve linear networs\n(So far, only resistive netrork).\n\nRun the code:\n`/help`\n for the short guide.\n\nRun the code:\n`/tutorial`\n to lean how to use the bot.",
                     parse_mode=telegram.ParseMode.MARKDOWN)
    fname = str(update.message.chat_id) + '.cnf'
    fid = open(fname, 'w')
    fid.write('False')
    fid.close()


# =========================================
# catch netlist from a file sent to the bot
# =========================================
def catch_netlist(bot, update):
    file = bot.getFile(update.message.document.file_id)
    fname = str(update.message.chat_id) + '.txt'
    file.download(fname)
    mex = 'This is your netlist:\n\n'
    with open(fname) as f:
        for line in f:
            mex += line
    bot.send_message(chat_id=update.message.chat_id, text=mex)

    mex = get_solution(fname, update)
    mex = 'This is the circuit solution:\n\n' + mex

    bot.send_message(chat_id=update.message.chat_id, text=mex)


# ==========================
# help - short guide
# ==========================
def help(bot, update):
    bot.send_message(chat_id=update.message.chat_id,
                     text="*Very short guide*.\n\n1)upload a file with the netlist (don't know what a netlist is? Run `/tutorial` in the bot)\n2) enjoy\n\n\n*If you need a more detailed guide*\nRun `/tutorial` in the bot",
                     parse_mode=telegram.ParseMode.MARKDOWN)


# =========================================
# Tutorial - learn to use the bot
# =========================================
def tutorial(bot, update):
    fname = "./resources/network.net"

    bot.send_message(chat_id=update.message.chat_id, text="Let us assume to solve the following circuit:")
    bot.send_photo(chat_id=update.message.chat_id, photo=open('./resources/circ.png', 'rb'))

    mex = 'You have to write on a file the netlist describing the circuit:\n\nIt should look like the following one:\n\n'
    with open(fname) as f:
        for line in f:
            mex += line
    bot.send_message(chat_id=update.message.chat_id, text=mex)

    bot.send_chat_action(chat_id=update.message.chat_id, action=telegram.ChatAction.TYPING)
    time.sleep(8)

    mex = 'Here it is your file...'
    bot.send_message(chat_id=update.message.chat_id, text=mex)
    bot.send_photo(chat_id=update.message.chat_id, photo=open('./resources/tutorial1.png', 'rb'))

    mex = 'and its content...'
    bot.send_message(chat_id=update.message.chat_id, text=mex)
    bot.send_photo(chat_id=update.message.chat_id, photo=open('./resources/tutorial2.png', 'rb'))

    bot.send_chat_action(chat_id=update.message.chat_id, action=telegram.ChatAction.TYPING)
    time.sleep(8)

    mex = 'tap on the upload button...'
    bot.send_message(chat_id=update.message.chat_id, text=mex)
    bot.send_photo(chat_id=update.message.chat_id, photo=open('./resources/tutorial3.png', 'rb'))

    bot.send_chat_action(chat_id=update.message.chat_id, action=telegram.ChatAction.TYPING)
    time.sleep(8)

    mex = 'tap on your file...'
    bot.send_message(chat_id=update.message.chat_id, text=mex)
    bot.send_photo(chat_id=update.message.chat_id, photo=open('./resources/tutorial4.png', 'rb'))

    mex = 'check the correctenss of the netlist and enjoyt the results...'
    bot.send_message(chat_id=update.message.chat_id, text=mex)
    bot.send_photo(chat_id=update.message.chat_id, photo=open('./resources/tutorial5.png', 'rb'))


# =========================================
# netlist - write te netlist in the BOT
# =========================================
def netlist(bot, update):
    global netlist_writing
    global fid
    bot.send_message(chat_id=update.message.chat_id, text="Please write the netlist\nAll in one message.")
    netlist_writing = 1
    fid = open("netlist" + str(update.message.chat_id) + ".txt", "w")


# =========================================
# reply - catch any message and reply to it
# =========================================
def reply(bot, update):
    global netlist_writing
    if netlist_writing:
        # write the netlist
        fid.write(str(update.message.text) + '\n')
        fid.close()

        # update global variable
        netlist_writing = 0

        fname = "netlist" + str(update.message.chat_id) + ".txt"
        mex = 'This is your netlist:\n\n'
        with open(fname) as f:
            for line in f:
                mex += line
        bot.send_message(chat_id=update.message.chat_id, text=mex)

        mex = get_solution(fname, update)
        mex = 'This is the circuit solution:\n\n' + mex
        bot.send_message(chat_id=update.message.chat_id, text=mex)
    else:
        update.message.reply_text("Come on! We are here to solve circuits and not to chat! 😀\nPlease provide me a netlist.", quote=True)


# =========================================
# unknown - catch any wrong command
# =========================================
def complex_repr(bot, update):
    global polar
    if polar is True:
        polar = False
        bot.send_message(chat_id=update.message.chat_id, text="Switched to cartesian representetion")
        fname = str(update.message.chat_id) + '.cnf'
        fid = open(fname, 'w')
        fid.write('False')
        fid.close()
    else:
        polar = True
        bot.send_message(chat_id=update.message.chat_id, text="Switched to polar representetion")
        fname = str(update.message.chat_id) + '.cnf'
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
# unknown - catch any wrong command
# =========================================
def unknown(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Sorry, I didn't understand that command.")


def main():
    # set TOKEN and initialization
    fname = 'SpicePyBot_token.txt'
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

    # /tutorial handler
    tutorial_handler = CommandHandler('tutorial', tutorial)
    dispatcher.add_handler(tutorial_handler)

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
