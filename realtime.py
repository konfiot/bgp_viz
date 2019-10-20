import json
import websocket
import logging
import curses
import signal
import sys
import glob
import math
import json
import random
import time
from datetime import datetime
import networkx as nx
from colorama import Fore, Back, Style, init
import matplotlib.pyplot as plt

AS_TO_DISPLAY = 513 # CERN
AS_TO_DISPLAY = 15169 # Google

DEGREE_DISPLAY_LABEL = 50

MESSAGES_TO_GATHER = 1e5
#MESSAGES_TO_GATHER = 1e2

#SAVE_INTERVAL = 60*2
SAVE_INTERVAL = 10

DISPLAY = False
SAVE = True

def extract_core(ASNs):
	cont = True
	G = ASNs.copy()
	while cont:
		cont = False
		for node, degree in G.copy().degree():
			if degree <= 2:
				G.remove_node(node)
				cont = True
	return G.nodes()

def wiggle(t, r):
	a,b = t
	a += random.uniform(-r,r)
	b += random.uniform(-r,r)
	return (a,b)

def restore_terminal(signal, frame):
	curses.echo()
	curses.nocbreak()
	curses.endwin()
	sys.exit(0)

init() # Init colors

# Init curses
#stdscr = curses.initscr()
#curses.noecho()
#curses.cbreak()


signal.signal(signal.SIGINT, restore_terminal)
signal.signal(signal.SIGTERM, restore_terminal)

# Create ASN to countries mapping
AS_countries = {}
AS_files = glob.glob("./db/*_asn")
for AS_file in AS_files:
	with open(AS_file, "r") as AS_fd:
		line = AS_fd.readline()
		while line:
			AS = int(line[2:].strip())
			country = AS_file.split("/")[-1][0:2].upper()
			AS_countries[AS] = country

			line = AS_fd.readline()

country_continent = {}
with open("continents.json", "r") as continent_file:
	continents = json.load(continent_file)
	for continent in continents:
		country_continent[continent["Two_Letter_Country_Code"]] = continent["Continent_Name"]

colors = {
	"Antartica": "skyblue",
	"Asia": "yellow",
	"Africa": "violet",
	"Europe": "blue",
	"North America": "tan",
	"Oceania": "seagreen",
	"South America": "orange"
}

initial_positions = {
	"Antartica": (0.1, 0.1),
	"Asia": (0.9, 0.5),
	"Africa": (0.5, 0.1),
	"Europe": (0.5, 0.9),
	"North America": (0.1, 0.9),
	"Oceania": (0.9, 0.1),
	"South America": (0.1,0.5)
}

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

messages_recieved = 0

last_time_saved = time.time()

for data in ws:
	messages_recieved+=1

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

				new_subnets = (subnets | news) - withdrawn
				ASNs.add_edge(int(AS), int(neighbor), subnets = new_subnets, weight=len(new_subnets))

					#logging.info(Fore.GREEN + f"CREATED Route to {new} to path between {AS} and {neighbor}, {len(ASNs[AS]['neighbors'][neighbor])} routes left" + Style.RESET_ALL)


	# Save
	if SAVE and time.time() - last_time_saved >= SAVE_INTERVAL:
		filename = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
		print("Saving graph,", len(ASNs.nodes), "nodes...", end="")
		nx.readwrite.gml.write_gml(ASNs, f"out/{filename}.gml.gz", stringizer=lambda x: str(list(x)))
		print(" Saved")
		last_time_saved = time.time()


	# Display
	if DISPLAY and ASNs.has_node(AS_TO_DISPLAY) and messages_recieved > MESSAGES_TO_GATHER:
		print(len(ASNs.nodes()), "nodes to display")

		print("Collection complete")
		print("Calculating core")

		core = extract_core(ASNs)

		print("Positioning")

		pos = {}
		for node in ASNs.nodes():
			pos[node] = wiggle((0.5, 0.5) if node in core else initial_positions[country_continent[AS_countries[node]]] if node in AS_countries else (0.1,0.1), 0.1)

		pos=nx.spring_layout(ASNs, pos=pos)
		#pos=nx.kamada_kawai_layout(ASNs, pos=pos)
		#pos=nx.spectral_layout(ASNs)
		labels = {}
		
		print("Assigning labels")
		for node, degree in ASNs.degree():
			if degree > DEGREE_DISPLAY_LABEL:
				labels[node] = node

		print("Drawing")
		nx.draw(ASNs, pos, arrowstyle="->", with_labels=False, node_color=["r" if x in core else colors[country_continent[AS_countries[x]]] if x in AS_countries else "black" for x in ASNs.nodes()], node_size=[3*x**(2/3) for _, x in ASNs.degree()], width=0.3, edge_color="grey", alpha=0.7)

		print("drawing labels")
		nx.draw_networkx_labels(ASNs, pos, labels, font_size=8)

		plt.show()

		print(f"AS {AS_TO_DISPLAY} has {len(list(nx.all_neighbors(ASNs, AS_TO_DISPLAY)))} neighbors : " + ', '.join(map(str, [x for _, x in nx.all_neighbors(ASNs, AS_TO_DISPLAY)])))

		exit(0)
	elif DISPLAY:
		print(int((messages_recieved/MESSAGES_TO_GATHER)*100), "% complete", end="\r")
