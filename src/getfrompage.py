import requests
from flask import request, redirect, render_template
from .config import config
from .projectinfo import get_project_info

def get_from_page():
	page_title = request.args['page']
	project = request.args['project'] if request.args['project'] else 'en.wikipedia.org'

	project_info = get_project_info(config, project)

	if not project_info:
		return render_template(
			'error.html',
			error = f'Project {project} does not exist.'
		)

	(_, project_url) = project_info
	project_domain = project_url.partition('//')[2]
	
	page_info = requests.get(f'{project_url}/w/api.php?action=query&titles={page_title}&format=json&formatversion=2')\
		.json()['query']['pages'][0]
	
	if not page_info:
		return render_template(
			'error.html',
			error = f'Page with title {page_title} not found.'
		)

	page_id = page_info['pageid']

	return redirect(f'/{project_domain}/{page_id}', 302)