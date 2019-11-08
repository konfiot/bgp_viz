# coding: utf-8
import json
import websocket
import sys
import time
from common.graph import update_graph, save_graph
import multiprocessing
from datetime import datetime
import networkx as nx

def connect(params):
	ws = websocket.WebSocket()
	ws.connect("ws://ris-live.ripe.net/v1/ws/?client=bgpm")
	ws.send(json.dumps({
		"type": "ris_subscribe",
		"data": params
		}))
	return ws



def do_collection(args):
	params = {
		"moreSpecific": False,
		"type": "UPDATE",
		"socketOptions": {
			"includeRaw": False
		}
	}

	# ASN Graph
	ASNs = nx.DiGraph()

	last_time_saved = time.time()

	while True:
		ws = connect(params)
		try:
			for data in ws:
				parsed = json.loads(data)

				if parsed["type"] != "ris_message":
					print(parsed)
				
				news = [] # Newly announced routes
				withdrawn = []
				if "withdrawals" in parsed["data"].keys():
					withdrawn = parsed["data"]["withdrawals"] # Withdrawn routes

				if "announcements" in parsed["data"].keys():
					for announcement in parsed["data"]["announcements"]:
						news.append(announcement["prefixes"])

				if "path" in parsed["data"].keys() and len(parsed["data"]["path"]) > 1: #TODO : Gérer mieux le cas à 1 dans le path, voire 0
					path_raw = parsed["data"]["path"]
					path = []
					for AS in path_raw:
						if isinstance(AS, int):
							path.append(AS)
						else:
							for real_AS in AS:
								path.append(real_AS)


					for i, AS in enumerate(path) :
						# Add new routes
						AS = int(AS)

						if i < (len(path) - 1):
							neighbor = int(path[i+1])

							if neighbor == AS:
								continue

							subnets = dict()
							update_graph(ASNs, AS, neighbor, news, withdrawn)



				# Save
				if time.time() - last_time_saved >= args.save_rate*60:
					save_process = multiprocessing.Process(target=save_graph, args=(ASNs.copy(), args.output_folder))
					save_process.start()
					last_time_saved = time.time()

		except websocket._exceptions.WebSocketConnectionClosedException:
			print("Socket closed, retrying")
			pass
		except websocket._exceptions.WebSocketBadStatusException as err:
			print("Bad status error :", err)
			pass
		except ConnectionResetError:
			print("Connection reset")
			pass

