#
# Functions to be used to revert jobs to the "submitted" state
#
from src import Database, BenchConfig

def revert_by_version_phase(config_name, version, phase, commit_hash=None):
    config = BenchConfig.BenchConfig()
    config.read_config(config_name)
    database = Database.Database.get_instance(host = config.db_server,
                                              name = config.db_name,
                                              user = config.db_user,
                                              pswd = config.db_password)
    rows = database.view('_design/benchmark/_view/docs_by_version_phase',
                         key = [version, phase, commit_hash],
                         include_docs = True)
    for row in rows:
        doc = row.doc
        revert = raw_input("Revert for %s docs in %s %s %s? " % (len(doc['info']), version, phase, commit_hash))
        if revert != "Y" and revert != "y":
            continue
        print "REVERTING"
        for macro in doc['info']:
            doc['info'][macro]['state'] = 'waiting'
        database.save(doc)


def revert_failed_by_version_phase(config_name, version, phase, commit_hash=None):
    config = BenchConfig.BenchConfig()
    config.read_config(config_name)
    database = Database.Database.get_instance(host = config.db_server,
                                              name = config.db_name,
                                              user = config.db_user,
                                              pswd = config.db_password)
    rows = database.view('_design/benchmark/_view/docs_by_version_phase',
                         key = [version, phase, commit_hash],
                         include_docs = True)
    for row in rows:
        doc = row.doc
        n_failed = 0
        for macro in doc['info']:
            if doc['info'][macro]['state'] == 'failed':
                n_failed += 1
        print "Total docs for %s %s: %s" % (version, phase, len(doc['info']))
        print "Total failed        : %s" % n_failed
        revert = raw_input("Revert failed docs? ")
        if revert != "Y" and revert != "y":
            continue
        for macro in doc['info']:
            if doc['info'][macro]['state'] == 'failed':
                doc['info'][macro]['state'] = 'waiting'
        database.save(doc)
