all_positions =  [(match.group('sym'), float(match.group('x')) ,float(match.group('y')) ,float(match.group('z')))
                    for match in pos_regex.finditer(traj_txt)])
                    import os, re
# import glob
pos_regex = re.compile('^(?P<sym>[a-zA-Z0-9]+)\s+(?P<x>[\-]?\d+\.\d+)\s+(?P<y>[\-]?\d+\.\d+)\s+(?P<z>[\-]?\d+\.\d+)$'
pos_block_regex = re.compile("""
            ([ \t]* [A-Z][a-z]?  ([ \t]+ [-]?[0-9]+([\.][0-9]+([E | e][+|-]?[0-9]+)?)?){3} [ \t]* [\n])+
            """, re.X | re.M)



xyz_txt = open('pos.xyz').read()


print len(pos_regex.findall(xyz_txt))
