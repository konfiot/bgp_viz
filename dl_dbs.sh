#!/bin/sh
wget -O continents.json https://gist.githubusercontent.com/konfiot/9bd14f0013afd05b0037e447de4b31ca/raw/d37f46d2e1eb37987a0e69f905cdb61a75e8e327/continents.json
wget -O db.tar.gz www.cc2asn.com/data/db.tar.gz
mkdir db
tar -C db -zxf db.tar.gz
rm db.tar.gz
