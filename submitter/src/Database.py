import getpass
import couchdb
from base64 import b64encode

class Database(object):
    '''The main class for interacting with the database
    '''
    def __init__(self,host,name,user,pswd=None):
        self.host = host
        self.name = name
        self.couch = couchdb.Server(host)
        if pswd==None:
            self.couch.resource.credentials = ( user , getpass.getpass('Database pswd: ') )
        else:
            self.couch.resource.credentials = ( user , pswd )
        self.db = self.couch[name]

    def get_credentials(self):
        return self.couch.resource.credentials

    def get_waiting_tasks(self):
        '''Get a list of macros in the waiting state
        '''
        rows = self.db.view('_design/benchmark/_view/macro_by_status',
                            key='waiting')
        return rows

    def get_failed_tasks(self):
        '''Get a list of macros in the waiting state
        '''
        rows = self.db.view('_design/benchmark/_view/macro_by_status',
                            key='failed')
        return rows

    def get_submitted_tasks(self):
        '''Get a list of macros in the waiting state
        '''
        rows = self.db.view('_design/benchmark/_view/macro_by_status',
                            key='submitted')
        return rows
            
    def get_attachment(self,id_or_doc,filename):
        '''Get an attachment from a document
        '''
        attachment = self.db.get_attachment(id_or_doc, filename)
        return attachment

    def get_doc(self,doc_id):
        '''Just return the document
        '''
        doc = self.db[doc_id]
        return doc

    def save_doc(self,doc):
        '''Save a document
        '''
        self.db.save(doc)
