############################################
# The main script for benchmarking submission
# Author: Matt Mottram 
#         m.mottram@sussex.ac.uk
############################################

import os
import sys
import json
import getpass
import smtplib
import optparse
from base64 import b64encode
from src import Database, Macro, BenchConfig
from GangaSNOplus.Lib import RATUtil

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
    card_info['n_events']     = 1000 #always run this number of events
    card_info['root_name']    = 'bench.root' #always this output file (only ever stored in job directory)
    card_info['macro_name']   = macro_name
    if 'commitHash' in doc:
        card_info['commit_hash'] = doc['commitHash']
    return card_info
    
def submit_waiting(database,config):
    rows = database.get_waiting_tasks()
    for row in rows:
        macro_name = row.value
        macro = database.get_attachment(row.id,row.value)
        can_run,macro_str,reason = Macro.verifyMacro(macro)
        if not can_run:
            print reason
        else:
            submit_job(database,row.id,row.value,macro_str,config)

def write_job_environment(envName,swDir,ratVersion,commitHash=None,envFile=None):
    #create an environment file to use and ship with the job
    rat_env_file = os.path.join(swDir,'env_rat-%s.sh'%ratVersion)
    local_env = ''
    job_env = ''
    fout = file(envName,'w')
    if not os.path.exists(rat_env_file):
        error = 'RAT environment file not found: %s'%(rat_env_file)
        raise Exception,error
    rat_env_lines = file(rat_env_file,'r').readlines()
    if envFile:
        if not os.path.exists(envFile):
            error = 'Local environment file not found: %s'%(envFile)
            raise Exception,error
        temp = file(envFile,'r').readlines()        
        for temp_line in temp:
            line = temp_line.strip()
            if line!='' and line==None:
                local_env += temp_line
    if commitHash==None:
        #just need the basic rat env file, plus extras to work on feynman
        job_env += '#!/bin/bash -l\n'
        job_env += local_env
        for line in rat_env_lines:
            job_env += line
    else:
        #need to configure the shipped snapshot
        job_env += '#!/bin/bash -l\n'
        job_env += local_env
        for line in rat_env_lines[:-1]:
            #skip the last line - sourcing the rat/env.sh
            job_env += line
        job_env += 'jobdir=$(pwd)\n'
        job_env += 'tar -zxvf rat.*\n'
        job_env += 'cd rat\n'
        job_env += './configure\n'
        job_env += 'source env.sh\n'
        job_env += 'scons\n'
        job_env += 'cd ${jobdir}\n'
    fout.write(job_env)
    fout.close()

def submit_job(database,jobid,macro_name,macro,config):
    doc = database.get_doc(jobid)
    jobcard = create_job_card(database,doc,config.email_address,config.email_password,macro_name)
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
    if 'commitHash' in doc:
        commitHash = doc['commitHash']
    ratVersion = str(doc['ratVersion'])
    #get the job environment and write a temp file for it
    temp_env_name = 'temp_job_env.sh'
    write_job_environment(temp_env_name,config.sw_directory,ratVersion,commitHash,config.env_file)
    if 'commitHash' in doc:
        zipFileName = RATUtil.MakeRatSnapshot(commitHash,'rat/',os.path.expanduser('~/gaspCache'))
        print zipFileName,type(zipFileName)
        zipFileName = str(zipFileName)
        print zipFileName,type(zipFileName)
        job.inputsandbox += [temp_env_name,'job/card.json','job/macro.mac','job/benchmark.py',zipFileName]
    else:
        job.inputsandbox += [temp_env_name,'job/card.json','job/macro.mac','job/benchmark.py']
    job.application.args = [temp_env_name.split('/')[-1],'card.json','macro.mac']
    job.submit()
    #json.dumps(jobcard)
    doc['info'][macro_name]['state']='submitted'
    doc['info'][macro_name]['fqid']=job.fqid
    database.save_doc(doc)

def check_old(database,config):
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
                sendEmail('smtp.gmail.com',config.email_address,config.email_password,[doc['email']],email)
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
    parser.add_option('-a',dest='email_address',help='Email address')
    parser.add_option('-x',dest='email_password',help='Email password',default=None)
    parser.add_option('-w',dest='sw_directory',help='Snoing install directory')
    parser.add_option('-e',dest='env_file',help='Extra environment required for backend',default=None)
    (options, args) = parser.parse_args()
    config = BenchConfig.BenchConfig()
    if options.config:
        config.read_config(options.config)
    else:
        config.parse_options(options)
    database = Database.Database(config.db_server,config.db_name,
                                 config.db_user,config.db_password)
    try:
        emailCheck('smtp.gmail.com',config.email_address,config.email_password)
    except:
        raise Exception,'Bad email password'
    check_old(database,config)
    submit_waiting(database,config)
