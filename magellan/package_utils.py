"""
Module containing Package class.

This is a collection of methods concerning packages and their analysis.
"""

import re


class PackageException(Exception):
    pass


class InvalidEdges(PackageException):
    pass


class Package(object):
    """ Package type to hold analysis of packages."""

    def __init__(self, name="", version=None):
        self.name = name
        self.key = name.lower()

        self.version = version
        self.versions = {}

        self._descendants = []
        self._ancestors = []
        self._node_distances = {}
        self._ancestor_trace = []

    def check_versions(self):
        """Checks the major and minor versions (PyPI), compares to current."""
        return self.check_latest_major_minor_versions(self.name, self.version)

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

    def calc_self_node_distances(
            self, venv, include_root=False, keep_untouched_nodes=False,
            list_or_dict="dict", do_full_calc=False):
        """
        Calculates the distance to a node on an acyclic directed graph.

        :param venv: virtual env containing nodes and edges
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

        if not self._node_distances or do_full_calc:
            self._node_distances = self.calc_node_distances(
                self.name, venv.nodes, venv.edges, include_root,
                keep_untouched_nodes, list_or_dict)

        return self._node_distances

    def ancestor_trace(self, venv, include_root=True,
                       keep_untouched_nodes=False, do_full_calc=False):
        """
        Returns dict indicating ancestor trace of package.

        If X depends on Y, then if Y changes it may affect X; not vice versa.
        So if X changes it will not affect Y. Therefore it is the ancestors
        that are affected by their descendants. With this in mind, this
        routine traces the connections of a directed graph, returning only a
        direct ancestral lineage.

        This should indicate what packages are at risk should a package change.

        Implementation, breadth first search but focusing on upstream links.

        :param Environment venv: virtual env containing nodes and edges
        :return: dict indicating ancestor trace of package
        """

        if self._ancestor_trace and not do_full_calc:
            return self._ancestor_trace

        # Define recursive function in _scope_ of calc_node_distance_to fn.
        def rec_fun(search_set, cur_level):
            """Recursive function to determine distance of connected nodes"""
            to_search_next = []

            for p in search_set:
                if abs(dist_dict[p]) > cur_level:
                    dist_dict[p] = cur_level
                node_touched[p] = True

                # anc = p.ancestors(edges)
                anc, _ = self.get_direct_links_to_any_package(p, venv.edges)

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
        dist_dict = {x[0].lower(): start_dist for x in venv.nodes}
        if include_root:
            dist_dict['root'] = start_dist

        # set up search dictionary:
        node_touched = {x[0].lower(): False for x in venv.nodes}
        if include_root:
            node_touched['root'] = False

        rec_fun([self.key], 0)

        if keep_untouched_nodes:
            anc_trace = {(x[0], x[1]): dist_dict[x[0].lower()]
                         for x in venv.nodes}
        else:
            anc_trace = {(x[0], x[1]): dist_dict[x[0].lower()]
                         for x in venv.nodes
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
                    f_pkgs = [x for x in re.split(',|\s|\n', pf.read())
                              if x != '']
            except IOError as e:
                print("File not found {0}. {1}".format(p_file, e))

        pkg_list = list(set(p_list + f_pkgs))  # uniqs - hashable only...

        ret_pkg_list = []
        for p in pkg_list:
            lo_pac = [x for x in venv.nodes if x[0].lower() == str(p).lower()]
            if not lo_pac:
                print('"{}" not found in environment package list, '
                      'dropping from packages.'.format(p))
            else:
                ret_pkg_list.append(p)

        return ret_pkg_list

    @staticmethod
    def calc_node_distances(
            package, nodes, edges, include_root=False,
            keep_untouched_nodes=False, list_or_dict="list"):

        """
        Calculates the distance to a node on an acyclic directed graph.

        :param package: package to calculate distances from
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

        # Define recursive function in scope of calc_node_distance_to fn.
        def rec_fun(search_set, cur_level):
            """ Recursive function to determine distance of connected nodes"""
            to_search_next = []

            for p in search_set:
                if abs(dist_dict[p]) > cur_level:
                    dist_dict[p] = cur_level
                node_touched[p] = True

                anc, dec = Package.get_direct_links_to_any_package(p, edges)

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

        rec_fun([package.lower()], 0)

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
        return node_distances

    @staticmethod
    def get_direct_links_to_any_package(package, edges):
        """
        :param package: package to find ancestors and descendants for.
        :param edges: connections in the graph
        :return: ancestors and descendants.
        """
        if not hasattr(edges, "__iter__") or not edges:
            raise InvalidEdges

        ancestors = [x for x in edges if package.lower() == x[1][0].lower()]
        descendants = [x for x in edges if package.lower() == x[0][0].lower()]
        return ancestors, descendants

    @staticmethod
    def get_package_versions_from_pypi(package):
        """
        Query PyPI for latest versions of package, return in order.

        return list: version info
        """
        from distutils.version import LooseVersion
        import yarg

        try:
            yp = yarg.get(package)
            rels = yp.release_ids
        except yarg.HTTPError as e:
            print("{0} not found at PyPI; "
                  "no version information available.".format(package))
            # log e
            return None

        rels.sort(key=LooseVersion)
        if not rels:
            print('No version info available for "{}" at CheeseShop (PyPI)'
                  .format(package))
            return None

        return rels

    @staticmethod
    def check_latest_major_minor_versions(package, version):
        """
        Compare 'version' to latest major and minor versions on PyPI.
        """
        from pkg_resources import parse_version

        versions = Package.get_package_versions_from_pypi(package)
        if versions is None:
            # Something went wrong when looking for versions:
            return [None, None], [None, None]

        latest_major_version = versions[-1]
        minor_outdated = None
        major_outdated = (parse_version(version)
                          < parse_version(latest_major_version))

        if major_outdated:
            print("{0} Major Outdated: {1} > {2}"
                  .format(package, versions[-1], version))
            major_v = version.split('.')[0]
            minor_v = version.split('.')[1]

            minor_versions = [x for x in versions
                              if x.split('.')[0] == major_v
                              and x.split('.')[1] == minor_v]

            if not minor_versions:
                print("Unable to check minor_versions for {0}"
                      .format(package))
                latest_minor_version = None
            else:
                latest_minor_version = minor_versions[-1]
                minor_outdated = (parse_version(version)
                                  < parse_version(latest_minor_version))
                if minor_outdated:
                    print("{0} Minor Outdated: {1} > {2}"
                          .format(package, minor_versions[-1], version))
                    minor_outdated = True
                else:
                    print("{0} Minor up to date: {1} <= {2}"
                          .format(package, minor_versions[-1], version))
        else:
            minor_outdated = False
            latest_minor_version = latest_major_version
            print("{0} up to date, current: {1}, latest: {2}"
                  .format(package, version, versions[-1]))

        min_ret = [minor_outdated, latest_minor_version]
        maj_ret = [major_outdated, latest_major_version]
        return min_ret, maj_ret
