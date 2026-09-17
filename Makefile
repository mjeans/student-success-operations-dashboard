.PHONY: all data database outputs previews check-previews test clean

all:
	$(MAKE) data
	$(MAKE) database
	$(MAKE) outputs
	$(MAKE) previews
	$(MAKE) test

data:
	python scripts/generate_data.py

database:
	python scripts/build_database.py

outputs:
	python scripts/run_queries.py

previews:
	python scripts/render_previews.py

check-previews:
	python scripts/render_previews.py --check

test:
	python -m unittest discover -s tests -v

clean:
	rm -f build/student_success.db
