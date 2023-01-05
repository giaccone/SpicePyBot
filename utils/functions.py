import spicepy.netlist as ntl
from spicepy.netsolve import net_solve
from telegram import ParseMode
import numpy as np
import matplotlib.pyplot as plt
import logging
import matplotlib
matplotlib.use('Agg')


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
                                     parse_mode=ParseMode.MARKDOWN)

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
                                         parse_mode=ParseMode.MARKDOWN)

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
            StatLog = logging.getLogger('StatLog')
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
        SolverLog = logging.getLogger('SolverLog')
        SolverLog.error('UserID: ' + str(update.effective_user.id) + ' - Netlist error: ' + wrong_net)
        return net, "*Something went wrong with your netlist*.\nPlease check the netlist format."
