#!/bin/bash -l
# Wrapper script to set up environment for benchmarking

${EnvAdditions}

cd ${jobdir}
source ${ratenv}

python benchmark.py ${dbserver} ${dbname} ${dbauth} ${documentid} ${ratversion}
# Maintain the exit status of the python script
exit $$?
