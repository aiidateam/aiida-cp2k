# -*- coding: utf-8 -*-

import os, re, sys

RE_FLAGS = re.M | re.X 


testtxt = """
H GTH-BLYP-q1
    1 3 5
     0.20000000    2    -4.19596147     0.73049821
     0.20000000    2    -4.19596147     0.73049821
     0.20000000    2    -4.19596147     0.73049821
     0.20000000    2    -4.19596147     0.73049821
    0
     0.20000000    2    -4.19596147     0.73049821
     0.20000000    2    -4.19596147     0.73049821
     0.20000000    2    -4.19596147     0.73049821
    0
     0.20000000    2    -4.19596147     0.73049821
     0.20000000    2    -4.19596147     0.73049821
     0.20000000    2    -4.19596147     0.73049821
    0
#
He GTH-BLYP-q2
    2
     0.20000000    2    -9.14737128     1.71197792
    0
H GTH-PADE-q1 GTH-LDA-q1
    1
     0.20000000    2    -4.18023680     0.72507482
    0

#
"""
       
        
potentials_regex = re.compile("""
        [A-Z][a-z]{0,1}([ \t]+[-\w]+)+\s*  #The first line, an element followed by basis set name (for some an alternative name is given after): H GTH-PADE-q1 [GTH-LDA-q1}
        (([ \t]*[0-9])+\s*  #The next lines are a bunch of integers
        (( [ \t]*[\.\d-]+)+ \s*)+)+ #This matches a bunch of floats
        """, RE_FLAGS)
        
#~ potentials_regex = re.compile("[A-Z][a-z]{0,1}[ \t]+[-\w]+[ \t]*\n", RE_FLAGS)
        #(\s*[\.\d]+)+\s* \n #The next lines are a bunch of numbers and spaces
filename  = 'GTH_POTENTIALS'

#~ txt = open(filename).read()
txt = testtxt 
#~ print  potentials_regex.search(txt).group(0)
for chunk in potentials_regex.finditer(txt):
    print chunk.group(0)
    raw_input()
