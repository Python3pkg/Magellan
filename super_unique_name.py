
from pprint import pprint
import pickle
import pip

#default_skip = ['setuptools', 'pip', 'python', 'distribute'] # something is relying on setuptools, apparently
default_skip = ['pip', 'python', 'distribute']
skip = default_skip + ['pipdeptree', 'virtualenv', 'magellan']
local_only = True
pkgs = pip.get_installed_distributions(local_only=local_only,
                                        skip=skip)

# FORM NODES
nodes = [(x.project_name, x.version) for x in pkgs]

# FORM EDGES
installed_vers = {x.key: x.version for x in pkgs}
edges = []
for p in pkgs:
    p_tup = (p.project_name, p.version)
    edges.append([('root','0.0.0'), p_tup])
    reqs = p.requires()
    if reqs:
        for r in reqs:
            if r.key in installed_vers:
                r_tup = (r.key, installed_vers[r.key])
            else:
                r_tup = (r.key)
            edges.append([p_tup, r_tup, r.specs])

# Output:
#for node in nodes:
#    print("N#{}".format(node))
#for edge in edges:
#    print("E#{}".format(edge))

# Record nodes and edges to disk to be read in  by main program if needed (saves parsing)
pickle.dump(nodes, open('nodes.p','wb'))
pickle.dump(edges, open('edges.p','wb'))
