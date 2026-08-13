.PHONY: all data database outputs test clean

all: data database outputs test

data:
	python scripts/generate_data.py

database:
	python scripts/build_database.py

outputs:
	python scripts/run_queries.py

test:
	python -m unittest discover -s tests -v

clean:
	rm -f build/student_success.db
