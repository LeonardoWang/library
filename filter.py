import db

from collections import defaultdict

def name_better(n1, n2):
    if n1 is None or n2 is None: return False
    parts1 = list(reversed(n1[1:].split('/')))
    parts2 = list(reversed(n2[1:].split('/')))
    l1 = max(len(p) for p in parts1)
    l2 = max(len(p) for p in parts2)
    if l1 <= 1 and l2 > 1: return False
    if len(parts1) > len(parts2): return False
    for i in range(len(parts1)):
        if parts1[i] == parts2[i]: continue
        if len(parts2[i]) == 1: continue
        if parts1[i] != parts2[i]: return False
    return True


def main():
    names_by_sha256 = defaultdict(set)
    for sha256, pkg_name, weight in db.get_clustered_libs():
        names_by_sha256[sha256].add(pkg_name)
    
    for sha256, names in names_by_sha256.items():
        if len(names) == 1: continue
    
        names = list(sorted(names))
        for i in range(len(names)):
            for j in range(i):
                if name_better(names[i], names[j]):
                    names[j] = None
                elif name_better(names[j], names[i]):
                    names[i] = None
        names = [ n for n in names if n is not None ]
    
        for name in names:
            db.insert_lib(sha256, name)


if __name__ == '__main__':
    main()