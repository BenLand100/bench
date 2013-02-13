################################################
# benchmark.py    
# Author: James Waterfield
#         jw419@sussex.ac.uk
#         2012/09/05
# 2012/10/03 - m.mottram@sussex.ac.uk
#   Now writes memory error message to
#   log file and exits while loop. Can now give
#   script macros from any directory.
# 2013/02/07 - m.mottram@sussex.ac.uk
#   Works as a submitted script, will feedback
#   benchmark information and insert directly
#   into a database.
################################################

import sys
import smtplib
import os
from subprocess import Popen
import time
import couchdb
import json

_scale = {'kB': 1024.0, 'mB': 1024.0*1024.0, 'gB': 1024.0*1024.0*1024.0,
          'KB': 1024.0, 'MB': 1024.0*1024.0, 'GB': 1024.0*1024.0*1024.0}

##################################################################

def memory(pid):
    '''Returns virtual memory of RAT
    '''
    global _scale
    t = open(pid,'r') #Get pid info
    lines=t.readlines()
    v=''
    for line in lines:
        if 'VmSize' in line:
            v = line
            break
    if v=='':
        print 'Cannot get info from PID stat'
        raise Exception
    t.close() 
    # get VmSize line e.g. 'VmSize:  9999  kB\n ...'
    v = v.split()
    if len(v) != 3:
        print 'Invalid memory format!'
        raise Exception
    # convert Vm value to bytes
    print v[1],_scale[v[2]]
    return float(v[1]) * _scale[v[2]]

################################################################

def benchmark(macro,card):
    ''' Runs macro to get per event statistics and memory usage.
    '''
    sTime = time.time() #start timing RAT
    logName = 'bench.'+os.path.basename(macro)+'.log'
    #calling rat spawns rat_exe, need to call that directly ... urgh!
    ratdir=os.environ['RATROOT']
    ratsys=os.environ['RATSYSTEM']
    ratexe='%s/bin/rat_%s' % (ratdir,ratsys)    
    args = [ratexe,'-l',logName,'-N',str(card['n_events']),'-o',card['root_name'],macro]
    for arg in args:
        print 'arg:',arg,type(arg)
    try:
        p = Popen(args=args, shell=False) #Start RAT
    except:
        print 'Must source RAT before running benchmark!' #RAT not avaliable
        raise Exception
    pid = '/proc/%d/status' % p.pid #Get RAT PID no.
    cTime = time.time()
    # Sample memory for max of 10 mins:
    mem = []
    while cTime - sTime < 600:
        try:
            time.sleep(1)
            temp = memory(pid)
            #print 'mem sample: %s MB' % (temp / _scale["MB"])
            if temp == -1: #Exit loop if error code returned
                break
            else:
                mem.append(temp) #Add memory to list
                cTime = time.time()
            if temp > (3 * _scale['GB']):
                print 'BENCHMARK: JOB EXCEEDS ALLOWED 3GB MEM USAGE: %s'%temp
                raise Exception
        except:
            print 'exiting loop early may overestimate time/event...\n'
            break
    print 'here!?'
    p.communicate() #Check if RAT still running
    size = None
    outputDir = os.path.join(os.getcwd(),os.path.basename(macro)+'.log')#Output log file to cwd
    fileOut = open(outputDir,'w')
    size = None
    if os.path.exists(card['root_name']):
        size = os.path.getsize(card['root_name'])
    else:
        #Really just want to raise an exception and shove a message here for
        #the main script to find
        print 'BENCH: OUTPUT ROOT FILE DOES NOT EXIST'
        raise Exception
        #message += 'Output ROOT file does not exist! \n'
        #message += 'dir contents:\n'
        #for f in os.listdir(os.getcwd()):
        #    message += '%s \n' % f
        #failBench(card,macro,message)
    fileOut.write('For macro %s and a test of %i events.\n' % (macro, card['n_events']))
    ratLog = open(logName,'r')
    writeFlag = 0
    timeInfo = {}
    print 'here!?'
    for line in ratLog:
        if 'Processor usage statistics' in line:
            writeFlag = 1
        elif 'Total:' in line:
            fileOut.write(line)
            timeInfo['Total'] = float(line.split(':')[1].strip().split()[0])
            writeFlag = 0
        elif writeFlag == 1:
            if 'sec/event' in line:
                timeType = line.split(':')[0].strip()
                timeInfo[timeType] = float(line.split(':')[1].strip().split()[0])
            fileOut.write(line)
        else:
            continue
    print 'got here?'
    ratLog.close()
    evSize = size / card['n_events']
    # Write macro stats to log file:
    fileOut.write('Size per event: %.3f bytes\n' % evSize)
    if len(mem)>0:
        mMax = max(mem) # Get maximum memory usage
        mAv = sum(mem) / len(mem) # Get average memory usage
        fileOut.write('Max memory usage: %.3f bytes \n' % mMax)
        fileOut.write('Average memory usage: %.3f bytes \n' % mAv)
    else: #Write error message to log
        fileOut.write('WARNING: Unable to get memory usage stats. This is a Linux only script.')
    fileOut.close()
    fileOut= open(outputDir,'r')
    for line in fileOut:
        line = line.rstrip('\n')
        print line
    fileOut.close()
    print 'Output written to:', outputDir

    finalInfo = {}
    finalInfo['eventSize'] = evSize
    finalInfo['eventTime'] = timeInfo
    finalInfo['memoryMax'] = mMax
    finalInfo['memoryAve'] = mAv

    finishBench(card,finalInfo)

    return 0

def finishBench(card,finalInfo):
    '''Finish the benchmarking with an update of the DB and an email!
    '''
    email = ''
    email += 'Results for job %s/_utils/database.html?%s/%s: \n'%(card['db_server'],card['db_name'],card['doc_id'])
    email += 'Macro: %s \n'%card['macro_name']
    email += 'Time per event %s seconds\n'%finalInfo['eventTime']['Total']
    email += 'Size per event %s bytes\n'%finalInfo['eventSize']
    email += 'Max memory usage %s MB\n'%(finalInfo['memoryMax']/_scale['MB'])
    email += '\n'
    email += 'For production purposes:\n'
    email += 'Events in 24hr job: %s \n' % (int(round(3600.*24 / finalInfo['eventTime']['Total'])))
    email += 'Events in 1.6GB file: %s \n' % (int(round(1.6*_scale['GB'] / finalInfo['eventSize'])))
    sendEmail(card['email_server'],card['email_user'],card['email_pswd'],card['email_list'],email)

    db = connectDB(card['db_server'],card['db_name'],card['db_auth'])
    doc = db[card['doc_id']]
    doc['info'][card['macro_name']]['state']='completed'
    doc['info'][card['macro_name']]['event_size']=finalInfo['eventSize']
    doc['info'][card['macro_name']]['event_time']=finalInfo['eventTime']
    doc['info'][card['macro_name']]['memory_max']=finalInfo['memoryMax']
    db.save(doc)

def failBench(card,macro,message=None):
    '''Benchmarking failed, notify user!
    '''
    email = ''
    email += 'Results for job %s/_utils/database.html?%s/%s: \n'%(card['db_server'],card['db_name'],card['doc_id'])
    email += 'Macro: %s \n'%macro
    email += 'Job failed\n'
    if message != None:
        email += message
    sendEmail(card['email_server'],card['email_user'],card['email_pswd'],card['email_list'],email)

    db = connectDB(card['db_server'],card['db_name'],card['db_auth'])
    doc = db[card['doc_id']]
    doc[card['macro_name']]['state']='failed'
    db.save(doc)

def connectDB(host,name,auth):
    couch = couchdb.Server(host)
    couch.resource.headers['Authorization'] = 'Basic %s' % auth
    db = couch[name]
    return db

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
    smtp.sendmail(mailUser,mailList,message)

def read_card(card_filename):
    cardfile = open(card_filename)
    card = json.load(cardfile)
    return card

#############################################################################

if __name__ == '__main__':
    print 'running with macro:',sys.argv[1]
    card_file = sys.argv[1]
    macro = sys.argv[2]
    card = read_card(card_file)
    if os.path.isfile(macro) == True: #Check macro exists
        #try:
        benchmark(macro,card)
        #except:
        #    failBench(card,macro)
        #    sys.exit(1)
    else:
        print 'User must give macro directory to benchmark.py in command line' #No macro or invalid path!
        sys.exit()
