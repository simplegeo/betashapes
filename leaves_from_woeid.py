#!/usr/bin/python
import sys
import psycopg2
import psycopg2.extras
import csv
import copy
#take in a woe_id
#find all the children of that woe_id that are local_admins or suburbs
#for each of the children that are local admins, get all their children that are local admins or suburbs
#repeat until have list of descendents that have no children
#print list as name, woe_id

def main():
    woeid = sys.argv[1]

    outfile = "leaves_%s.csv" % woeid

    childq = """select * from woe_places
            where parent_id = %s
            and placetype in ('LocalAdmin','Suburb')"""

    conn_string = "dbname='hood'"
    # get a connection, if a connect cannot be made an exception will be raised here
    conn = psycopg2.connect(conn_string)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    search = set([woeid])
    leaves = set()
    names = {}
    while len(search) > 0:
        curr_search = copy.copy(search)
        for woe in curr_search:
            search.remove(woe)
            qry = childq % woe
            cursor.execute(qry)
            if cursor.rowcount == 0:
                leaves.add((names[woe],woe))
            for line in cursor:
                names[line['woe_id']] = line['name']
                search.add(line['woe_id'])

    conn.close()

    owriter = csv.writer(open(outfile, 'w'))
    owriter.writerow(["name","woe_id"])
    for leaf in leaves:
        owriter.writerow(leaf)

if __name__ == "__main__":
    sys.exit(main())

