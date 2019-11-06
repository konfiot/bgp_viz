import logging
import sys
import time
from datetime import datetime
import networkx as nx
from _pybgpstream import BGPStream, BGPRecord, BGPElem
import ast

SAVE_INTERVAL = 30
#SAVE_INTERVAL = 10

START_TIMESTAMP = 1438417216
RECORD_PERIOD = 60*2

# Init logging
logging.basicConfig(level=logging.WARNING)

# Create stream
stream = BGPStream()
rec = BGPRecord()

#stream.add_interval_filter(START_TIMESTAMP,START_TIMESTAMP + RECORD_PERIOD)

# Consider Route Views Singapore only
stream.add_filter('collector','route-views.sg')

# Consider RIBs dumps only
stream.add_filter('record-type','ribs')

# Consider this time interval:
# Sat, 01 Aug 2015 7:50:00 GMT -  08:10:00 GMT
stream.add_interval_filter(1438415400,1438416600)

stream.start()

# ASN Graph
ASNs = nx.DiGraph()

messages_recieved = 0

last_time_saved = START_TIMESTAMP

while(stream.get_next_record(rec)):
	if rec.status != "valid":
		print("Invalid record", rec.project, rec.collector, rec.type, rec.time, rec.status)
		continue

	elem = rec.get_next_elem()
	while(elem):
		news = set() # Newly announced routes
		withdrawn = set()
		if elem.type == "W":
			withdrawn = {elem.fields["prefix"]} # Withdrawn routes

		elif elem.type in ["A", "R"]:
			news = {elem.fields["prefix"]}

		if "as-path" in elem.fields.keys() and len(elem.fields["as-path"]) > 1: #TODO : Gérer mieux le cas à 1 dans le path, voire 0
			path_raw = elem.fields["as-path"].split(" ")
			path = []
			for AS in path_raw:
				AS = ast.literal_eval(AS)
				if isinstance(AS, int):
					path.append(AS)
				else:
					for real_AS in AS:
						path.append(real_AS)

			for i, AS in enumerate(path) :
				# Add new routes

				if i < (len(path) - 1):
					neighbor = path[i+1]

					if neighbor == AS:
						#logging.debug(Fore.YELLOW + f"DIDN'T ADD NOR CREATE : Circling on SELF : path between {AS} and {neighbor}" + Style.RESET_ALL)
						continue

					subnets = ASNs.edges[int(AS), int(neighbor)]["subnets"] if ASNs.has_edge(int(AS), int(neighbor)) else set()

					new_subnets = (subnets | news) - withdrawn
					ASNs.add_edge(int(AS), int(neighbor), subnets = new_subnets, weight=len(new_subnets))

		elem = rec.get_next_elem()

	# Save
	if rec.time - last_time_saved >= SAVE_INTERVAL:
		filename = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
		print("Saving graph,", len(ASNs.nodes), "nodes...", end="")
		nx.readwrite.gml.write_gml(ASNs, f"out/{filename}.gml.gz", stringizer=lambda x: str(list(x)))
		print(" Saved")
		last_time_saved = rec.time
