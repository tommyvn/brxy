edge_bin := dist/brxy.edge
node_bin := dist/brxy.node

.PHONY: all tests clean

.PHONY: node-bin
node-bin: $(node_bin)

.PHONY: edge-bin
edge-bin: $(edge_bin)

$(node_bin): 
	pyinstaller -F brxy/node/__main__.py -n brxy.node

$(edge_bin): 
	pyinstaller -F brxy/edge/__main__.py -n brxy.edge

bin: edge-bin node-bin

tests:
	flake8 tests brxy setup.py
	nosetests -v tests.edge
	# flake8 tests brxy setup.py
	# nosetests --with-coverage --cover-package=brxy -v tests.edge

clean:
	-rm -fr dist build brxy.node.spec brxy.edge.edge
