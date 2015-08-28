"""
File executed inside another virtual environment to interrogate the details
of a specific package within that environment.
"""
import json
import os
import pkg_resources
import sys

if len(sys.argv) != 3:
    print("package_interrogation.py requires 2 CL args: package, cache_dir.")
    sys.exit(1)

package = str(sys.argv[1])
cache_dir = sys.argv[2]

p_key = '{0}'.format(package.lower())
# pkgs = pip.get_installed_distributions()
pkgs = [d for d in pkg_resources.working_set]
try:
    p = [x for x in pkgs if x.key == p_key][0]
except IndexError:
    print("Package {} not found in env, installation successful?"
          .format(package))
    sys.exit(1)

req_dic = {'project_name': p.project_name,
           'version': p.version, 'requires': {}}

for r in p.requires():
    req_dic['requires'][r.key] = {}
    req_dic['requires'][r.key]['project_name'] = r.project_name
    req_dic['requires'][r.key]['key'] = r.key
    req_dic['requires'][r.key]['specs'] = r.specs

fn = "{0}_{1}_req.json".format(p.key, p.version.replace(".", "_"))
fn = os.path.join(cache_dir, fn)

json.dump(req_dic, open(fn, 'w'))
