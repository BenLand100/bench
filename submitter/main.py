############################################
# The main script for benchmarking submission
# Author: Matt Mottram 
#         m.mottram@sussex.ac.uk
############################################

import os
import sys
import json
import time
import getpass
import smtplib
import optparse
import cmdexec
from base64 import b64encode
from src import Database, Macro, BenchConfig
from GangaSNOplus.Lib import RATUtil
from Ganga import Core


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
    card_info['rat_version']  = str(doc['ratVersion'])
    card_info['doc_id']       = doc.id
    card_info['n_events']     = 1000 #always run this number of events
    card_info['root_name']    = 'bench' #always this output file (only ever stored in job directory)
    card_info['macro_name']   = macro_name
    if 'commitHash' in doc:
        card_info['commit_hash'] = doc['commitHash']
    return card_info

def create_test_card(doc):
    '''create a card for testing mode
    '''
    card_info = {}
    card_info['test_mode']    = True
    card_info['rat_version']  = str(doc['ratVersion'])
    card_info['n_events']     = 10 #always run this number of events
    card_info['root_name']    = 'bench' #always this output file (only ever stored in job directory)
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

def submit_test(version, commitHash=None):
    # Create a moc document, include the testing macro
    doc = {}
    doc['ratVersion'] = version
    macro = open('test/macro.mac', 'r')
    jobcard = create_test_card(doc)
    cardfile = file('job/card.json','w')
    cardfile.write(json.dumps(jobcard))
    cardfile.close()
    macrofile = file('job/macro.mac','w')
    macrofile.write(macro.read())
    macrofile.close()
    job = Job()
    job.backend='Batch'
    job.application = Executable(exe=(os.path.join(os.getcwd(),'job/job.sh')))
    if commitHash is not None:
        doc['commitHash'] = commitHash
    ratVersion = str(doc['ratVersion'])
    #get the job environment and write a temp file for it
    job_env = get_env_path(config.sw_directory, ratVersion)
    if 'commitHash' in doc:
        job_env = install_snapshot(config, ratVersion, commitHash)
    job.inputsandbox += ['job/card.json', 'job/macro.mac', 'job/benchmark.py']
    job.application.args = [job_env, 'card.json', 'macro.mac']
    job.submit()
    

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
        for i, temp_line in enumerate(temp):
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
        for i, line in enumerate(rat_env_lines):
            #skip the last line - sourcing the rat/env.sh
            if i==len(rat_env_lines)-1 or i==len(rat_env_lines)-2:
                if 'source' in line:
                    continue
            job_env += line
        job_env += 'jobdir=$(pwd)\n'
        # Untar to a known dir name!
        job_env += 'mkdir rat \n'
        job_env += 'tar -zxf rat.* -C rat --strip-components 1 \n'
        job_env += 'cd rat\n'
        job_env += './configure\n'
        job_env += 'source env.sh\n'
        job_env += 'scons\n'
        job_env += 'cd ${jobdir}\n'
    fout.write(job_env)
    fout.close()

def install_snapshot(config, rat_version, commit_hash):
    '''Download a RAT snapshot, install to a common area for all jobs to use.
    '''
    zip_name = RATUtil.MakeRatSnapshot('snoplus', commit_hash, versionUpdate=False,
                                       zipPrefix='rat/', cachePath=os.path.expanduser('~/gaspCache'))
    sw_path = os.path.join(config.sw_directory, 'snapshots')
    sw_name = 'rat-%s' % commit_hash
    env_name = os.path.join(sw_path, 'env_rat-%s.sh' % commit_hash)
    if os.path.exists(os.path.join(sw_path, sw_name, 'bin/rat')) and \
       os.path.exists(env_name):
        return str(env_name) # installed already
    print "INSTALLING rat-%s; this may take a while" % commit_hash
    print "untarring..."
    untar_file(zip_name, sw_path, sw_name)
    os.system("chmod u+x %s" % os.path.join(sw_path, sw_name, 'configure'))
    # Untarred; now configure and install
    base_env = os.path.join(config.sw_directory, 'env_rat-%s.sh' % rat_version)
    create_env(os.path.join(sw_path, 'installerTemp.sh'), base_env)
    # compile
    print "compiling..."
    command_text = "\
#!/bin/bash\n \
source %s\n \
cd %s\n \
./configure \n \
source env.sh\n \
scons" % (os.path.join(sw_path, 'installerTemp.sh'), os.path.join(sw_path, sw_name))
    filename = os.path.join(os.getcwd(), "temp.sh")
    temp_file = file(filename, 'w')
    temp_file.write(command_text)
    temp_file.close()
    os.system('/bin/bash %s' % filename)
    os.system('chmod u+x %s' % os.path.join(sw_path, sw_name, 'bin/rat'))
    print "...installed"
    ###
    create_env(env_name, base_env, os.path.join(sw_path, sw_name))
    return str(env_name)

def untar_file(tarname, target_path, target_dir):
    import tarfile
    import shutil
    tarred_file = tarfile.open(tarname)
    tarred_file.extractall(target_path)
    tarred_file.close()

def create_env(filename, env_file, rat_dir=None):
    '''Create environment file to source for RAT jobs.
    
    If rat_dir is not set, then assumes only base directories are needed.
    '''
    if not os.path.exists(env_file):
        raise Exception("create_env::cannot find environment %s" % env_file)
    fin = file(env_file, 'r')
    env_text = ''
    lines = fin.readlines()
    for i,line in enumerate(lines):
        if 'source ' in line:
            if i==len(lines)-1 or i==len(lines)-2:
                # This is the fixed RAT release line; remove it!
                pass
            else:
                env_text += '%s \n' % line
        else:
            env_text += '%s \n' % line
    if rat_dir is not None:
        env_text += "source %s" % os.path.join(rat_dir, "env.sh")
    env_file = file(filename, 'w')
    env_file.write(env_text)

def get_env_path(sw_directory, rat_version):
    rat_env_file = str(os.path.join(sw_directory, 'env_rat-%s.sh' % rat_version))
    if not os.path.exists(rat_env_file):
        raise Exception("Missing job environment for: " % rat_env_file)
    return rat_env_file

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
    job_env = get_env_path(config.sw_directory, ratVersion)
    if 'commitHash' in doc:
        job_env = install_snapshot(config, ratVersion, commitHash)
    job.application.args = [job_env, 'card.json', 'macro.mac']
    job.inputsandbox += ['job/card.json', 'job/macro.mac', 'job/benchmark.py']
    job.submit()
    #json.dumps(jobcard)
    # Ensure that the doc is saved
    doc = database.get_doc(jobid)
    doc['info'][macro_name]['state']='submitted'
    doc['info'][macro_name]['fqid']=job.fqid
    try:
        database.save_doc(doc)
    except:
        print "Warning: 2nd try at saving"
        time.sleep(1)
        doc = database.get_doc(jobid)
        doc['info'][macro_name]['state']='submitted'
        doc['info'][macro_name]['fqid']=job.fqid
        database.save_doc(doc)


def check_old(database,config):
    # First, run monitoring
    mon_result = Core.monitoring_component.runMonitoring(timeout=600)
    if not mon_result:
        log.error("Ganga monitoring loop failed to complete!")
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
                print "JOB FAILED",j.fqid
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
    parser.add_option('--test', dest='test_mode', help='Just run in test mode, supply an arg for the version and (optional) commit',
                      action = 'store_true')
    (options, args) = parser.parse_args()
    config = BenchConfig.BenchConfig()
    if options.config:
        config.read_config(options.config)
    else:
        config.parse_options(options)

    if options.test_mode:
        if len(args)>1:
            submit_test(args[0], args[1])
        else:
            submit_test(args[0])
    else:
        database = Database.Database(config.db_server,config.db_name,
                                     config.db_user,config.db_password)
        try:
            emailCheck('smtp.gmail.com',config.email_address,config.email_password)
        except:
            raise Exception,'Bad email password'
        check_old(database,config)
        submit_waiting(database,config)
