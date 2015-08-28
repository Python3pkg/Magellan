import pickle
import pkg_resources

default_skip = ['pip', 'python', 'distribute']
skip = ['pipdeptree', 'magellan', 'vex'] \
       + default_skip

# local_only = True
# pkgs = pip.get_installed_distributions(local_only=local_only,
#                                        skip=skip+default_skip)
pkgs = [d for d in pkg_resources.working_set if d.key not in skip]


# FORM NODES
nodes = [(x.project_name, x.version) for x in pkgs]

# FORM EDGES
installed_versions = {x.key: x.version for x in pkgs}
edges = []
for p in pkgs:
    p_tup = (p.project_name, p.version)
    edges.append([('root', '0.0.0'), p_tup])
    reqs = p.requires()
    if reqs:
        for r in reqs:
            if r.key in installed_versions:
                r_tup = (r.key, installed_versions[r.key])
            else:
                r_tup = (r.key, '')
            edges.append([p_tup, r_tup, r.specs])

# Record nodes and edges to disk to be read in  by main program if needed.
pickle.dump(nodes, open('nodes.p', 'w'), protocol=2)
pickle.dump(edges, open('edges.p', 'w'), protocol=2)

# Was having issues with pickle so writing custom dict.
pkgs_out = {}
for p in pkgs:
    pkgs_out[p.key] = {}
    pkgs_out[p.key]['project_name'] = p.project_name
    pkgs_out[p.key]['version'] = p.version
    pkgs_out[p.key]['requires'] = {}
    for r in p.requires():
        pkgs_out[p.key]['requires'][r.key] = {}
        pkgs_out[p.key]['requires'][r.key]['project_name'] = r.project_name
        pkgs_out[p.key]['requires'][r.key]['specs'] = r.specs

pickle.dump(pkgs_out, open('package_requirements.p', 'w'), protocol=2)
