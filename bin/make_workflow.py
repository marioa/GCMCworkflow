#!/usr/bin/env python
"""Create a GCMC workflow and stage it on launchpad

``genspec`` creates an empty specfile to fill out

``submit``  adds a Workflow to the launchpad

``list``    shows all defined workflows

specfile defines the dimensions of the GCMC sampling to perform.
lpspec defines the parameters for the job database, without this
the workflow will be submitted to the mongodb on localhost.

To execute the workflow once created, use ``rlaunch``

Usage:
  make_workflow.py genspec
  make_workflow.py submit <specfile> [-l <lpspec>] [--simple]
  make_workflow.py list
  make_workflow.py check <wfname>

Options:
  -h --help
  -v --version
  -l --launchpad  Launchpad yaml file (job database)
"""
from collections import Counter
from colorclass import Color
import docopt
import terminaltables

import gcmcworkflow as gcwf


STATUS = [
    ('READY', Color('{autowhite}W{/autowhite}')),
    ('WAITING', Color('{autowhite}W{/autowhite}')),
    ('RUNNING', Color('{autoyellow}R{/autoyellow}')),
    ('FINISHED', Color('{autogreen}F{/autogreen}')),
    ('FIZZLED', Color('{autored}X{/autored}')),
]

def build_table(status):
    # generate the table
    print(status)
    status[80.0, 200.0] = ['READY', 'FINISHED', 'FIZZLED']

    table = [['Temperature', 'Pressure', 'Status']]
    prev_T = None
    for (T, P), v in sorted(status.items(), key=lambda x: (float(x[0][0]), float(x[0][1]), x[1])):
        Tcol = T if T != prev_T else ''

        status = ''
        statcount = Counter(v)
        print(statcount)
        for cat, entry in STATUS:
            status += entry * statcount[cat]
        print(status)
        table.append([Tcol, P, status])

    return terminaltables.SingleTable(table).table


if __name__ == '__main__':
    args = docopt.docopt(__doc__, version=gcwf.__version__)

    if args['genspec']:
        gcwf.spec_parser.generate_spec()
    elif args['submit']:
        specs = gcwf.read_spec(args['<specfile>'])
        wf = gcwf.make_workflow(specs) #, simple=args['--simple'])

        gcwf.launchpad_utils.submit_workflow(wf, lpspec=args['<lpspec>'])
    elif args['list']:
        names = gcwf.launchpad_utils.get_workflow_names(lpspec=args['<lpspec>'])

        print(names)
    elif args['check']:
        stat = gcwf.launchpad_utils.get_workflow_report(
            args['<wfname>'], lpspec=args['<lpspec>'])

        print(build_table(stat))
