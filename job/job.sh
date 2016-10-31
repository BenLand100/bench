#!/bin/bash -l
# Wrapper script to set up environment for benchmarking

${EnvAdditions}

cd ${jobdir}
source ${ratenv}

python benchmark.py ${dbserver} ${dbauth} ${dbname} ${documentid} ${ratversion}
# Maintain the exit status of the python script
exit $$?
