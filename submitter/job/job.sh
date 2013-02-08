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
# arg2: card file
# arg3: macro to benchmark

echo $PATH
source $1
cat $1
echo $PATH
python benchmark.py $2 $3

rtc=$?
if [ $rtc -eq 0 ]
then
    exit 0
else
    exit 10
fi