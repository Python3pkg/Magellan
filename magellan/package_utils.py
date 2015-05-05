"""
Module containing Package class.

This is a collection of methods concerning package analysis.

"""

import re


class Package(object):
    """ Package type to hold analysis of packages.
    """

    def __init__(self, name=""):
        self.name = name
        self.key = name.lower()

        self._descendants = []
        self._ancestors = []
        self._node_distances = []
        self._ancestor_trace = []

    def ancestors(self, edges):
        """Packages that this depends on."""
        if not self._ancestors:
            self._ancestors = [x for x in edges if self.key == x[1][0].lower()]
        return self._ancestors

    def descendants(self, edges):
        """Packages that depend on this."""
        if not self._descendants:
            self._descendants = [x for x in edges
                                 if self.key == x[0][0].lower()]
        return self._descendants

    def get_direct_links_to_package(self, edges):
        """Returns direct dependency links from a given package."""
        return self.ancestors(edges), self.descendants(edges)

    def produce_package_report(
            self, pdp_tree_parsed, pdp_errs_parsed, verbose):
        """ Produce package report."""
        from magellan.reports import produce_package_report as ppr
        ppr(self.name, pdp_tree_parsed, pdp_errs_parsed, verbose)

    def calc_node_distances(
            self, packages, nodes, edges, include_root=False,
            keep_untouched_nodes=False, list_or_dict="list",
            do_full_calc=False):
        """ Calculates the distance to a node on an acyclic directed graph.

        :param packages: dictionary of Packages
        :param nodes: list of nodes
        :param edges: list of edges (node links)
        :param include_root=False: whether to include the environment root
        :param keep_untouched_nodes=False: whether to return untouched nodes
        :param list_or_dict="dict": return type
        :rtype: list | dict
        :return: list or dict of nodes and distance

        NB: package name will be a string of just the name, we are
        ignoring version and assuming package name is unique!

        NB: 'root' connects everything, so can skip that node optionally

        Other details:
            Selected package root node (not env 'root') has distance of zero
            Everything begins at -999

        """
        if self._node_distances and not do_full_calc:
            return self._node_distances

        # Define recursive function in _scope_ of calc_node_distance_to fn.
        def rec_fun(search_set, cur_level):
            """ Recursive function to determine distance of connected nodes"""
            to_search_next = []

            for p in search_set:
                if abs(dist_dict[p]) > cur_level:
                    dist_dict[p] = cur_level
                node_touched[p] = True

                anc, dec = packages[p].get_direct_links_to_package(edges)
                if not include_root:
                    anc = [nx for nx in anc if 'root' not in str(nx)]
                    dec = [nx for nx in dec if 'root' not in str(nx)]

                dec_search = [nx[1][0].lower() for nx in dec
                              if not node_touched[nx[1][0].lower()]]
                anc_search = [nx[0][0].lower() for nx in anc
                              if not node_touched[nx[0][0].lower()]]
                to_search_next += dec_search + anc_search

            to_search_next = list(set(to_search_next))  # uniques

            if to_search_next:
                rec_fun(to_search_next, cur_level+1)

            # END OF RECURSIVE FUNCTION #
            # ------------------------- #

        start_distance = -999
        # set up distance dictionary:
        dist_dict = {x[0].lower(): start_distance for x in nodes}
        if include_root:
            dist_dict['root'] = start_distance

        # set up search dictionary:
        node_touched = {x[0].lower(): False for x in nodes}
        if include_root:
            node_touched['root'] = False

        rec_fun([self.key], 0)

        if list_or_dict == "list":
            if keep_untouched_nodes:
                node_distances = [(x[0], x[1], dist_dict[x[0].lower()])
                                  for x in nodes]
            else:
                node_distances = [(x[0], x[1], dist_dict[x[0].lower()])
                                  for x in nodes
                                  if dist_dict[x[0].lower()] > start_distance]
            if include_root:
                node_distances.append(('root', '0.0.0', dist_dict['root']))
        else:  # return type dict
            if keep_untouched_nodes:
                node_distances = {(x[0], x[1]): dist_dict[x[0].lower()]
                                  for x in nodes}
            else:
                node_distances = {(x[0], x[1]): dist_dict[x[0].lower()]
                                  for x in nodes
                                  if dist_dict[x[0].lower()] > start_distance}
            if include_root:
                node_distances[('root', '0.0.0')] = dist_dict['root']

        # Return type dict:
        self._node_distances = node_distances
        return node_distances

    def ancestor_trace(self, nodes, edges, include_root=True,
                       keep_untouched_nodes=False, do_full_calc=False):
        """ Returns dict indicating ancestor trace of package.

        If X depends on Y, then if Y changes it may affect X; not vice versa.
        So if X changes it will not affect Y. Therefore it is the ancestors that
        are affected by their descendants. With this in mind, this routine traces
        the connections of a directed graph, returning only a direct ancestral
        lineage.

        This should indicate what packages are at risk should a package change.

        Implementation, breadth first search but focusing only on upstream links.

        :param nodes: list of nodes
        :param edges: list of edges
        :return: dict indicating ancestor trace of package
        """

        if self._ancestor_trace and not do_full_calc:
            return self._ancestor_trace

        # Define recursive function in _scope_ of calc_node_distance_to fn.
        def rec_fun(search_set, cur_level):
            """ Recursive function to determine distance of connected nodes"""
            to_search_next = []

            for p in search_set:
                if abs(dist_dict[p]) > cur_level:
                    dist_dict[p] = cur_level
                node_touched[p] = True

                anc = p.ancestors(edges)
                if not include_root:
                    anc = [nx for nx in anc if 'root' not in str(nx)]

                anc_search = [nx[0][0].lower() for nx in anc
                              if not node_touched[nx[0][0].lower()]]
                to_search_next += anc_search

            to_search_next = list(set(to_search_next))  # uniques

            if to_search_next:
                rec_fun(to_search_next, cur_level + 1)

                # END OF RECURSIVE FUNCTION #
                # ------------------------- #

        start_dist = -999
        # set up distance dictionary:
        dist_dict = {x[0].lower(): start_dist for x in nodes}
        if include_root:
            dist_dict['root'] = start_dist

        # set up search dictionary:
        node_touched = {x[0].lower(): False for x in nodes}
        if include_root:
            node_touched['root'] = False

        rec_fun([self.key], 0)

        if keep_untouched_nodes:
            anc_trace = {(x[0], x[1]): dist_dict[x[0].lower()] for x in nodes}
        else:
            anc_trace = {(x[0], x[1]): dist_dict[x[0].lower()]
                         for x in nodes
                         if dist_dict[x[0].lower()] > start_dist}
        if include_root:
            anc_trace[('root', '0.0.0')] = dist_dict['root']

        # Return type dict:
        self._ancestor_trace = anc_trace
        return anc_trace

    @staticmethod
    def resolve_package_list(venv, kwargs):
        """Resolve packages into list from cmd line and file.

        Splits on " ", "," and "\n" when reading file.

        :rtype: list
        :return: package_list
        """

        p_list = kwargs['packages']
        p_file = kwargs['package_file']

        f_pkgs = []
        if p_file:
            try:
                with open(p_file, 'rb') as pf:
                    f_pkgs = [x for x in re.split(',|\s|\n', pf.read()) if x != '']
            except IOError as e:
                print("File not found {0}. {1}".format(p_file, e))

        pkg_list = list(set(p_list + f_pkgs))  # uniqs

        ret_pkg_list = []
        for p in pkg_list:
            lo_pac = [x for x in venv.nodes if x[0].lower() == p.lower()]
            if not lo_pac:
                print('"{}" not found in environment package list, '
                      'dropping from packages.'.format(p))
            else:
                ret_pkg_list.append(p)

        return ret_pkg_list