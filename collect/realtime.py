import orjson as json
import websocket
import logging
import sys
import time
import multiprocessing
from datetime import datetime
import networkx as nx
from colorama import Fore, Back, Style, init

SAVE_INTERVAL = 60*30
#SAVE_INTERVAL = 10

def save_graph(ASNs):
	print("Saving graph,", len(ASNs.nodes), "nodes,", len(ASNs.edges()), "edges...", end="")
	for edge in ASNs.edges(data=True):
		edge[2]["subnets"] = list(edge[2]["subnets"].keys())
	nx.readwrite.gml.write_gml(ASNs, f"out/{filename}.gml", stringizer=nx.readwrite.gml.literal_stringizer)
	print(" Saved")


init() # Init colors

# Init logging
logging.basicConfig(level=logging.WARNING)

params = {
	"moreSpecific": False,
	"type": "UPDATE",
	"socketOptions": {
		"includeRaw": False
	}
}

def connect(params):
	ws = websocket.WebSocket()
	ws.connect("ws://ris-live.ripe.net/v1/ws/?client=bgpm")
	ws.send(json.dumps({
		"type": "ris_subscribe",
		"data": params
		}))
	return ws



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

				#logging.debug(f"Processing path {path} announce {news} withdraw {withdrawn}")

				for i, AS in enumerate(path) :
					# Add new routes
					AS = int(AS)

					if i < (len(path) - 1):
						neighbor = int(path[i+1])

						if neighbor == AS:
							#logging.debug(Fore.YELLOW + f"DIDN'T ADD NOR CREATE : Circling on SELF : path between {AS} and {neighbor}" + Style.RESET_ALL)
							continue

						subnets = dict()

						try:
							subnets = ASNs.edges[AS, neighbor]["subnets"]
						except:
							pass


						for x in news:
							if isinstance(x, list):
								for y in x:
									subnets[y] = True
							else:
								subnets[x] = True
						for x in withdrawn:
							try:
								del subnets[x]
							except KeyError:
								pass

						if len(subnets) > 0:
							ASNs.add_edge(AS, neighbor, subnets = subnets, weight=len(subnets))
						else:
							try:
								ASNs.remove_edge(AS,neighbor)
							except:
								pass

							#logging.info(Fore.GREEN + f"CREATED Route to {new} to path between {AS} and {neighbor}, {len(ASNs[AS]['neighbors'][neighbor])} routes left" + Style.RESET_ALL)


			# Save
			if time.time() - last_time_saved >= SAVE_INTERVAL:
				filename = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
				save_process = multiprocessing.Process(target=save_graph, args=(ASNs.copy(),))
						
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

