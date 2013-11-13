import os
import sys
import threading
import logging
 
sys.path.append(os.path.split(os.getcwd())[0])
sys.path.append(os.getcwd())
 
from AVCommon.mq import MQStar
from av_machine import AVMachine
from AVCommon import command

commands = ["EVAL_SERVER"]
 
class Dispatcher(object):
    """docstring for Dispatcher"""
 
    vms = []
    def __init__(self, mq, vms, report=None, timeout=0):
        self.vms = vms
        self.mq = mq
        self.report = report
        self.timeout = timeout
 
    def dispatch(self, procedure, ):
        global received
        exit = False

        procedure.add_begin_end()

        logging.debug("- SERVER len(procedure): %s"% len(procedure))
        self.num_commands = len(procedure)

        av_machines = {}
        for c in self.vms:
            av_machines[c] = AVMachine(self.mq, c, procedure)
 
        for a in av_machines.values():
            #a.start()
            self.mq.clean(a)
            r, c = a.execute_next_command()
            if self.report:
                self.report.sent(a.name, str(c))
            logging.debug("- SERVER SENT: %s" % c)
 
        ended = 0
        answered = 0
        while not exit and ended < len(self.vms):
            rec = self.mq.receive_server(blocking=True, timeout=self.timeout)
            if rec is not None:
                logging.debug("- SERVER RECEIVED %s %s" % (rec, type(rec)))
                c, msg = rec
                m = av_machines[c]
                answer = m.manage_answer(msg)
                if self.report:
                    self.report.received(c, msg)
                answered += 1
                #logging.debug("- SERVER RECEIVED ANSWER: %s" % answer.success)
                if answer.name == "END":
                    ended += 1
                    logging.debug("- SERVER RECEIVE END")
                elif answer.success:
                    r, cmd = av_machines[c].execute_next_command()
                    if self.report:
                        self.report.sent(a.name, str(cmd))
                    logging.debug("- SERVER SENT: %s, %s" % (c, cmd))
                else:
                    ended += 1
                    logging.debug("- SERVER RECEIVE ERROR, ENDING")
 
            else:
                logging.debug("- SERVER RECEIVED empty")
                exit = True
 
        logging.debug("answered: %s, ended: %s, num_commands: %s" %( answered, ended, self.num_commands))
        assert (ended == len(self.vms))
        #assert answered >= (len(self.vms) * (self.num_commands)), "answered: %s, len(vms): %s, num_commands: %s" % (answered , len(self.vms), self.num_commands)
        return answered