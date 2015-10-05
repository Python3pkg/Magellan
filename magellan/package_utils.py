"""
Module containing Package class.

This is a collection of methods concerning packages and their analysis.
"""

from __future__ import print_function

import logging
import re

from natsort import natsorted
import yarg

from magellan.utils import print_col

# Logging:
maglog = logging.getLogger("magellan_logger")
maglog.info("Env imported")


class PackageException(Exception):
    pass


class InvalidEdges(PackageException):
    pass


class InvalidNodes(PackageException):
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
        self._node_distances = {'list': None, 'dict': None}
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

    def ancestor_trace(self, venv, keep_untouched_nodes=False,
                       do_full_calc=False):
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

        include_root = True

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

        p_list = kwargs.get('packages', [])
        p_file = kwargs.get('package_file', [])
        f_pkgs = []
        if p_file:
            try:
                with open(p_file, 'r') as pf:
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
    def get_direct_links_to_any_package(package, edges):
        """
        :param package: package to find ancestors and descendants for.
        :param edges: connections in the graph
        :return: ancestors and descendants.
        """
        if not hasattr(edges, "__iter__") \
                or not edges or type(edges) is not list:
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

        try:
            yp = yarg.get(package)
            rels = yp.release_ids
        except Exception as e:
            maglog.debug("Unable to obtain {0} from PyPI; {1}."
                         .format(package, e))
            # log e
            return None

        rels = natsorted(rels)
        if not rels:
            maglog.info('No version info available for "{}" '
                        'at CheeseShop (PyPI)'.format(package))
            return None

        return rels

    @staticmethod
    def check_outdated_packages(package_list, pretty=False):
        """
        Convenience function to print major/minor versions based on filtered
        input.

        :param package_list: dict of magellan.package_utils.Package objects
        """

        for p_k, p in package_list.items():
            version_info = p.check_versions()
            maglog.debug(version_info)
            Package.detail_version_info(
                version_info, p.name, p.version, pretty)

    @staticmethod
    def detail_version_info(version_info, package, version, pretty=False):
        """
        Outputs to console the result of
        Package.check_latest_major_minor_versions
        """
        print_col("Analysing {} {}".format(package, version),
                  pretty=pretty, header=True)

        status = version_info.get("code")

        if status == -1:  # Error
            print_col("There was an error, see [super] verbose output "
                      "for details", pretty=pretty)
        elif status == 0:  # Up to date
            print_col("Up to date.", pretty=pretty)
        elif status == 999:  # beyond
            print_col("{} is BEYOND latest PyPI version {}".format(
                version,
                version_info.get("minor_version").get("latest")),
                pretty=pretty)
        else:
            maj_out = version_info.get("major_version").get("outdated")
            min_out = version_info.get("minor_version").get("outdated")
            if maj_out:
                print_col("Major version outdated {} > {}".format(
                    version_info.get("major_version").get("latest"),
                    version), pretty=pretty)
            if min_out:
                print_col("Minor version outdated {} > {}".format(
                    version_info.get("minor_version").get("latest"),
                    version), pretty=pretty)

    @staticmethod
    def check_latest_major_minor_versions(package, version=None):
        """
        Compare 'version' to latest major and minor versions on PyPI.

        Status codes:
        -1 : error
        0 : fine, up to date
        1 : minor or major outdated
        999: beyond latest version
        """
        from pkg_resources import parse_version

        return_info = {"major_version": {"outdated": None,
                                         'latest': None},
                       "minor_version": {"outdated": None,
                                         'latest': None},
                       "code": -1,
                       }

        versions = Package.get_package_versions_from_pypi(package)
        if versions is None:
            maglog.debug("Something went wrong when looking for versions.")
            return return_info

        latest_major_version = versions[-1]

        if version is None:
            # If not given a version, cannot do comparison; return latest.
            return_info['major_version'] = {
                "outdated": True, "latest": latest_major_version}
            return_info['minor_version'] = {
                "outdated": True, "latest": latest_major_version}
            return return_info

        beyond_up_to_date = (parse_version(version) >
                             parse_version(latest_major_version))
        if beyond_up_to_date:
            maglog.info("{0} version {1} is beyond latest PyPI version {2}"
                        .format(package, version, latest_major_version))
            # If beyond up to date then latest version is not the PyPI ver.
            return_info['code'] = 999
            return_info['major_version'] = {
                "outdated": False, "latest": latest_major_version}
            return_info['minor_version'] = {
                "outdated": False, "latest": latest_major_version}
            return return_info

        # Now normal checks:
        return_info['code'] = 0
        minor_outdated = None
        major_outdated = (parse_version(version)
                          < parse_version(latest_major_version))

        if major_outdated:
            return_info['code'] = 1
            maglog.info("{0} Major Outdated: {1} > {2}"
                        .format(package, versions[-1], version))
            major_v = version.split('.')[0]
            minor_v = version.split('.')[1]

            minor_versions = [x for x in versions
                              if x.split('.')[0] == major_v
                              and x.split('.')[1] == minor_v]

            if not minor_versions:
                maglog.info("Unable to check minor_versions for {0}"
                            .format(package))
                latest_minor_version = None
            else:
                latest_minor_version = minor_versions[-1]
                minor_outdated = (parse_version(version)
                                  < parse_version(latest_minor_version))
                if minor_outdated:
                    return_info['code'] = 1
                    maglog.info("{0} Minor Outdated: {1} > {2}"
                                .format(package, minor_versions[-1], version))
                    minor_outdated = True
                else:
                    maglog.info("{0} Minor up to date: {1} <= {2}"
                                .format(package, minor_versions[-1], version))
        else:
            minor_outdated = False
            latest_minor_version = latest_major_version
            maglog.info("{0} up to date, current: {1}, latest: {2}"
                        .format(package, version, versions[-1]))

        return_info['major_version'] = {
            "outdated": major_outdated, "latest": latest_major_version}
        return_info['minor_version'] = {
            "outdated": minor_outdated, "latest": latest_minor_version}
        return return_info


class Requirements(object):

    @staticmethod
    def parse_req_file(req_file=None):
        """
        We're import pip to parse the requirements files; but as pip in a
        CL tool this is perhaps not guaranteed to be future proof.

        :param req_file:
        :return: generator object of parsed requiremnets.
        """
        if req_file:
            from pip.req import parse_requirements
            from pip.download import PipSession
            return parse_requirements(req_file, session=PipSession())
        return []

    @staticmethod
    def check_outdated_requirements_file(req_file=None, pretty=None):
        """
        Reads a requirements file and prints whether the major or minor
        versions are outdated.
        """

        parsed_req = Requirements.parse_req_file(req_file)
        if not parsed_req:
            return None

        no_version_info = []
        for p in parsed_req:
            package = p.req.key

            try:
                version = p.req.specs[-1][-1]
            except IndexError as e:
                maglog.debug("No version info for {} in requirements file."
                             .format(package))
                no_version_info.append(package)
                continue

            ver_info = Package.check_latest_major_minor_versions(
                package, version)
            Package.detail_version_info(
                ver_info, package, version, pretty)

        if no_version_info:
            header = ('No version info in file "{}" for the '
                     'following packages'.format(req_file))
            Requirements._print_req_env_comp_list(
                header, no_version_info, pretty=pretty)

    @staticmethod
    def compare_req_file_to_env(req_file, venv):
        """
        Compares a requirement file to the environment.

        A simple way to do this would just be to use pip freeze and diff
        the files... but we can do better.

        We create 4 lists:
        1. same: Same version in requirements file (RF) and env
        2. verdiff: Package in RF and env with different versions; this will
        include packages that aren't pegged to specific version (so either
        not specs or spec range, i.e. >= etc)
        3. req_only: In RF not env
        4. env_only: In env not RF

        :param req_file: requirements file.
        :param venv: virtual environment
        :param pretty: prints in color.
        :return: 4 x lists.
        """

        parsed_req = Requirements.parse_req_file(req_file)
        if not parsed_req:
            return None

        all_reqs = {x.req.key: {'project_name': x.req.project_name,
                                'specs': x.req.specs}
                    for x in parsed_req}

        req_only = [x for x in all_reqs if x not in venv.all_packages]
        env_only = [x for x in venv.all_packages if x not in all_reqs]

        # Version comparison:
        REQ_NO_VERSION = '-1'  # value for when no requirements
        verdiff = []
        same = []
        ver_check = [x for x in all_reqs if x not in req_only]
        for package in ver_check:
            env_ver = venv.all_packages[package].version

            specs = all_reqs[package].get('specs')
            if not specs:
                req_ver = REQ_NO_VERSION
            else:
                req_ver = [x[1] for x in specs if x[0] == '=='][0]
                if not req_ver:
                    req_ver = REQ_NO_VERSION

            if req_ver == env_ver:
                same.append((package, env_ver))
            else:
                verdiff.append((package, req_ver, env_ver))

        return same, verdiff, req_only, env_only

    @staticmethod
    def print_req_env_comp_lists(
            same, verdiff, req_only, env_only, pretty=False):

        header = 'Only in requirements file:'
        Requirements._print_req_env_comp_list(header, req_only, pretty=pretty)

        header = 'Only in environment:'
        Requirements._print_req_env_comp_list(header, env_only, pretty=pretty)

        header = 'Same in requirements file and environment:'
        Requirements._print_req_env_comp_list(header, same, pretty=pretty)

        header = ("Versions differ (package, req_version, env_version):"
                  "\n(NB: '-1' indicates no version information or version "
                  "not '==' specific)")
        Requirements._print_req_env_comp_list(header, verdiff, pretty=pretty)

    @staticmethod
    def _print_req_env_comp_list(header, in_list, pretty=False):
        print_col(header, header=True, pretty=pretty)
        for line in in_list:
            print_col(str(line), pretty=pretty)
        if not in_list:
            print_col("None", pretty=pretty)
