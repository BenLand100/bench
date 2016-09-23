#!/bin/bash -l
# Wrapper script to set up environment for benchmarking
# Expects arguments:
# 1: job directory
# 2: rat_environment
# 3: db_server
# 4: db_name
# 5: db_auth
# 6: document_id
# 7: rat_version
# NB: have to escape all dollars unless part of the template

${EnvAdditions}

cd $$1
source $$2

python benchmark.py $$3 $$4 $$5 $$6 $$7
# Maintain the exit status of the python script
exit $$?
