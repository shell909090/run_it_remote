### Makefile --- 

## Author: shell@xps13
## Version: $Id: Makefile,v 0.0 2015/09/07 09:13:17 shell Exp $
## Keywords: 
## X-URL: 

install:
	python setup.py install

clean:
	rm -rf build

pylint:
	find . -name '*.py' | xargs pylint --disable=C

pymetrics:
	find . -name '*.py' | xargs pymetrics -B -C -S -i "mccabe:McCabeMetric"

unittest:
	python `which python-coverage` run --source=qweblib -m unittest discover test 
	python-coverage report -m
	python-coverage erase

### Makefile ends here
