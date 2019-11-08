# coding: utf-8
import multiprocessing
import sys
import time
from common.graph import update_graph, save_graph
from datetime import datetime
import networkx as nx
from _pybgpstream import BGPStream, BGPRecord, BGPElem
import ast

def do_collection(args):
	START_TIMESTAMP = 1438417216
	RECORD_PERIOD = 60*2

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
	stream.add_interval_filter(1438415400,1438517600)

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
								update_graph(ASNs, AS, neighbor, news, withdrawn)

				elem = rec.get_next_elem()

			# Save
			if rec.time - last_time_saved >= args.save_rate*60:
				save_process = multiprocessing.Process(target=save_graph, args=(ASNs.copy(), args.output_folder))
				save_process.start()
				last_time_saved = rec.time
