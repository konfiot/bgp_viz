import json
import websocket
import logging
import curses
import signal
import sys
import networkx as nx
from colorama import Fore, Back, Style, init

AS_TO_DISPLAY = 513

init() # Init colors

# Init curses
#stdscr = curses.initscr()
#curses.noecho()
#curses.cbreak()

def restore_terminal(signal, frame):
	curses.echo()
	curses.nocbreak()
	curses.endwin()
	sys.exit(0)

signal.signal(signal.SIGINT, restore_terminal)
signal.signal(signal.SIGTERM, restore_terminal)


# Init logging
logging.basicConfig(level=logging.WARNING)

# Vonnect to feed
ws = websocket.WebSocket()
ws.connect("wss://ris-live.ripe.net/v1/ws/?client=bgpm")

params = {
	"moreSpecific": True,
	#"host": "rrc21",
	"type": "UPDATE",
	#"prefix": "216.238.254.0/23",
	#"path": str(AS_TO_DISPLAY),
	"socketOptions": {
		"includeRaw": True
	}
}

# Subscribe
ws.send(json.dumps({
	"type": "ris_subscribe",
	"data": params
	}))


# ASN Graph
ASNs = nx.DiGraph()

for data in ws:
	parsed = json.loads(data)

	news = set() # Newly announced routes
	withdrawn = set()
	if "withdrawals" in parsed["data"].keys():
		withdrawn = set(parsed["data"]["withdrawals"]) # Withdrawn routes

	if "announcements" in parsed["data"].keys():
		for announcement in parsed["data"]["announcements"]:
			news.update(announcement["prefixes"])

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

			if i < (len(path) - 1):
				neighbor = path[i+1]

				if neighbor == AS:
					logging.debug(Fore.YELLOW + f"DIDN'T ADD NOR CREATE : Circling on SELF : path between {AS} and {neighbor}" + Style.RESET_ALL)
					continue

				subnets = ASNs.edges[int(AS), int(neighbor)]["subnets"] if ASNs.has_edge(int(AS), int(neighbor)) else set()

				ASNs.add_edge(int(AS), int(neighbor), subnets = (subnets | news) - withdrawn)

					#logging.info(Fore.GREEN + f"CREATED Route to {new} to path between {AS} and {neighbor}, {len(ASNs[AS]['neighbors'][neighbor])} routes left" + Style.RESET_ALL)

			

#	if ASNs.has_node(AS_TO_DISPLAY):
#		print(f"AS {AS_TO_DISPLAY} has {len(ASNs.edges(AS_TO_DISPLAY))} neighbors : " + ', '.join(map(str, [x for _, x in ASNs.edges(AS_TO_DISPLAY)])))
