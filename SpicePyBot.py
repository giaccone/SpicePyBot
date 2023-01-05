# general python modules
import logging
import os
# import token
from config import TOKEN
# import commands
import commands as cmd
import conversation as cnv
# PTB modules
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

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


# =========================================
# bot - main
# =========================================
def main():
    # set TOKEN and initialization
    updater = Updater(token=TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # /start handler
    start_handler = CommandHandler('start', cmd.start.execute)
    dispatcher.add_handler(start_handler)

    # catch netlist when sent to the BOT
    dispatcher.add_handler(MessageHandler(Filters.document, cnv.catch_netlist.execute))

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
    dispatcher.add_handler(CommandHandler('log', cmd.log.execute))

    # /stat - get stat file
    dispatcher.add_handler(CommandHandler('stat', cmd.stat.execute))

    # /send2all - send message to all users
    dispatcher.add_handler(CommandHandler('send2all', cmd.send2all.execute))

    # /send2admin - send message to all admins
    dispatcher.add_handler(CommandHandler('send2admin', cmd.send2admin.execute))

    # /who - retrieve user info from id
    dispatcher.add_handler(CommandHandler('who', cmd.who.execute))

    # reply to unknown commands
    unknown_handler = MessageHandler(Filters.command, cmd.unknown.execute)
    dispatcher.add_handler(unknown_handler)

    # reply to random message or get netlist after /netlist
    reply_handler = MessageHandler(Filters.text, cnv.reply.execute)
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
