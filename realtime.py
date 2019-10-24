import orjson as json
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
import multiprocessing
from datetime import datetime
import networkx as nx
from colorama import Fore, Back, Style, init
import matplotlib.pyplot as plt

DEGREE_DISPLAY_LABEL = 50

MESSAGES_TO_GATHER = 1e5
#MESSAGES_TO_GATHER = 1e2

SAVE_INTERVAL = 60*30
#SAVE_INTERVAL = 10

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

def save_graph(ASNs):
	print("Saving graph,", len(ASNs.nodes), "nodes,", len(ASNs.edges()), "edges...", end="")
	for edge in ASNs.edges(data=True):
		edge[2]["subnets"] = list(edge[2]["subnets"].keys())
	nx.readwrite.gml.write_gml(ASNs, f"out/{filename}.gml.gz", stringizer=nx.readwrite.gml.literal_stringizer)
	print(" Saved")


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

params = {
	"moreSpecific": False,
	#"host": "rrc21",
	"type": "UPDATE",
	#"prefix": "216.238.254.0/23",
	#"path": str(AS_TO_DISPLAY),
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

						ASNs.add_edge(AS, neighbor, subnets = subnets, weight=len(subnets))

							#logging.info(Fore.GREEN + f"CREATED Route to {new} to path between {AS} and {neighbor}, {len(ASNs[AS]['neighbors'][neighbor])} routes left" + Style.RESET_ALL)


			# Save
			if SAVE and time.time() - last_time_saved >= SAVE_INTERVAL:
				filename = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
				save_process = multiprocessing.Process(target=save_graph, args=(ASNs.copy(),))
						
				save_process.start()

				last_time_saved = time.time()
	except websocket._exceptions.WebSocketConnectionClosedException:
		print("Socket closed, retrying")
		pass


	# Display
#	if DISPLAY and messages_recieved > MESSAGES_TO_GATHER:
#		print(len(ASNs.nodes()), "nodes to display")
#
#		print("Collection complete")
#		print("Calculating core")
#
#		core = extract_core(ASNs)
#
#		print("Positioning")
#
#		pos = {}
#		for node in ASNs.nodes():
#			pos[node] = wiggle((0.5, 0.5) if node in core else initial_positions[country_continent[AS_countries[node]]] if node in AS_countries else (0.5,0.5), 0.1)
#
#		pos=nx.spring_layout(ASNs, pos=pos)
#		#pos=nx.kamada_kawai_layout(ASNs, pos=pos)
#		#pos=nx.spectral_layout(ASNs)
#		labels = {}
#		
#		print("Assigning labels")
#		for node, degree in ASNs.degree():
#			if degree > DEGREE_DISPLAY_LABEL:
#				labels[node] = node
#
#		print("Drawing")
#		nx.draw(ASNs, pos, arrowstyle="->", with_labels=False, node_color=["r" if x in core else colors[country_continent[AS_countries[x]]] if x in AS_countries else "black" for x in ASNs.nodes()], node_size=[3*x**(2/3) for _, x in ASNs.degree()], width=0.3, edge_color="grey", alpha=0.7)
#
#		print("drawing labels")
#		nx.draw_networkx_labels(ASNs, pos, labels, font_size=8)
#
#		plt.show()
#
#		exit(0)
#	elif DISPLAY:
#		print(int((messages_recieved/MESSAGES_TO_GATHER)*100), "% complete", end="\r")
