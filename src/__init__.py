from flask import Flask, render_template, send_from_directory, request
from werkzeug.exceptions import HTTPException
from .getfrompage import get_from_page
from .permalink import permalink

app = Flask(__name__)

@app.route('/')
def home():
	return render_template('form.html')

@app.route('/robots.txt')
def robots_txt():
	return send_from_directory(app.static_folder, request.path[1:])

app.add_url_rule('/get', view_func = get_from_page)
app.add_url_rule('/<project>/<page_id>', view_func = permalink)

@app.errorhandler(HTTPException)
def handle_exception(error: HTTPException):
	return render_template('error.html', error = error), error.code