"""
Build database from the CSV files.
"""

import csv
import mysql.connector
from mysql.connector import Error


class MySql(object):
    cnx_ = None
    cursor_ = None
    host_ = None
    user_ = None
    passwd_ = None
    db_ = None

    def __init__(self, host='localhost', user='', passwd='', db=''):
        self.host_ = host
        self.user_ = user
        self.passwd_ = passwd
        self.db_ = db

    def __del__(self):
        self.cnx_.close()

    def sqlExecute(self, execStr, toPrint):
        if toPrint:
            print execStr
        try:
            self.cursor_.execute(execStr)
        except mysql.connector.Error as err:
            print(err.msg)
            return False
        return True

    # Connect to MySQL Database
    def connect(self):
        self.cnx_ = mysql.connector.connect(host=self.host_,
                                            database=self.db_,
                                            user=self.user_,
                                            password=self.passwd_)
        if self.cnx_.is_connected():
            self.cursor_ = self.cnx_.cursor()

    # Create tables
    def createTable(self, tabName, colList, toPrint=False):
        colListStr = ',\n\t'.join(colList)
        execStr = 'CREATE TABLE IF NOT EXISTS %s (\n\t%s\n);' % (
            tabName, colListStr)
        return self.sqlExecute(execStr, toPrint)

    # Load CSV data into TABLE
    def loadCSV(self, fileName, tabName, colList, fieldTerm=',',
                lineTerm='\\r\\n', ignoreHeader=True, toPrint=False):
        ignoreHeaderStr = ""
        if ignoreHeader:
            ignoreHeaderStr = "IGNORE 1 LINES"
        execStr = '''
            LOAD DATA LOCAL INFILE '%s' INTO TABLE %s
            FIELDS TERMINATED BY '%s' LINES TERMINATED BY '%s'
            %s (%s);
            ''' % (fileName, tabName, fieldTerm, lineTerm,
                   ignoreHeaderStr, colList)
        ret = self.sqlExecute(execStr, toPrint)
        self.cnx_.commit()  # MySQL connector needs commit for ins, del, update
        return ret


sql = MySql(user='ngovindaraj', passwd='the rock', db='sf')
sql.connect()

print "Creating nodes table:"
sql.createTable('nodes',
                ['id BIGINT PRIMARY KEY NOT NULL',
                 'lat REAL',
                 'lon REAL',
                 'user VARCHAR(36)',
                 'uid INTEGER',
                 'version INTEGER',
                 'changeset INTEGER',
                 'timestamp VARCHAR(36)'])
sql.loadCSV('nodes.csv', 'nodes',
            'id, lat, lon, user, uid, version, changeset, timestamp')

print "Creating nodes_tags table:"
sql.createTable('nodes_tags',
                ['id BIGINT',
                 '`key` VARCHAR(36)',
                 'value VARCHAR(40)',
                 'type VARCHAR(10)',
                 'FOREIGN KEY (id) REFERENCES nodes(id)'])
sql.loadCSV('nodes_tags.csv', 'nodes_tags', 'id, `key`, value, type')

print "Creating ways table:"
sql.createTable('ways',
                ['id BIGINT PRIMARY KEY NOT NULL',
                 'user VARCHAR(36)',
                 'uid INTEGER',
                 'version VARCHAR(36)',
                 'changeset INTEGER',
                 'timestamp VARCHAR(36)'])
sql.loadCSV('ways.csv', 'ways', 'id, user, uid, version, changeset, timestamp')

print "Creating ways_tags table:"
sql.createTable('ways_tags',
                ['id BIGINT NOT NULL',
                 '`key` VARCHAR(36)',
                 'value VARCHAR(36)',
                 'type VARCHAR(10)',
                 'FOREIGN KEY (id) REFERENCES ways(id)'])
sql.loadCSV('ways_tags.csv', 'ways_tags', 'id, `key`, value, type')

print "Creating ways_nodes table:"
sql.createTable('ways_nodes',
                ['id BIGINT NOT NULL',
                 'node_id BIGINT NOT NULL',
                 'position INTEGER NOT NULL',
                 'FOREIGN KEY (id) REFERENCES ways(id)',
                 'FOREIGN KEY (node_id) REFERENCES nodes(id)'])
sql.loadCSV('ways_nodes.csv', 'ways_nodes', 'id, node_id, position')
