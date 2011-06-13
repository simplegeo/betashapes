#!/usr/bin/python
import sys
import csv

#first arg: input file, csv. column woe_id should be the list of woe_ids we want to pull out of photos.txt
#second arg: output file, txt subset of photos.txt (also remove photoid. samplr not expecting it)

def main():
    infile = sys.argv[1]

    outfile = sys.argv[2]

    photofile = "photos.txt"

    woes = []
    ireader = csv.DictReader(open(infile, 'r'))
    for line in ireader:
        woes.append(line['woe_id'])


    pfh = open(photofile, 'r')
    ofh = open(outfile, 'w')

    outstr = "%s\t%s\t%s\n"
    
    for row in pfh:
        photoid, placeid, lon, lat = row.strip().split()
        if placeid in woes:
            out = outstr % (placeid, lon, lat)
            ofh.write(out)

if __name__ == "__main__":
    sys.exit(main())

