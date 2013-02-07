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

def create_job_card(database,doc):
    '''create a job card for each job
    '''
    card_info = {}
    card_info['db_server']    = database.host
    card_info['db_name']      = database.name
    card_info['db_auth']      = b64encode('%s:%s' % (database.get_credentials()))
    card_info['email_server'] = 'smtp.gmail.com'
    card_info['email_user']   = raw_input('gmail username:')
    card_info['email_pswd']   = getpass.getpass('gmail password')
    card_info['email_list']   = [doc.email]
    card_info['doc_id']       = doc.id
    card_info['n_events']     = 100 #always run this number of events
    card_info['root_name']    = 'bench.root' #always this output file (only ever stored in job directory)
    return card_info
    
def submit_waiting(database):
    rows = database.get_waiting_tasks()
    for row in rows:
        macro = database.get_attachment(row.id,row.value)
        can_run,reason = Macro.verifyMacro(macro)
        if not can_run:
            print reason
        else:
            submit_job(database,row.id,macro)

def submit_job(database,jobid,macro):
    doc = database.get_doc(jobid)
    jobcard = create_job_card(database,doc)
    cardfile = file('job/card.json','w')
    cardfile.write(json.dumps(jobcard))
    cardfile.close()
    j = Job()
    j.application = Executable(exe=(os.path.join(os.getcwd(),'job/job.sh')))
    j.application.args = ['environment.sh','card.json',macro_name]
    j.backend='Batch'
    j.submit()
    #json.dumps(jobcard)
    doc['status']='submitted'
    doc['fqid']=job.fqid
    database.save_doc(doc)

host = 'http://127.0.0.1:5984'
name = 'bench'
user = 'mjmottram'
database = Database.Database(host,name,user)
submit_waiting(database)
