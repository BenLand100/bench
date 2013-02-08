############################################
# The main script for benchmarking submission
# Author: Matt Mottram 
#         m.mottram@sussex.ac.uk
############################################

import os
import json
import getpass
from base64 import b64encode
from src import Database, Macro

def create_job_card(database,doc,email_user,email_pswd,macro_name):
    '''create a job card for each job
    '''
    card_info = {}
    card_info['db_server']    = database.host
    card_info['db_name']      = database.name
    card_info['db_auth']      = b64encode('%s:%s' % (database.get_credentials()))
    card_info['email_server'] = 'smtp.gmail.com'
    card_info['email_user']   = email_user
    card_info['email_pswd']   = email_pswd
    card_info['email_list']   = [doc['email']]
    card_info['doc_id']       = doc.id
    card_info['n_events']     = 100 #always run this number of events
    card_info['root_name']    = 'bench.root' #always this output file (only ever stored in job directory)
    card_info['macro_name']   = macro_name
    return card_info
    
def submit_waiting(database,email_user,email_pswd):
    rows = database.get_waiting_tasks()
    #rows = database.get_failed_tasks()
    #rows = database.get_submitted_tasks()
    for row in rows:
        macro_name = row.value
        macro = database.get_attachment(row.id,row.value)
        can_run,macro_str,reason = Macro.verifyMacro(macro)
        if not can_run:
            print reason
        else:
            submit_job(database,row.id,row.value,macro_str,email_user,email_pswd)

def submit_job(database,jobid,macro_name,macro,email_user,email_pswd):
    doc = database.get_doc(jobid)
    jobcard = create_job_card(database,doc,email_user,email_pswd,macro_name)
    cardfile = file('job/card.json','w')
    cardfile.write(json.dumps(jobcard))
    cardfile.close()
    macrofile = file('job/macro.mac','w')
    macrofile.write(macro)
    macrofile.close()
    job = Job()
    job.application = Executable(exe=(os.path.join(os.getcwd(),'job/job.sh')))
    job.application.args = ['environment.sh','card.json','macro.mac']
    job.inputsandbox += ['job/environment.sh','job/card.json','job/macro.mac','job/benchmark.py']
    job.backend='Batch'
    job.submit()
    #json.dumps(jobcard)
    doc['state']='submitted'
    doc['fqid']=job.fqid
    database.save_doc(doc)

host = 'http://neutrino1.phys.susx.ac.uk:5984'
name = 'bench'
user = 'mjmottram'
database = Database.Database(host,name,user)
email_user = raw_input('Email address: ')
email_pswd = getpass.getpass('Email password: ')
submit_waiting(database,email_user,email_pswd)
