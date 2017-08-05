def print_branch_quantity(net):
    """
    'print_branch_quantity' prepare a message to be sent on a chat by the SpycePyBot

    """

    # if necessary reorder
    if net.isort is None:
        net.reorder()

    mex = '==============================\n'
    mex += '         branch quantities\n'
    mex += '==============================\n'

    for k, index in enumerate(net.isort):
        if k == 0: # resistors
            for h in index:
                mex += 'v({}) = {:6.3f} V    '.format(net.names[h], net.vb[h])
                mex += 'i({}) = {:6.3f} A\n'.format(net.names[h], net.ib[h])
        elif k == 1: # voltage sources
            for h in index:
                mex += 'v({}) = {:6.3f} V    '.format(net.names[h], net.vb[h])
                mex += 'i({}) = {:6.3f} A\n'.format(net.names[h], net.ib[h])
        elif k == 2: # current sources
            for h in index:
                mex += 'v({}) = {:6.3f} V    '.format(net.names[h], net.vb[h])
                mex += 'i({}) = {:6.3f} A\n'.format(net.names[h], net.ib[h])
                mex += '==============================\n'

    return mex
