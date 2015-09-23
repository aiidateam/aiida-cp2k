#!/usr/bin/python

import xml.etree.ElementTree as ET

import pydot
import matplotlib.pyplot as plt
import networkx as nx

graph=pydot.Dot(graph_type='graph')

xml_parsed = ET.parse('cp2k_input.xml')


root=xml_parsed.getroot()

N_node=0
level=0

min_level=0

max_level=1

def build_tree(parent, parent_name, parent_number):
    global N_node
    global level
    global min_level
    global max_level

    level+=1
    for child in parent:
        #print child.tag, child.attrib
        child_name=child.tag
        if child.tag == "NAME":
            continue
        elif child.tag == "SECTION":            #
            for subchild in child:
                if subchild.tag == "NAME":
                    child_name=subchild.text
#                    if ( child_name != "SWARM" and level == 1)  or child_name == "EACH"  : 
#                        continue
                    print child_name
                    N_node+=1
                    if level > min_level and level <= max_level:
                        edge=pydot.Edge("%s lvl:%d n: %d" % (parent_name,level-1, parent_number) , "%s lvl:%d n: %d" % (child_name,level, N_node ) )
                        graph.add_edge(edge)
                    build_tree(child, child_name, N_node)
        elif child.tag == "KEYWORD" :
            for subchild in child:
                if subchild.tag == "NAME":
                    child_name=subchild.text
                    print child_name
                    N_node+=1
                    if level > min_level and level <= max_level:
                        edge=pydot.Edge("%s lvl:%d n: %d" % (parent_name,level-1, parent_number) , "%s lvl:%d n: %d" % (child_name,level, N_node ) )
                        graph.add_edge(edge)

#        if N_node > 200:
#            break
    level-=1


build_tree(root,"CP2K_INPUT", N_node)
'''
for i in ['asda','asdfasd','as']:
    edge=pydot.Edge("king", i)
    graph.add_edge(edge)
'''




G=nx.from_pydot(graph)

nx.draw_spring(G, with_labels=True, nod_size=10)
plt.show()


#graph.write_svg('result.svg')
