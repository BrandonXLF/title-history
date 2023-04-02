from flask import Flask, render_template
from .getfrompage import get_from_page
from .permalink import permalink

app = Flask(__name__)

@app.route('/')
def home():
	return render_template('form.html')

app.add_url_rule('/get', view_func = get_from_page)
app.add_url_rule('/<project>/<page_id>', view_func = permalink)