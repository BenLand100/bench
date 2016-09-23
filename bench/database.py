import httplib

# Important: this is a file that may get shipped to the backend

def connect_db(db_server, db_auth):
    '''Connect to the benchmarking database
    '''
    conn = httplib.HTTPConnection(db_server)
    headers = {'Content-type': 'application/json'}
    if db_auth is not None:
        authstring = 'Basic {0}'.format(db_auth)
        headers['Authorization'] = authstring
    return conn, headers


def get(db_server, db_name, db_auth, extension):
    '''Perform get request on an extension to the benchmarking DB
    '''
    conn, headers = connect_db(db_server, db_auth)
    url = '/{0}/{1}'.format(db_name, extension)
    conn.request('GET', url, headers = headers)
    return conn.getresponse().read()


def put(db_server, db_name, db_auth, extension, body):
    '''Perform put request on an extension to the benchmarking DB
    '''
    conn, headers = connect_db(db_server, db_auth)
    url = '/{0}/{1}'.format(db_name, extension)
    conn.request('PUT', url, body, headers = headers)
    return conn.getresponse().read()


