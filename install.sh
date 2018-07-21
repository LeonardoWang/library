LIB_PATH=${HOME}/.local/lib
PYTHON_VERSION=`python3 --version | grep -o '3\..'`
PYTHON_PATH=${LIB_PATH}/python${PYTHON_VERSION}/site-packages

mkdir -p ${PYTHON_PATH}/library
cp *.py ${PYTHON_PATH}/library/
cp apis.txt ${PYTHON_PATH}/library/
