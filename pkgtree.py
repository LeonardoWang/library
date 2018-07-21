from __future__ import annotations

from common import *

from .stub import *

import hashlib


def _get_invoked_apis(class_: DexClass, api_set: Set[str]) -> List[str]:
    ret: List[str] = [ ]
    for method in class_.methods():
        for invoked_method in method.get_invoked_methods():
            if invoked_method in api_set:
                ret.append(invoked_method)
    return ret


def _calc_hash(lst: list) -> bytes:
    ret = hashlib.sha1()
    for s in sorted(lst):
        if isinstance(s, str):
            s = s.encode('utf8')
        ret.update(s)
    return ret.digest()


class PackageTree:
    def __init__(self, dex: Dex, api_set: Set[str]) -> None:
        # create empty tree
        self.root: _TreeNode = _TreeNode('')
        self.root.name = ''  # otherwise root.name will be 'L'

        # create tree nodes
        for class_ in dex.classes:
            name = class_.name()
            assert name.startswith('L')
            apis = _get_invoked_apis(class_, api_set)
            if len(apis) == 0: continue
            leaf = _TreeNode(name, _calc_hash(apis), len(apis))
            self.root.add_leaf(leaf)

        # calculate hash and weight
        self.nodes: Dict[bytes, _TreeNode] = { cast(bytes, node.hash) : node for node in self.root.finish() }


    def detect_libs(self, exact_libs: List[LibInfo], match_rate_threshold: float,
            include_subpkgs: bool) -> Dict[str, str]:
        """Calculate match rate of potential libraries, return matches above threshold
        exact_libs: list of perfectly matched libraries
        """
        for lib in exact_libs:
            node = self.nodes[lib.hash]
            node.match_libs[lib.name] = cast(int, node.weight)
        self.root.calc_match_rate()
        return self.root.get_libs(match_rate_threshold, include_subpkgs)


    def detect_exact_libs(self, exact_libs: List[LibInfo]) -> Dict[str, str]:
        """Get perfectly matched libraries, excluding subpackages"""
        for lib in exact_libs:
            node = self.nodes[lib.hash]
            node.match_libs[lib.name] = cast(int, node.weight)
        return self.root.get_exact_libs()



class _TreeNode:
    def __init__(self, name: str, hash_: Optional[bytes] = None, weight: Optional[int] = None) -> None:
        self.name = 'L' + name[1:]  ## the package name (or full class name)
        self.hash = hash_
        self.weight = weight

        if hash_ is None:  # not leaf (package)
            self.children: Optional[Dict[str, _TreeNode]] = { }
        else:  # leaf (class)
            self.children = None

        # mapping from potential library name to matched API weight
        self.match_libs: Dict[str, int] = defaultdict(int)


    def add_leaf(self, node: _TreeNode) -> None:
        """Insert a leaf into the tree
        Create missing nodes on the path to that leaf and set their name
        """
        assert node.name.startswith(self.name)
        assert node.name != self.name  # class name must be unique

        suffix = node.name[ len(self.name) + 1 : ]
        next_name = suffix.split('/', 1)[0]
        children = cast(Dict[str, _TreeNode], self.children)

        if '/' in suffix:  # inner package exist
            if next_name not in children:
                children[next_name] = _TreeNode(self.name + '/' + next_name)
            children[next_name].add_leaf(node)

        else:  # self is last layer
            children[next_name] = node


    def finish(self) -> List[_TreeNode]:
        """Calculate hash of self and each node in subtree; return a list of all nodes"""
        if self.children is None: return [ self ]  # hash of leaf nodes are calculated when create

        children_nodes: List[_TreeNode] = [ ]
        for c in self.children.values():
            children_nodes += c.finish()

        self.hash = _calc_hash([ cast(bytes, c.hash) for c in self.children.values() ])
        self.weight = sum( c.weight for c in self.children.values() )
        return [ self ] + children_nodes


    def calc_match_rate(self) -> None:
        """Search partially matched libraries in this node and its children

        Simplest example:
        Child X matches 'com.lib.foo' with weight 10 and matches 'another.foo' with weight 12.
        Child Y matches 'com.lib.bar' with weight 20 and matches 'whatever' with weight 15.
        Then this node matches 'com.lib' with weight 30, and 'another' with weight 12.

        Special case #1:
        If Child X matches 'com.lib.foo1' with weight 10 and matches 'com.lib.foo2' with weight 8,
        it only contributes max(10,8) weights to this node with name 'com.lib', instead of 10+8.

        Special case #2:
        If the weight of this node is only 25, then matched weight of 'com.lib' is 25 instead of 30.
        """
        if len(self.match_libs) > 0 or self.children is None:
            return  # nothing to calculate for perfect matches and leaf nodes

        for c in self.children.values():
            c.calc_match_rate()
            child_match: Dict[str, int] = defaultdict(int)
            for child_pkg, weight in c.match_libs.items():
                pkg = child_pkg.rsplit('/', 1)[0]
                child_match[pkg] = max(child_match[pkg], weight)
            for pkg, weight in child_match.items():
                self.match_libs[pkg] += weight

        for pkg, weight in self.match_libs.items():
            if weight > cast(int, self.weight):
                self.match_libs[pkg] = cast(int, self.weight)


    def get_libs(self, match_rate_threshold: float, include_subpkgs: bool = True) -> Dict[str, str]:
        """Get all perfectly or partially matched libraries
        Return the mapping from package name in dex to standard library name.
        """
        if self.children is None: return { }  # assuming lib is always package instead of class

        ret: Dict[str, str] = { }

        if len(self.match_libs) > 0:
            # find all potential library names with max matched weight
            max_weight = max(self.match_libs.values())
            pkgs = [ p for p, w in self.match_libs.items() if w == max_weight ]

            if len(pkgs) > max_weight:  # small feature size with too many potential names
                return { }  # likely to be false-positive

            if self.name in pkgs:  # this package has the same name of one of best-matched libraries
                pkg = self.name  # looks good
            else:
                pkg = sorted(pkgs)[0]  # just randomly pick one

            if max_weight >= cast(int, self.weight) * match_rate_threshold:  # good match rate
                ret[self.name] = pkg  # add this match to result
            if max_weight == self.weight:  # excellent match rate
                return ret  # we can ignore children's match

        lib = ret.get(self.name)
        for child in self.children.values():
            if child.children is None: continue  # ignore classes (leaves), only consider packages
            for child_pkg, child_lib in child.get_libs(match_rate_threshold).items():
                if include_subpkgs:
                    # always add children's matches
                    ret[child_pkg] = child_lib
                elif lib is None or not child_lib.startswith(lib):
                    # only when its not a subpackage of this node's matched lib
                    ret[child_pkg] = child_lib

        return ret


    def get_exact_libs(self) -> Dict[str, str]:
        """Get perfectly matched libraries, excluding subpackages"""
        if self.children is None: return { }  # ignore classes

        if len(self.match_libs) > 0:
            pkgs = self.match_libs.keys()
            if self.name in pkgs:
                return { self.name: self.name }
            else:
                return { self.name: sorted(pkgs)[0] }

        ret: Dict[str, str] = { }
        for child in self.children.values():
            ret.update(child.get_exact_libs())
        return ret
