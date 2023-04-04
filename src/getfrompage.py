import requests
import urllib.parse
from flask import request, redirect
from .projectinfo import get_project_info
from .error import ProcessError

def get_from_page():
	page_title = request.args.get('page', '')
	project = request.args.get('project', '') or 'en.wikipedia.org'

	if not page_title:
		raise ProcessError('Page title is required.', 400, project)

	project_info = get_project_info(project)

	if not project_info:
		raise ProcessError(f'Project {project} does not exist.', 404, project, page_title)

	(_, project_url) = project_info
	project_domain = project_url.partition('//')[2]
	encoded_title = urllib.parse.quote(page_title)
	
	pages = requests.get(f'{project_url}/w/api.php?action=query&titles={encoded_title}&format=json&formatversion=2')\
		.json()['query'].get('pages')

	if not pages or 'pageid' not in pages[0]:
		raise ProcessError(f'Page with title {page_title} not found.', 404, project, page_title)

	page_id = pages[0]['pageid']

	return redirect(f'/{project_domain}/{page_id}', 302)