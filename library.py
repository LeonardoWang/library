import lx
from dex import Dex

import hashlib
import sys


##  `set` of all API functions
api_list = None

##  `list` of all tagged libraries' names
tagged_pkg_list = None


##  load `api_list` and `tagged_pkg_list` from config file and database
def init():
    global api_list
    global tagged_pkg_list

    lx.connect_db('main')
    lx.connect_db('android')

    api_list = set( l.split(',')[0] for l in lx.open_file(__file__, 'strict_api.csv') )

    sql = 'select pkg from thr_known'
    tagged_pkg_list = [ r[0] for r in lx.query(sql) ]


def main(dex_file_name):
    init()
    dex = Dex(dex_file_name)

    # create an empty tree
    root = TreeNode('')
    root.tag = ''  # otherwise root.tag will be 'L'

    # create tree nodes
    for class_ in dex.classes:
        name = class_.name()
        assert name.startswith('L')
        apis = get_invoked_apis(class_)
        if len(apis) == 0: continue
        leaf = TreeNode(name, calc_hash(apis), len(apis))
        root.add_leaf(leaf)

    # calculate hash and weight
    root.finish()

    # calculate match rate of potential libraries
    root.search_children()

    # get matched libraries
    return root.get_result()


def get_invoked_apis(class_):
    ret = [ ]
    for method in class_.methods():
        for invoked_method in method.get_invoked_methods_libradar():
            if invoked_method in api_list:
                ret.append(invoked_method)
    return ret


def calc_hash(str_list):
    ret = hashlib.sha256()
    for s in sorted(str_list):
        if type(s) is str:
            s = s.encode('utf8')
        ret.update(s)
    return ret.digest()


def query_package(sha256):
    sql = 'select un_ob_pn from library where sha256 = %s'
    r = lx.query(sql, sha256, 'android')
    if len(r) == 0: return None
    return r[0][0] if r else None



##  each tree node represents a package or a class
class TreeNode:
    def __init__(self, tag, hash_ = None, weight = None):
        self.tag = 'L' + tag[1:]    ## the package name (or full class name)
        self.hash = hash_           ## sha256 of children's hash (for package) or of invoked APIs' name (for class)
        self.weight = weight        ## number of API calls in this package

        self.parent = None

        if hash_ is None:  # not leaf (package)
            assert weight is None
            self.children = { }
        else:  # leaf (class)
            assert weight is not None
            self.children = None

        self.match_libs = { }       ## mapping from potential libraries' names to sum of matched descendants' weight


    ##  insert a leaf to the tree; create missing nodes on the path to that leaf and set their tag
    def add_leaf(self, node):
        assert node.tag.startswith(self.tag)
        assert node.tag != self.tag  # class name must be unique

        suffix = node.tag[ len(self.tag) + 1 : ]
        next_tag = suffix.split('/', 1)[0]

        if '/' in suffix:  # inner package exist
            if next_tag not in self.children:
                self.children[next_tag] = TreeNode(self.tag + '/' + next_tag)
            self.children[next_tag].add_leaf(node)
            self.children[next_tag].parent = self

        else:  # self is last layer
            self.children[next_tag] = node


    ##  calculate the hash of every node
    def finish(self):
        for c in self.children.values():
            if c.children is not None:
                c.finish()
        self.hash = calc_hash([ c.hash.hex() for c in self.children.values() ])
        self.weight = sum( c.weight for c in self.children.values() )


    ##  search potential libraries in children
    def search_children(self):
        if self.children is None: return
        for c in self.children.values():
            c.search()


    ##  search potential libraries in this node and its children
    ##  this function is copied from MaZA's code and seems odd
    def search(self):
        pkg = query_package(self.hash)

        if pkg is None:
            self.search_children()
            return

        dont_search_children = False

        for tagged_pkg in tagged_pkg_list:

            if tagged_pkg == pkg:
                self.match_libs[pkg] = self.weight

            elif pkg.startswith(tagged_pkg):
                cursor = self
                for i in range(pkg.count('/') - tagged_pkg.count('/')):
                    if cursor.parent.parent is not None:
                        cursor = cursor.parent
                    else:
                        self.search_children()
                        return
                if tagged_pkg in cursor.match_libs is not None:
                    if cursor.match_libs[tagged_pkg] != cursor.weight:
                        cursor.match_libs[tagged_pkg] += self.weight
                else:
                    cursor.match_libs[tagged_pkg] = self.weight

                dont_search_children = True

        if dont_search_children:
            return

        self.search_children()


    # find all matched libraries which have identify package name or high API match rate
    def get_result(self):
        ret = { }
        for pkg, match_weight in self.match_libs.items():
            if match_weight / self.weight >= 0.1 or pkg == self.tag:
                ret[self.tag] = pkg
        if self.children is not None:
            for c in self.children.values():
                ret.update(c.get_result())
        return ret


if __name__ == '__main__':
    if len(sys.argv) > 1:
        dex_file = sys.argv[1]
    else:
        dex_file = 'classes.dex'
    print(lx.json(main(dex_file), pretty = True))
