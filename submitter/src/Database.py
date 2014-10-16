# Singleton object, essentially a copy of the CouchDB database
# but with login handled automatically

import getpass
import couchdb
from base64 import b64encode

class Database(couchdb.client.Database):
    '''The main class for interacting with the database
    '''

    _instance = None

    class SingletonHelper(object):

        def __call__(self, *args, **kw):
            if Database._instance is None:
                object = Database(*args, **kw)
                Database._instance = object
            return Database._instance

    get_instance = SingletonHelper()


    def __init__(self, host, name, user, pswd):
        couch = couchdb.Server(host)
        couch.resource.credentials = (user, pswd)
        super(Database, self).__init__(couch.resource(name), name)

