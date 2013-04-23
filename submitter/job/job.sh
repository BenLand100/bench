#!/bin/bash -l

#################################
# The job script, always submitted
# Author: Matt Mottram 
#         m.mottram@sussex.ac.uk
# This could be made into a python
# script (might be better for error
# handling)
#################################

#Expects three arguments, no arg parser
# arg1: software script to source
# arg2: rat version to source
# arg3: card file
# arg4: macro to benchmark

source $1 env_rat-${2}.sh
python benchmark.py $3 $4

rtc=$?
if [ $rtc -eq 0 ]
then
    exit 0
else
    exit 10
fi