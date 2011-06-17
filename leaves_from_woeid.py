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
leaftypes = ('LocalAdmin',"Suburb")

#owriter = csv.writer(sys.stdout)
#owriter.writerow(["parent_id","name","type","woe_id"])

def main():
    for woeid in sys.argv[1:]:
        print >>sys.stderr, woeid,

        childq = """select * from woe_places
                where parent_id = %s
                and placetype in ('County','LocalAdmin','Suburb')"""

        conn_string = "dbname='hood'"
        # get a connection, if a connect cannot be made an exception will be raised here
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        search = set([woeid])
        leaves = set()
        names = {}
        types = {}
        while len(search) > 0:
            print >>sys.stderr, ".",
            curr_search = copy.copy(search)
            for woe in curr_search:
                search.remove(woe)
                qry = childq % woe
                cursor.execute(qry)
                if cursor.rowcount == 0:
                    if woe not in types:
                        break
                    if types[woe] in leaftypes:
                        leaves.add((woeid,names[woe],types[woe],woe))
                for line in cursor:
                    names[line['woe_id']] = line['name']
                    types[line['woe_id']] = line['placetype']
                    search.add(line['woe_id'])

        conn.close()
        print >>sys.stderr, ""

        for leaf in leaves:
            #owriter.writerow(leaf)
            print "\t".join(map(str,leaf))

if __name__ == "__main__":
    sys.exit(main())

