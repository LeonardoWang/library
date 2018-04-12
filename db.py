import lx

MinWeight = 3
MinLibCount = 5

pkg_name_black_list = [ 'Lcn', 'Lcom', 'Lorg' ]

def load_api_list():
    return set( l.split(',', 1)[0] for l in lx.open_res_file(__file__, 'strict_api.csv') )

def get_lib_names(sha256):
    sql = 'select pkg_name from lib where sha256 = %s'
    return lx.query('library', sql, sha256, multi = True)

def add_pkg(sha256, weight, name):
    if len(name) <= 2 or name in pkg_name_black_list: return
    sql = 'insert into cluster (sha256, pkg_name, weight, count) values (%s,%s,%s,%s)' + \
            'on duplicate key update count = count + 1'
    lx.commit('library', sql, (sha256, name, weight, 1))

def get_clustered_libs():
    sql = 'select sha256, pkg_name, weight from cluster where count >= %s'
    return lx.query('library', sql, MinLibCount)

def insert_lib(sha256, pkg_name):
    sql = 'insert ignore into lib (sha256, pkg_name) values (%s,%s)'
    lx.commit('library', sql, (sha256, pkg_name))
