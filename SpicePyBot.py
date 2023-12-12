# general python modules
import logging
import os
# import token
from config import TOKEN
# import commands
import commands as cmd
import conversation as cnv
# PTB modules
from telegram.ext import ApplicationBuilder, CommandHandler
from telegram.ext import MessageHandler, filters

# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)

# ===============================
# create necessary folders
# ===============================
if not os.path.exists('users'):
    os.makedirs('users')

# ===========
# Define logs
# ===========
# basic (on shell)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


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
async def error_callback(update, context):
    """
    'error_callback' log uncaught error

    :param update: bot update
    :param context: CallbackContext
    :return: None
    """
    OtherLog.error("Update {} caused error {}".format(update, context.error))


# ==========
# bot - main
# ==========
def main():
    # initialize bot
    application = ApplicationBuilder().token(TOKEN).build()

    # /start handler
    start_handler = CommandHandler('start', cmd.start.execute)
    application.add_handler(start_handler)

    # catch netlist when sent to the BOT
    application.add_handler(MessageHandler(filters.Document.ALL, cnv.catch_netlist.execute))

    # /help handler
    help_handler = CommandHandler('help', cmd.help.execute)
    application.add_handler(help_handler)

    # /netlist handler
    netlist_handler = CommandHandler('netlist', cmd.netlist.execute)
    application.add_handler(netlist_handler)

    # /complex_repr handler
    complex_repr_handler = CommandHandler('complex_repr', cmd.complex_repr.execute)
    application.add_handler(complex_repr_handler)

    # /nodal_pot handler
    nodal_pot_handler = CommandHandler('nodal_pot', cmd.nodal_pot.execute)
    application.add_handler(nodal_pot_handler)

    # /decibel handler
    decibel_handler = CommandHandler('decibel', cmd.decibel.execute)
    application.add_handler(decibel_handler)

    # /log - get log file
    application.add_handler(CommandHandler('log', cmd.log.execute))

    # /stat - get stat file
    application.add_handler(CommandHandler('stat', cmd.stat.execute))

    # /send2all - send message to all users
    application.add_handler(CommandHandler('send2all', cmd.send2all.execute))

    # /send2admin - send message to all admins
    application.add_handler(CommandHandler('send2admin', cmd.send2admin.execute))

    # /who - retrieve user info from id
    application.add_handler(CommandHandler('who', cmd.who.execute))

    # catch unknown commands and notify the user
    unknown_handler = MessageHandler(filters.COMMAND, cmd.unknown.execute)
    application.add_handler(unknown_handler)

    # reply to random message or get netlist after /netlist
    reply_handler = MessageHandler(filters.TEXT, cnv.reply.execute)
    application.add_handler(reply_handler)

    # log every uncaught error with error handler
    application.add_error_handler(error_callback)

    # start the BOT
    application.run_polling()


if __name__ == '__main__':
    main()
