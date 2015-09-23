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

max_level=100000

def build_tree(parent, parent_name, parent_number):
    global N_node
    global level
    global min_level
    global max_level
    return_value=False

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
                    N_node+=1
                    n_node_print_here=N_node
                    if child_name == "PRINT":
                        print child_name
                        return_value=True
                        edge=pydot.Edge("%s lvl:%d n: %d" % (parent_name,level-1, parent_number) , "%s lvl:%d n: %d" % (child_name,level,n_node_print_here  ) )
                        graph.add_edge(edge)
                    if True == build_tree(child, child_name, N_node)  :
                        edge=pydot.Edge("%s lvl:%d n: %d" % (parent_name,level-1, parent_number) , "%s lvl:%d n: %d" % (child_name,level,n_node_print_here  ) )
                        print "Hey"
                        graph.add_edge(edge)
                        return_value=True

    level-=1
    return return_value


build_tree(root,"CP2K_INPUT", N_node)
'''
for i in ['asda','asdfasd','as']:
    edge=pydot.Edge("king", i)
    graph.add_edge(edge)
'''




G=nx.from_pydot(graph)
nx.draw_spring(G, with_labels=True, nod_size=10, node_color="blue")
#nx.draw(G,pos=nx.spectral_layout(G), nodecolor='r',edge_color='b')
graph.write_svg('result.svg')
plt.show()


