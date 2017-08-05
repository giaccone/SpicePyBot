# ===================
# module from SpicePy
# ===================
import netlist as ntl
import netsolve as slv
import netpost as pst
import netprint as prn

# ===================
# module of SpicePyBot
# ===================
import netprintbot as prn

# ==========================
# python-temegam-bot modules
# ==========================
from telegram.ext import Updater, MessageHandler, Filters
import telegram as telegram
from telegram.ext import CommandHandler

# ==========================
# TOKEN section
# ==========================
# The following function reads the TOKEN from a filename
# it is not incuded in the Repo for obvious reasons
def read_token(filename):
    with open(filename) as f:
        token = f.readline().replace('\n','')
    return token

# set TOKEN and initialization
fname = 'SpicePyBot_token.txt'
updater = Updater(token=read_token(fname))
dispatcher = updater.dispatcher

# ==========================
# standard logging
# ==========================
import logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',level=logging.INFO)


# ==========================
# usefult functions
# ==========================
def sove_dc_network(fname):
    net = ntl.Network(fname)
    slv.dc_solve(net)
    pst.branch_voltage(net)
    pst.branch_current(net)

    mex = prn.print_branch_quantity(net)

    return mex

# ==========================
# welcome message
# ==========================
def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id,
                     text="*Welcome to SpycePyBot*.\n\nIt allows you to solve linear networs\n(So far, only resistive netrork).\n\nRun the code:\n`/tutorial`\n to lean how to use the bot ",
                     parse_mode=telegram.ParseMode.MARKDOWN)

start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)

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

    mex = sove_dc_network(fname)
    mex = 'This is the circuit solution:\n\n' + mex

    bot.send_message(chat_id=update.message.chat_id, text=mex)

dispatcher.add_handler(MessageHandler(Filters.document, catch_netlist))



# =========================================
# Tutorial
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

    mex = 'Instruction to use the bot goes here (TO DO...)'
    bot.send_message(chat_id=update.message.chat_id, text=mex)

    mex = sove_dc_network(fname)
    mex = 'This is the circuit solution:\n\n' + mex
    bot.send_message(chat_id=update.message.chat_id, text=mex)

tutorial_handler = CommandHandler('tutorial', tutorial)
dispatcher.add_handler(tutorial_handler)


# Start the Bot
updater.start_polling()

# Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
# SIGABRT. This should be used most of the time, since start_polling() is
# non-blocking and will stop the bot gracefully.
updater.idle()
