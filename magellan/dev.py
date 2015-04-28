#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Playground for various ideas. Nothing to see here, move along...
"""

from pprint import pprint

from analysis import (write_dot_graph_to_disk, query_nodes_eges_in_venv,
                      calc_node_distances, write_dot_graph_to_disk_with_distance_colour,
                      direct_links_to_package, ancestor_trace,
                      calc_weighted_connections, calc_connected_nodes,
                      write_dot_graph_subset)


def scratchpad():
    """Playground for various ideas. Nothing to see here, move along..."""

    nodes, edges = query_nodes_eges_in_venv('D16/bin/')
    package = 'whowhatwhere'

    # Attempt to see if a package is out of date.

    # anc_track = ancestor_trace(package, nodes, edges)
    # write_dot_graph_to_disk_with_distance_colour(nodes, edges, '{}_anc_track.gv'.format(package), anc_track)
    # write_dot_graph_subset(nodes, edges, '{}_anc_track_trunc.gv'.format(package), anc_track)

    from distutils.version import StrictVersion, LooseVersion
    from pkg_resources import parse_version
    import yarg

    yp = yarg.get(package)
    sv = [x[1] for x in nodes if x[0] == package][0]

    print(package, sv)

    rels = yp.release_ids

    rels.sort(key=LooseVersion)

    pprint(rels)

    major_outdated = parse_version(sv) < parse_version(rels[-1])

    print("Package: {}  Versions: {}".format(yp, sv))
    if major_outdated:
        print("MAJOR OUTDATED")
        print(rels[-1])
        major_v = sv.split('.')[0]
        minor_v = sv.split('.')[1]

        minor_rels = [x for x in rels if x.split('.')[0]==major_v and x.split('.')[1]==minor_v]
        minor_outdated = parse_version(sv) < parse_version(minor_rels[-1])
        if minor_outdated:
            print("MINOR OUTDATED")
            print(minor_rels[-1])
        else:
            print("Minor up to date.")

    else:
        print("All up to date")



