#Module for handling interaction with (i.e. checking of) the macro
#Where the following commands are lists, they must be found in that order but can be
#space separated (so use regex to find them)

import os
import re
import sys

bad_commands = [#Commands that are scrictly forbidden
    ['/run/beamOn'],#'Not a valid command',
    ['/rat/procset','file'],#'Filename must not be set in macro'
    ]

bad_options = [#Commands that are allowed, as long as options for them are disabled
    '/rat/run/start',#'Number of events should not be set'
    ]

required_commands = [#Commands that MUST be used
    ['/rat/proclast','outroot'],#'ROOT output must be set as final processor'
    ['/rat/run/start'],
    ]

def verifyMacro(macro):
    '''Check the lines in the macro (a streamer object)
    '''
    #maximum parts that can be checked is three
    badCmd=False
    badOpt=False
    reqCmd=[]
    canRun=True
    reason = ''#only useful if the macro is bad
    for i in range(len(required_commands)):
        reqCmd.append(False)
    for i,line in enumerate(macro.readlines()):
        for cmd in bad_commands:
            if checkCommand(cmd,line):
                badCmd=True
                canRun=False
                reason+='Unacceptable command (line %s): %s \n'%(i,''.join(['%s ' % bit for bit in cmd]) )
        for cmd in bad_options:
            if checkOption(cmd,line):
                badOpt=True
                canRun=False
                reason+='No options allowed for command (line %s): %s \n'%(i,bad_options)
        for i,cmd in enumerate(required_commands):
            if checkCommand(cmd,line):
                reqCmd[i]=True
    for i,cmd in enumerate(required_commands):
        if reqCmd[i]==False:
            canRun=False
            reason+='Missing command: %s \n'%(''.join(['%s ' % bit for bit in cmd]))
    return canRun,reason

def checkCommand(command,line):
    '''Match the line and groups, return true if a match
    '''
    pattern = re.compile(r'''\s*(?P<command>\S*)\s*(?P<option>\S*)''')
    search = pattern.search(line)
    parts = ['command','option']
    match=[]
    for i in range(len(command)):
        match.append(0)
    for i,part in enumerate(parts):
        if i>=len(command):
            continue
        if command[i]==search.group(part):
            match[i]=1
    fullMatch=True
    for i in match:
        if i==0:
            fullMatch=False
    return fullMatch

def checkOption(command,line):
    '''Fine to have a command, as long as no option is present
    '''
    pattern = re.compile(r'''\s*(?P<command>\S*)\s*(?P<option>\S*)''')
    search = pattern.search(line)
    parts = ['command','option']
    hasOption=False
    optionParts = parts[1:]
    commandPart = parts[0]
    if command==search.group(commandPart):
        #the command is present, is there an option?
        for part in optionParts:
            if search.group(part)!='':
                #option is present
                hasOption=True
    return hasOption
