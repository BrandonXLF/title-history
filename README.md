# Title History

Tool that allows you to view the previous titles of an article hosted on Wikimedia project wikis (like Wikipedia) with details about when it was moved. The tool makes use to the article's history to find when the article was moved and then it finds the accompanying log entry to get the move comment.

The tool is hosted at https://titlehistory.toolforge.org/.

## Setup

To run, the tool requires Python 3 and several dependencies that are  installed with `pip install -r requirements.txt`.

The app also requires a connection to the Wikimedia replica database to work, which you can access by becoming a Toolforge user. In development mode, it expects the meta database to be located at `localhost:4711` and the project database to be at `localhost:4712`. A command like `ssh -N USERNAME@login.toolforge.org -L 4711:meta.web.db.svc.wikimedia.cloud:3306 -L 4712:PROJECT.web.db.svc.wikimedia.cloud:3306` can be used to create an ssh tunnel to these databases with `USERNAME` being your Toolforge username and `PROJECT` being the project database's name, e.g. `enwiki`. Your database login info, obtained from your `replica.my.cnf` file, and other config options must be set in `config.ini` based on the template at `example-config.ini`.

## Running

The app is started with the `app.py` file and can be run with a command like `py app.py`.