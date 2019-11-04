#!/usr/bin/python3

import glob
import networkx as nx
import sys
import matplotlib.pyplot as plt
import json
import random

DEGREE_DISPLAY_LABEL = 100
DPI = 6000

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

if len(sys.argv) < 2:
	print(f"usage: {sys.argv[0]} filename.gml[.gz]")
	exit(-1)

print(f"Reading {sys.argv[1]}")

ASNs = nx.read_gml(sys.argv[1])

print(len(ASNs.nodes()), "nodes to display")

print("Collection complete")
print("Calculating core")

core = extract_core(ASNs)

print("Positioning")

pos = {}
for node in ASNs.nodes():
	pos[node] = wiggle((0.5, 0.5) if node in core else initial_positions[country_continent[AS_countries[int(node)]]] if node in AS_countries else (0.5,0.5), 0.1)

pos=nx.spring_layout(ASNs, pos=pos)
#pos=nx.kamada_kawai_layout(ASNs, pos=pos)
#pos=nx.spectral_layout(ASNs)
labels = {}

print("Assigning labels")
for node, degree in ASNs.degree():
	if degree > DEGREE_DISPLAY_LABEL:
		labels[node] = node

print("Drawing")
nx.draw(ASNs, pos, arrowstyle="->", with_labels=False, node_color=["r" if x in core else colors[country_continent[AS_countries[int(x)]]] if x in AS_countries else "black" for x in ASNs.nodes()], node_size=[3*x**(2/3) for _, x in ASNs.degree()], width=0.3, edge_color="grey", alpha=0.7)

print("drawing labels")
nx.draw_networkx_labels(ASNs, pos, labels, font_size=8)

plt.savefig("out,png", dpi=DPI)

plt.show()

