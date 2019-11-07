import networkx as nx
import sys
from datetime import datetime
import time

def save_graph(ASNs):
	filename = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H%M')
	print("Saving graph,", len(ASNs.nodes), "nodes,", len(ASNs.edges()), "edges...", end="")
	for edge in ASNs.edges(data=True):
		edge[2]["subnets"] = list(edge[2]["subnets"].keys())
	nx.readwrite.gml.write_gml(ASNs, f"{sys.argv[1]}/{filename}.gml.gz", stringizer=nx.readwrite.gml.literal_stringizer)
	print(" Saved")


def update_graph(ASNs, AS, neighbor, news, withdrawn):
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
