import json
import websocket
import logging
import curses
import signal
import sys
from colorama import Fore, Back, Style, init

AS_TO_DISPLAY = 513

init() # Init colors

# Init curses
stdscr = curses.initscr()
curses.noecho()
curses.cbreak()

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
	"path": str(AS_TO_DISPLAY),
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
ASNs = {}

for data in ws:
	parsed = json.loads(data)

	news = [] # Newly announced routes
	withdrawn = []
	if "withdrawals" in parsed["data"].keys():
		withdrawn = parsed["data"]["withdrawals"] # Withdrawn routes

	if "announcements" in parsed["data"].keys():
		for announcement in parsed["data"]["announcements"]:
			news += announcement["prefixes"]

	if "path" in parsed["data"].keys() and len(parsed["data"]["path"]) > 1: #TODO : Gérer mieux le cas à 1 dans le path, voire 0
		path_raw = parsed["data"]["path"]
		path = []
		for AS in path_raw:
			if isinstance(AS, int):
				path.append(AS)
			else:
				for real_AS in AS:
					path.append(real_AS)

		logging.debug(f"Processing path {path} announce {news} withdraw {withdrawn}")

		for i, AS in enumerate(path) :
			potential_neighbors = [path[i-1], path[i+1]] if (0 < i < (len(path)-1)) else [path[i-1]] if 0 < i else [path[i+1]]


			# Add new routes

			if AS not in ASNs.keys():
				ASNs[AS] = {
					"neighbors": dict([(neighbor, news) for neighbor in potential_neighbors if neighbor != AS]),
				}

				for neighbor in potential_neighbors:
					if neighbor == AS:
						logging.debug(Fore.YELLOW + f"DIDN'T ADD NOR CREATE : Circling on SELF : Route to {new} to path between {AS} and {neighbor}" + Style.RESET_ALL)
						continue

					for new in news:
						logging.info(Fore.GREEN + f"CREATED Route to {new} to path between {AS} and {neighbor}, {len(ASNs[AS]['neighbors'][neighbor])} routes left" + Style.RESET_ALL)

			else :
				for neighbor in potential_neighbors:
					if neighbor == AS:
						logging.debug(Fore.YELLOW + f"DIDN'T ADD NOR CREATE : Circling on SELF : Route to {new} to path between {AS} and {neighbor}" + Style.RESET_ALL)
						continue

					if neighbor in ASNs[AS]["neighbors"].keys():
						for new in news:
							if new not in ASNs[AS]["neighbors"][neighbor]:
								ASNs[AS]["neighbors"][neighbor].append(new)
								logging.info(Fore.BLUE + f"ADDED Route to {new} to path between {AS} and {neighbor}, {len(ASNs[AS]['neighbors'][neighbor])} routes left" + Style.RESET_ALL)
							else :
								logging.debug(Fore.YELLOW + f"DIDN'T ADD NOR CREATE : Already existing : Route to {new} to path between {AS} and {neighbor}, {len(ASNs[AS]['neighbors'][neighbor])} routes left" + Style.RESET_ALL)
					else :
						ASNs[AS]["neighbors"][neighbor] = news
						for new in news:
							logging.info(Fore.BLUE + f"ADDED Route to {new} to path between {AS} and {neighbor}, {len(ASNs[AS]['neighbors'][neighbor])} routes left" + Style.RESET_ALL)

			# Delete withdrawn routes

			if AS in ASNs.keys():
				for neighbor in potential_neighbors:
					if neighbor in ASNs[AS]["neighbors"].keys():
						for withdraw in withdrawn:
							try: 
								ASNs[AS]["neighbors"][neighbor].remove(withdraw)
								logging.info(Fore.RED + f"DELETED Route to {new} from path between {AS} and {neighbor}, {len(ASNs[AS]['neighbors'][neighbor])} routes left" + Style.RESET_ALL)
								if len(ASNs[AS]["neighbors"][neighbor]) == 0:
									del ASNs[AS]["neighbors"][neighbor]
									logging.info(Fore.MAGENTA + f"DELETED Neighbor {neighbor} from AS {AS}" + Style.RESET_ALL)

							except:
								#print("Tried to delete route to", withdraw, "from path between", AS, "and", neighbor, ", but the route didn't exist")
								pass



	if AS_TO_DISPLAY in ASNs.keys():
		stdscr.addstr(0, 0, f"AS {AS_TO_DISPLAY} has {len(ASNs[AS_TO_DISPLAY]['neighbors'])} neighbors : " + ', '.join(map(str, ASNs[AS_TO_DISPLAY]['neighbors'].keys())))
		stdscr.refresh()

