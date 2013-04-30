############################################
# The main script for benchmarking submission
# Author: Matt Mottram 
#         m.mottram@sussex.ac.uk
############################################

import os
import json
import getpass
import smtplib
from base64 import b64encode
from src import Database, Macro, Config
from GangaSNO.Lib import RATUtil

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
    if 'commitHash' in doc:
        card_info['commit_hash'] = doc['commitHash']
    return card_info
    
def submit_waiting(database,email_user,email_pswd):
    rows = database.get_waiting_tasks()
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
    job.backend='Batch'
    job.application = Executable(exe=(os.path.join(os.getcwd(),'job/job.sh')))
    commitHash = None
    ratVersion = str(doc['ratVersion'])
    if 'commitHash' in doc:
        commitHash = doc['commitHash']
        zipFileName = RATUtil.MakeRatSnapshot(commitHash,'rat/',os.path.expanduser('~/gaspCache'))
        print zipFileName,type(zipFileName)
        zipFileName = str(zipFileName)
        print zipFileName,type(zipFileName)
        job.application.args = ['environment_dev.sh','%s.dev'%(ratVersion),'card.json','macro.mac']
        job.inputsandbox += ['job/environment_dev.sh','job/card.json','job/macro.mac','job/benchmark.py','job/env_rat-%s.dev.sh'%(ratVersion),zipFileName]
    else:
        job.application.args = ['environment_fix.sh','%s'%(ratVersion),'card.json','macro.mac']
        job.inputsandbox += ['job/environment_fix.sh','job/card.json','job/macro.mac','job/benchmark.py','job/env_rat-%s.sh'%(ratVersion)]
    job.submit()
    #json.dumps(jobcard)
    doc['info'][macro_name]['state']='submitted'
    doc['info'][macro_name]['fqid']=job.fqid
    database.save_doc(doc)

def check_old(database,email_user,email_pswd):
    rows = database.get_submitted_tasks()
    for row in rows:
        try:
            doc = database.get_doc(row.id)
            macro_name = row.value
            fqid = int(doc['info'][macro_name]['fqid'])
            j = jobs(fqid)
        except:
            print 'no job with that fqid',fqid,type(fqid),'setting status to failed'
            doc['info'][macro_name]['state']='waiting'
            database.save_doc(doc)
            continue
        if True:
            if j.status=='failed':
                email = ''
                email += 'Results for job %s/_utils/database.html?%s/%s: \n'%(database.host,database.name,row.id)
                email += 'Macro: %s \n'%macro_name
                email += 'Job failed\n'
                errPath = os.path.join(j.outputdir,'stderr')
                outPath = os.path.join(j.outputdir,'stdout')
                if os.path.exists(errPath):
                    email += '\nError:\n'
                    for line in file(errPath,'r').readlines():
                        try:
                            email += line
                        except:
                            pass
                if os.path.exists(outPath):
                    email += '\nOutput:\n:'
                    #only want the last 30 lines max
                    lines = file(outPath,'r').readlines()
                    nlines = len(lines)
                    for i,line in enumerate(lines):
                        if (i+30)>nlines:
                            email += line
                if not os.path.exists(errPath) and not os.path.exists(outPath):
                    email += '\nNo output records!'
                sendEmail('smtp.gmail.com',email_user,email_pswd,[doc['email']],email)
                doc['info'][row.value]['state']='failed'
                database.save_doc(doc)
                jobs(fqid).remove()

def emailCheck(mailServer,mailUser,mailPass=None):
    '''Just check we can login'''
    if mailPass==None:
        getpass.getpass('Email password: ')
    if mailServer == 'smtp.gmail.com':
        port = 587
        smtp = smtplib.SMTP(mailServer,port)
    else:
        smtp = smtplib.SMTP(mailServer)
    if mailUser and mailPass:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(mailUser,mailPass)
        
def sendEmail(mailServer,mailUser,mailPass,mailList,body):
    subject = 'Benchmarking results'
    message = ''
    message += 'From: %s\r\n' % mailUser
    message += 'To: %s\r\n' % ', '.join(mailList)
    message += 'Subject: %s\r\n\r\n' % subject
        #if there is email to send, do it
    message += '%s\n'%body
    if mailServer == 'smtp.gmail.com':
        port = 587
        smtp = smtplib.SMTP(mailServer,port)
    else:
        smtp = smtplib.SMTP(mailServer)
    if mailUser and mailPass:    
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(mailUser,mailPass)
    print message
    smtp.sendmail(mailUser,mailList,message)

if __name__=="__main__":
    parser = optparse.OptionParser()
    parser.add_option('-c',dest='config',help="Specify path to config file (overrides other options)")
    parser.add_option('-s',dest='db_server',help='Database server')
    parser.add_option('-n',dest='db_name',help='Database name')
    parser.add_option('-u',dest='db_user',help='Database user')
    parser.add_option('-p',dest='db_password',help='Database password',default=None)
    parser.add_option('-e',dest='email_address',help='Email address')
    parser.add_option('-x',dest='email_password',help='Email password',default=None)
    (options, args) = parser.parse_args()
    config = Config.Config()
    if options.config:
        config_options = config.read_config(options.config)
    else:
        config_options = config.parse_options(options)
    database = Database.Database(config_options.db_server,config_options.db_name,
                                 config_options.db_user,config_options.db_password)
    try:
        emailCheck('smtp.gmail.com',email_user,email_password)
    except:
        raise Exception,'Bad email password'
    check_old(database,email_user,email_password)
    submit_waiting(database,email_user,email_password)
