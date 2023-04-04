from src import app
from src.config import config

if __name__ == '__main__':
	app.run(debug = config.getboolean('General', 'dev'))