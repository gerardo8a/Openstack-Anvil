# vim: tabstop=4 shiftwidth=4 softtabstop=4

#    Copyright (C) 2012 Yahoo! Inc. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import json
import re
import time

from devstack import exceptions as excp
from devstack import log as logging
from devstack import settings
from devstack import shell as sh
from devstack import trace as tr
from devstack import utils

LOG = logging.getLogger("devstack.runners.screen")

#my type
RUN_TYPE = settings.RUN_TYPE_SCREEN
TYPE = settings.RUN_TYPE_TYPE

#trace constants
SCREEN_TEMPL = "%s.screen"
ARGS = "ARGS"
NAME = "NAME"

#screen session name
SESSION_NAME = 'stack'
SESSION_NAME_MTCHER = re.compile(r"^\s*([\d]+\.%s)\s*(.*)$" % (SESSION_NAME))

#how we setup screens status bar
STATUS_BAR_CMD = r'hardstatus alwayslastline "%-Lw%{= BW}%50>%n%f* %t%{-}%+Lw%< %= %H"'

#cmds
SESSION_INIT = ['screen', '-d', '-m', '-S', SESSION_NAME, '-t', SESSION_NAME, '-s', "/bin/bash"]
BAR_INIT = ['screen', '-r', SESSION_NAME, '-X', STATUS_BAR_CMD]
CMD_INIT = ['screen', '-S', SESSION_NAME, '-X', 'screen', '-t', "%NAME%"]
CMD_START = ['screen', '-S', SESSION_NAME, '-p', "%NAME%", '-X', 'stuff', "\"%CMD%\r\""]

#screen rc file created
RC_FILE = 'stack-screenrc'

#used to wait until started before we can run the actual start cmd
WAIT_ONLINE_TO = settings.WAIT_ALIVE_SECS

ALREADY_GOIN_MSG = [
                    "You are already running a stack screen session.",
                    "To rejoin this session type 'screen -x %s'." % (SESSION_NAME),
                    "To destroy this session, kill the running screen.",
                   ]


class ScreenRunner(object):
    def __init__(self, cfg):
        self.cfg = cfg

    def stop(self, name, *args, **kargs):
        msg = "Not implemented yet"
        raise NotImplementedError(msg)

    def _check_start(self):
        screen_list_cmd = ['screen', '-ls']
        (sysout, _) = sh.execute(screen_list_cmd, check_exit_code=False)
        for line in sysout.splitlines():
            if SESSION_NAME_MTCHER.match(line):
                msg = utils.joinlinesep(*ALREADY_GOIN_MSG)
                raise excp.StartException(msg)

    def _do_screen_init(self):
        sh.execute(*SESSION_INIT, shell=True)
        time.sleep(WAIT_ONLINE_TO)
        sh.execute(*BAR_INIT, shell=True)

    def _do_start(self, name, cmd):
        init_cmd = list()
        mp = dict()
        mp['NAME'] = name
        mp['CMD'] = " ".join(cmd)
        for piece in CMD_INIT:
            init_cmd.append(utils.param_replace(piece, mp))
        sh.execute(*init_cmd, shell=True)
        time.sleep(WAIT_ONLINE_TO)
        start_cmd = list()
        for piece in CMD_START:
            start_cmd.append(utils.param_replace(piece, mp))
        sh.execute(*start_cmd, shell=True)

    def _start(self, name, program, *program_args, **kargs):
        self._check_start()
        tracedir = kargs["trace_dir"]
        fn_name = SCREEN_TEMPL % (name)
        tracefn = tr.touch_trace(tracedir, fn_name)
        runtrace = tr.Trace(tracefn)
        runtrace.trace(TYPE, RUN_TYPE)
        runtrace.trace(NAME, name)
        runtrace.trace(ARGS, json.dumps(program_args))
        full_cmd = [program] + list(program_args)
        self._do_screen_init()
        self._do_start(name, full_cmd)
        return tracefn

    def start(self, name, program, *program_args, **kargs):
        return self._start(name, program, *program_args, **kargs)
