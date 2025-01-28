
import dbConnection
from PyQt6 import QtCore

class dbConnectionClassExample(QtCore.QObject):

    def __init__(self, odbcSource, user, password):

        super(dbConnectionClassExample, self).__init__()

        #  create an instance of our dbConnection
        self.db = dbConnection.dbConnection(odbcSource, user, password)

        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.runExample)
        timer.setSingleShot(True)
        timer.start(1)


    def runExample(self):

        #  open the connection - dbOpen will raise an error if it can't connect
        try:
            self.db.dbOpen()
        except Exception as err:
            print("ooops, we couldn't open up the database")
            print(err)
            QtCore.QCoreApplication.instance().quit()


        s_ship = '157'
        s_survey = '201407'

        #  create some sql
        sql = ("SELECT ship,survey,name,chief_scientist,start_date,end_date,start_port," +
               "end_port,sea_area,abstract FROM clamsbase2.surveys WHERE ship=" + s_ship +
               " AND survey=" + s_survey)

        #  call the dbQuery method of our dbConnection object to return an instance
        #  of dbQueryResults that is an iterable that contains the results of our query.
        query = self.db.dbQuery(sql)

        #  the dbQueryResults object has a couple of properties we may insterested in
        #  and so we just print them out here for your information
        print("Query Column Names: ", query.columns)
        print("Query Column Types: ", query.columnTypes)
        print("Number of Columns: ", query.nColumns)

        #  if you need access to the underlying qSqlQuery object it's in there too.
        #  just note that if you manipulate it by calling it's next(), first(), or
        #  last() arguments you will alter how the iterator behaves.
        print("The underlying query object: ", query.query)

        #  you can use the regular python methods for accessing the iterator
        #  usually this will be a for-in loop. The benefit is that this approach
        #  should be far more readable than the query.value(0).toString() business
        #  we have been doing to date.
        for ship,survey,name,chief_scientist,start_date,end_date,start_port,end_port,sea_area,abstract in query:
            print(ship)
            print(survey)
            print(name)
            print(chief_scientist)
            print(start_date)
            print(end_date)
            print(start_port)
            print(end_port)
            print(sea_area)
            print(abstract)

        print('')


        #  you can also call the dbQueryResults first() method to get the first
        #  result from a query. This is typically used when you know you will only
        #  get a single result from your query.
        #
        #  In this example we purposly select for an empty result to demonstrate
        #  what happens in these cases.
        sql = ("SELECT ship,survey,name,chief_scientist FROM clamsbase2.surveys WHERE ship=9999")
        query = self.db.dbQuery(sql)
        #  this query will be empty so all of the fields returned contain None
        ship,survey,name,chief_scientist = query.first()
        if (ship == None):
            print('NO RESULTS! FROM YOUR EMPTY QUERY')
        else:
            print(ship)
            print(survey)
            print(name)
            print(chief_scientist)

        #  IMPORTANT NOTE: By default the dbQuery method returns a "Forward Only" query. This
        #  results in better performance, especially on large result sets, but forward only
        #  queries will return an error if you call the first() method more than once.
        #  Before you set the forwardOnly keyword to False, consider re-writing your code to
        #  not call first() multiple times.


        #  another simple example
        print('')
        sql = ("SELECT device_id, device_name FROM clamsbase2.devices")
        query = self.db.dbQuery(sql)
        for dev_id,dev_name in query:
            print("ID: %s ::: %s" % (dev_id,dev_name))


        #  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! #
        #  LOOK AT THIS EXAMPLE BECAUSE THIS WILL DEFINITELY TRIP YOU UP #
        #  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! #

        #  The way that python knows you want to unpack a list into a series
        #  of variables is that you give it multiple variables on the LHS:
        #
        #  x,y,z = [1,2,3]
        #
        #  results in x=1, y=2, and z=3.
        #
        #  But what if your query only returns a single value and you want to
        #  unpack that? Then you use the following syntax:
        #
        #  x, = [1]
        #
        #  results in x=1. You see the comma there? Yes, that's the magic. So
        #  look closely at the example below:

        print('')
        sql = ("SELECT device_id FROM clamsbase2.devices")
        query = self.db.dbQuery(sql)
        for dev_id, in query:                # <------See the comma there?
            print("ID: %s " % (dev_id))


        #  test how dbSelectResults works with an empty query
        print('')
        sql = ("SELECT event_parameter FROM clamsbase2.event_parameters where event_parameter='NO SUCH PARAM'")
        query = self.db.dbQuery(sql)
        for ep in query:
            print(ep)


        #  test how dbSelectResults works when selecting a null entry
        #  Answer: NULLS are returned as None so deal with the accordingly
        print('')
        sql = ("SELECT event_id,comments FROM clamsbase2.samples where ship=157 AND survey=201207 AND event_id=15")
        query = self.db.dbQuery(sql)
        for event_id, comments in query:
            print("ID: %s Comments in here--->%s<---" % (event_id,comments))


        #  ------------------   DATES AND TIMESTAMPS --------------------------
        #
        #  dbConnection sets the Oracle NLS_TIMESTAMP_FORMAT and NLS_DATE_FORMAT
        #  when you open your connection. This ensures a readable and consistent
        #  format is used when querying date/timestamp data.
        #
        #  When using dbQuery/dbQueryResults, all Date type columns are returned
        #  as strings in the following format:
        #
        #        MM/DD/YYYY HH24:MI:SS
        #
        #  Date types in Oracle also store time to the second, but if you are
        #  dealing with dates that don't have time, you can truncate the string
        #  or reformat it as needed. To query dates you do not need to do anything
        #  special:

        print('')
        print('Dates:')
        sql = ("SELECT event_id,time_stamp FROM clamsbase2.samples where ship=157 AND survey=201207 AND event_id=15")
        query = self.db.dbQuery(sql)
        for event_id, time_stamp in query:
            print("ID: %s Date type output--->%s<---" % (event_id,time_stamp))

        #  When you want to INSERT dates, you must use the TO_DATE() function to
        #  convert the date string to a Date object the database can store. Note that
        #  you don't have to provide a format string if you provide dates in the
        #  default format as defined above. Here is a ficticious example:

        #sql = ("INSERT INTO nunya.biznass (event_id, time_stamp) VALUES (1, TO_DATE(time_stamp))")
        #self.db.dbExec(sql)

        #  TIMESTAMPS ARE DIFFERENT. Qt treats timestaps as dates and because of this
        #  the fractional seconds are dropped if you don't convert to a string on the
        #  database side. But, since we've set the NLS_TIMESTAMP_FORMAT we don't at
        #  least have to explicitly set the format eact time we call TO_CHAR:
        print('')
        print('Timestamps:')
        sql = ("SELECT event_id,TO_CHAR(time_stamp) FROM clamsbase2.event_stream_data where ship=157 AND survey=201608 "
                "AND time_stamp BETWEEN '6/14/2016 9:19:21' AND '6/14/2016 9:19:23'")
        query = self.db.dbQuery(sql)
        for event_id, time_stamp in query:
            print("ID: %s Timestamp type output--->%s<---" % (event_id,time_stamp))

        #  just like with dates, you must convert your string to a timestamp before
        #  inserting it into the database. Use the TO_TIMESTAMP function like so:

        #sql = ("INSERT INTO nunya.biznass (event_id, time_stamp) VALUES (1, TO_TIMESTAMP(time_stamp))")
        #self.db.dbExec(sql)


        #  RETURNING QUERIES AS DICTIONARIES
        #  sometimes you may not want to iterate through your result set and just
        #  want the data packed in a dicitonary. As of 9/2019 you can set the "asDict"
        #  keyword of dbQuery to return the results in a dictionary. The dictionary
        #  will be keyed by column names and the values will be lists, orderd by row.
        #
        #  Note that the column names will match what is in your SELECT statement.
        #  This means that computed columns will include the function and args. In the
        #  query below, the last column will be "prc_nasc*1.1234"
        #
        #  Also note that when returning a dict, the entire query set is read into
        #  memory. This may cause problems with very large query sets. Use yer brain.

        sql = ("SELECT ship,survey,data_set_id, prc_nasc*1.1234 FROM macebase2.integration_results "
                "WHERE ship=157 AND survey=200909 AND interval=13330")
        data = self.db.dbQuery(sql, asDict=True)

        print('')
        print("Dict keys: ", data.keys())
        for k in data.keys():
            print("Key:" + k, data[k])



        #  select "*" queries return their results in an undefined order so you can't
        #  blindly unpack them but you can use the dbSelectResults.columns property
        #  if needed. (But it is best not to use "*" queries.)
        print('')
        sql = ("SELECT * FROM clamsbase2.gear")
        query = self.db.dbQuery(sql)
        for results in query:
            for i in range(query.nColumns):
                print('%s : %s' % (query.columns[i],results[i]))


        #  test how dbConnection handles SQL errors
        print('')
        try:
            sql = ("SELECT Garbage this makes no sense")
            query = self.db.dbQuery(sql)
            for results in query:
                print(results)
        except Exception as e:
            print("There was a problem.")
            print(e)


        #  close the database connection
        print('Done!')

        #  close the connection
        self.db.dbClose()

        #  quit
        QtCore.QCoreApplication.instance().quit()



#  this is a common way to make a script with classes/functions in it run
if __name__ == "__main__":
    import sys
    app = QtCore.QCoreApplication(sys.argv)
    #form = dbConnectionClassExample('ODBC_CONNECTION', 'DATABASE_USER', 'PASSWORD')
    form = dbConnectionClassExample('ODBC-DSN', 'username', 'password')
    sys.exit(app.exec())






