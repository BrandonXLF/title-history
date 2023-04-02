from src import app
from src.config import config

app.run(debug = config.getboolean('General', 'dev'))