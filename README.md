# Installing

## Install dependancies
Install libpybgpstream using instructions here (use the instructions tailored for your distribution) : https://bgpstream.caida.org/docs/install/bgpstream

Install python packages using pip : `pip install -r requirements.txt`

## Download db files
```
wget www.cc2asn.com/data/db.tar.gz
mkdir out
mkdir db
tar -C db -zxf db.tar.gz 
wget -O continents.json https://datahub.io/JohnSnowLabs/country-and-continent-codes-list/r/country-and-continent-codes-list-csv.json
```


