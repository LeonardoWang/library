import db

from collections import defaultdict
import hashlib
import operator


LibMatchThreshold = 0.9


##  `set` of all API functions
_api_list = db.load_api_list()


def _get_invoked_apis(class_):
    ret = [ ]
    for method in class_.methods():
        for invoked_method in method.get_invoked_methods_libradar():
            if invoked_method in _api_list:
                ret.append(invoked_method)
    return ret


def _calc_hash(lst):
    ret = hashlib.sha256()
    for s in sorted(lst):
        if type(s) is str:
            s = s.encode('utf8')
        ret.update(s)
    return ret.digest()


class PackageTree:
    def __init__(self, dex):
        # create an empty tree
        self.root = _TreeNode('')
        self.root.tag = ''  # otherwise root.tag will be 'L'

        # create tree nodes
        for class_ in dex.classes:
            name = class_.name()
            assert name.startswith('L')
            apis = _get_invoked_apis(class_)
            if len(apis) == 0: continue
            leaf = _TreeNode(name, _calc_hash(apis), len(apis))
            self.root.add_leaf(leaf)

        # calculate hash and weight
        self.root.finish()

    ##  insert the tree into clustering database
    def cluster(self):
        self.root.cluster()

    ##  calculate match rate of potential libraries
    def match_libs(self):
        self.root.match_perfect_libs()
        self.root.match_potential_libs()
        return self.root.get_all_libs()


##  each tree node represents a package or a class
class _TreeNode:
    def __init__(self, tag, hash_ = None, weight = None):
        self.tag = 'L' + tag[1:]    ## the package name (or full class name)
        self.hash = hash_           ## sha256 of children's hash (for package) or of invoked APIs' name (for class)
        self.weight = weight        ## number of API calls in this package

        self.parent = None

        if hash_ is None:  # not leaf (package)
            self.children = { }
        else:  # leaf (class)
            self.children = None

        self.match_libs = { }


    ##  insert a leaf to the tree; create missing nodes on the path to that leaf and set their tag
    def add_leaf(self, node):
        assert node.tag.startswith(self.tag)
        assert node.tag != self.tag  # class name must be unique

        suffix = node.tag[ len(self.tag) + 1 : ]
        next_tag = suffix.split('/', 1)[0]

        if '/' in suffix:  # inner package exist
            if next_tag not in self.children:
                self.children[next_tag] = _TreeNode(self.tag + '/' + next_tag)
            self.children[next_tag].add_leaf(node)
            self.children[next_tag].parent = self

        else:  # self is last layer
            self.children[next_tag] = node


    ##  calculate the hash of every node
    def finish(self):
        for c in self.children.values():
            if c.children is not None:
                c.finish()
        self.hash = _calc_hash([ c.hash for c in self.children.values() ])
        self.weight = sum( c.weight for c in self.children.values() )


    def cluster(self):
        if self.weight < db.MinWeight: return
        db.add_pkg(self.hash, self.weight, self.tag)
        for c in self.children.values():
            if c.children is not None:
                c.cluster()


    ##  search perfectly matched libraries in this node and its children
    def match_perfect_libs(self):
        libs = db.get_lib_names(self.hash)
        if len(libs) > 0:
            self.match_libs = { lib : self.weight for lib in libs }
        elif self.children is not None:
            for c in self.children.values():
                c.match_perfect_libs()


    ##  search partially matched libraries in this node and its children
    def match_potential_libs(self):
        if len(self.match_libs) > 0 or self.children is None: return

        self.match_libs = defaultdict(int)
        for c in self.children.values():
            c.match_potential_libs()
            child_match = defaultdict(int)
            for child_pkg, weight in c.match_libs.items():
                pkg = child_pkg.rsplit('/', 1)[0]
                child_match[pkg] = max(child_match[pkg], weight)
            for pkg, weight in child_match.items():
                self.match_libs[pkg] += weight


    ##  get all matched libraries
    def get_all_libs(self):
        ret = { }

        if len(self.match_libs) > 0:
            pkg, weight = max(self.match_libs.items(), key = operator.itemgetter(1))
            pkgs = [ p for p, w in self.match_libs.items() if w == weight ]
            if self.tag in pkgs:
                pkg = self.tag
            elif len(pkgs) > weight:
                return ret  # small feature size and too many potential package names, not a lib
            if weight >= self.weight * LibMatchThreshold:
                ret[self.tag] = pkg
                #print(self.tag, pkg, self.hash.hex())
            if weight == self.weight:
                return ret

        if self.children is not None:
            for c in self.children.values():
                ret.update(c.get_all_libs())
        return ret
