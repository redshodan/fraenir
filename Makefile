ifeq "$(origin VIRTUAL_ENV)" "undefined"
	VENV=$(abspath $(dir $(abspath $(lastword $(MAKEFILE_LIST))))/venv)
else
	VENV=$(abspath $(VIRTUAL_ENV))
endif

VBIN=$(VENV)/bin
VINC=$(VENV)/inc
VLIB=$(VENV)/lib
VSRC=$(VENV)/src
PYTHON=$(VBIN)/python
PYTEST=$(VBIN)/pytest
PIP=$(VBIN)/pip
FLAKE8=$(VBIN)/flake8
PY_LIB=$(VLIB)/python*/site-packages
ifdef LD_LIBRARY_PATH
	LD_LIBRARY_PATH:=$(VLIB):$(LD_LIBRARY_PATH)
else
	LD_LIBRARY_PATH=$(VLIB)
endif

SQLCIPHER=$(VSRC)/sqlcipher
SQLCIPHER_CFLAGS="-DSQLITE_DEFAULT_CACHE_SIZE=-8000 -DSQLITE_ENABLE_FTS3 -DSQLITE_ENABLE_FTS3_PARENTHESIS -DSQLITE_ENABLE_FTS4 -DSQLITE_ENABLE_FTS5 -DSQLITE_ENABLE_JSON1 -DSQLITE_ENABLE_STAT4 -DSQLITE_ENABLE_UPDATE_DELETE_LIMIT -DSQLITE_SOUNDEX -DSQLITE_USE_URI -DSQLITE_HAS_CODEC -O2"

PYSQLCIPHER=$(VSRC)/pysqlcipher3
PYSQLCIPHER_EGG=$(PY_LIB)/pysqlcipher3-1.0.3-py3.7-linux-x86_64.egg

all: venv build

venv: $(VENV)/bin/python
$(VENV)/bin/python:
	virtualenv -p python3 $(VENV)
	echo "export LD_LIBRARY_PATH=$(LD_LIBRARY_PATH)" >> $(VBIN)/activate
$(VSRC): $(VENV)/bin/python
	mkdir $(VSRC)

build: requirements pysqlcipher
requirements: venv
	$(PIP) install -r requirements.txt
	$(PIP) install --no-deps .
	rm -rf $(PY_LIB)/fraenir
	ln -s ../../../../fraenir `ls -1d venv/lib/python*/site-packages`/fraenir
	rm -rf fraenir.egg-info

# Ignore future warning for flake8 itself
check: $(FLAKE8)
	PYTHONWARNINGS=ignore $(FLAKE8)

tests: pytest tests-clean
ifdef FTF
	$(PYTHON) setup.py test --addopts "-k $(FTF)"
else
	$(PYTHON) setup.py test
endif
	rm -rf fraenir.egg-info

sqlcipher: sqlcipher-install
sqlcipher-build: $(SQLCIPHER)/libsqlcipher.la
sqlcipher-install: $(VLIB)/libsqlcipher.la
$(SQLCIPHER): $(VSRC)
	(cd $(VSRC); if [ ! -d sqlcipher ]; then git clone https://github.com/sqlcipher/sqlcipher.git; else touch sqlcipher; fi)
$(SQLCIPHER)/configure: $(SQLCIPHER)
	(cd $(SQLCIPHER); autoconf)
$(SQLCIPHER)/Makefile: $(SQLCIPHER)/configure
	(cd $(SQLCIPHER); CFLAGS=$(SQLCIPHER_CFLAGS) ./configure --prefix=$(VENV) --disable-tcl --enable-tempstore=yes LDFLAGS="-lcrypto -lm")
$(SQLCIPHER)/libsqlcipher.la: $(SQLCIPHER)/Makefile
	(cd $(SQLCIPHER); make)
$(VLIB)/libsqlcipher.la: $(SQLCIPHER)/libsqlcipher.la
	(cd $(SQLCIPHER); make install)

pysqlcipher: pysqlcipher-install
pysqlcipher-build: $(PYSQLCIPHER)/build
pysqlcipher-install: $(PYSQLCIPHER_EGG)
$(PYSQLCIPHER): $(VSRC) sqlcipher
	(cd $(VSRC); if [ ! -d pysqlcipher3 ]; then git clone https://github.com/rigglemania/pysqlcipher3; else touch pysqlcipher3; fi)
#	(cd $(VSRC); git clone https://github.com/leapcode/pysqlcipher)
#	(cd $(PYSQLCIPHER); git checkout 2.6.9.1)
$(PYSQLCIPHER)/build: $(PYSQLCIPHER)
	(cd $(PYSQLCIPHER); CFLAGS="-I../../include" LDFLAGS="-L../../lib" $(PYTHON) setup.py build)
$(PYSQLCIPHER_EGG): $(PYSQLCIPHER)/build
	(cd $(PYSQLCIPHER); $(PYTHON) setup.py install)


pytest: $(PYTEST)
$(PYTEST): requirements-test.txt
	$(PIP) install -r requirements-test.txt

$(FLAKE8): requirements-test.txt
	$(PIP) install -r requirements-test.txt

clean:
	find fraenir test -name '__pycache__' -type d | xargs rm -rf
	find fraenir test -name '*.pyc' | xargs rm -f

dist-clean:
	-rm -rf $(VENV)

DOCKER_COMPOSE := docker-compose -f docker/docker-compose.yml
image:
	@$(DOCKER_COMPOSE) build

docker: image
	@$(DOCKER_COMPOSE) create --no-recreate

docker-clean:
	docker stop fraenir
	docker rm fraenir
	-docker rmi -f fraenir

.PHONY: test tests clean venv build docker image docker-clean requirements pysqlcipher sqlcipher
