import requests
from flask import request, redirect, abort
from .config import config
from .projectinfo import get_project_info

def get_from_page():
	page_title = request.args.get('page', '')
	project = request.args.get('project', '') or 'en.wikipedia.org'

	if not page_title:
		abort(400, 'Page title is required.')

	project_info = get_project_info(config, project)

	if not project_info:
		abort(404, f'Project {project} does not exist.')

	(_, project_url) = project_info
	project_domain = project_url.partition('//')[2]
	
	page_info = requests.get(f'{project_url}/w/api.php?action=query&titles={page_title}&format=json&formatversion=2')\
		.json()['query']['pages'][0]

	if 'pageid' not in page_info:
		abort(404, f'Page with title {page_title} not found.')

	page_id = page_info['pageid']

	return redirect(f'/{project_domain}/{page_id}', 302)