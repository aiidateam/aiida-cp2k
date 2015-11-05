import os, re


# import glob
pos_regex = re.compile("""
        (?P<sym>[a-zA-Z0-9]+)\s+
        (?P<x>[-]?\d+[\.]?\d+([E | e][+|-]?\+)?)\s+
        (?P<y>[-]?\d+[\.]?\d+([E | e][+|-]?\+)?)\s+
        (?P<z>[-]?\d+[\.]?\d+([E | e][+|-]?\+)?)""", re.X)
pos_block_regex = re.compile("""
            (
                \s*   #White space in the beginning (maybe)
                [A-Za-z0-9]+  #A tag for a species
                (
                   \s+ [-]?\d+[\.]?\d+([E | e][+|-]?\+)?  #The number   ([E | e][+|-]?[0-9]+)?)?
                ){3} 
                \s* [\n] #White space and line break in the end
            )+ #A block should one or more lines
            """, re.X | re.M)
#~ all_positions =  [(match.group('sym'), float(match.group('x')) ,float(match.group('y')) ,float(match.group('z')))
                    #~ for match in pos_regex.finditer(traj_txt)])
                    #~ 

return_last = False

xyz_txt = open('pos.xyz').read()

blocks = [block for block in  pos_block_regex.finditer(xyz_txt)]
if return_last:
    block = blocks[-1]
    print [(match.group('sym'), float(match.group('x')) ,float(match.group('y')) ,float(match.group('z'))) 
        for  match in pos_regex.finditer(block.group(0))]
else:
    print [[(match.group('sym'), float(match.group('x')) ,float(match.group('y')) ,float(match.group('z'))) 
        for  match in pos_regex.finditer(block.group(0))] 
            for block in blocks]
#~ print len(blocks)
#~ print xyz_txt[:10000]
#~ blocks = pos_block_regex.findall(xyz_txt)
#~ print blocks[0]
#~ print len(blocks)
#~ all_positions =  [(match.group('sym'), float(match.group('x')) ,float(match.group('y')) ,float(match.group('z')))
                    #~ for match in pos_regex.finditer(blocks[-1])]
                    
#~ print all_positions
#~ print len(blocks)
