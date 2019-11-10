#!/usr/bin/python3

import glob
import networkx as nx
import matplotlib.pyplot as plt
import json
import random
import numpy as np

#DEGREE_DISPLAY_LABEL = 100
#DPI = 600 # tu te calmes

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

def load_AS_countries():
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
	return AS_countries

def load_country_continent():
	country_continent = {}
	with open("continents.json", "r") as continent_file:
		continents = json.load(continent_file)
		for continent in continents:
			country_continent[continent["Two_Letter_Country_Code"]] = continent["Continent_Name"]
	return country_continent




def do_stats(args) :
	ASNs = nx.convert_node_labels_to_integers(nx.read_gml(args.file))

	print(len(ASNs.nodes()), "nodes")
	print(len(ASNs.edges()), "edges")

	A = nx.adjacency_matrix(ASNs)
	print('Average degree : ', np.mean(np.sum(A, axis = 1)))

def do_adjimg(args):
	ASNs = nx.convert_node_labels_to_integers(nx.read_gml(args.file))
	# get adj matrix
	A = nx.adjacency_matrix(ASNs)

	# replace weighted entries with 1 for adj visualization
	A[A>0] = 1

	plt.imshow(A.todense())

	if args.output_file is not None:
		plt.savefig(args.output_file, dpi=args.dpi)

	plt.title('Adjacency Matrix (unweighted)')
	plt.show()

def do_graph(args):
	AS_countries = load_AS_countries()
	country_continent = load_country_continent()

	ASNs = nx.convert_node_labels_to_integers(nx.read_gml(args.file))

	core = extract_core(ASNs)

	print("Positioning")

	pos = {}
	for node in ASNs.nodes():
		pos[node] = wiggle((0.5, 0.5) if node in core else initial_positions[country_continent[AS_countries[node]]] if node in AS_countries else (0.5,0.5), 0.1)

	if args.layout == "spring":
		pos=nx.spring_layout(ASNs, pos=pos)
	elif args.layout == "kamada-kawai":
		pos=nx.kamada_kawai_layout(ASNs, pos=pos)
	elif args.layout == "spectral":
		pos=nx.spectral_layout(ASNs, pos=pos)
	elif args.layout == "planar":
		pos=nx.planar_layout(ASNs, pos=pos)
	elif args.layout == "random":
		pos=nx.random_layout(ASNs, pos=pos)
	elif args.layout == "shell":
		pos=nx.shell_layout(ASNs, pos=pos)

	labels = {}

	if args.degree_display is not None :
		print("Assigning labels")
		for node, degree in ASNs.degree():
			if degree > args.degree_display:
				labels[node] = node

	print("Drawing")
	nx.draw(ASNs, pos, arrowstyle="->", with_labels=False, node_color=["r" if x in core else colors[country_continent[AS_countries[x]]] if x in AS_countries else "black" for x in ASNs.nodes()], node_size=[3*x**(2/3) for _, x in ASNs.degree()], width=0.3, edge_color="grey", alpha=0.7)

	if args.degree_display is not None :
		print("drawing labels")
		nx.draw_networkx_labels(ASNs, pos, labels, font_size=8)

	if args.output_file is not None:
		plt.savefig(args.output_file, dpi=args.dpi)

	plt.show()

