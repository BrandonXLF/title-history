import mysql.connector
import requests
from flask import Flask, request, render_template, escape
import dateutil.parser
import re
import urllib.parse
import phpserialize
from configparser import ConfigParser

app = Flask(__name__)
config = ConfigParser('')
config.read('config.ini')

@app.route('/')
def movehist():
	def display_page_name(namespace, title):
		if namespace == None or title == None:
			return None

		title = title.replace('_', ' ')
		ns_text = namespaces[str(namespace)]['name']
		
		if ns_text:
			return ns_text + ':' + title
			
		return title
		
	def get_project_info():
		db = mysql.connector.connect(
			host = 'localhost' if config.getboolean('General', 'dev') else 'meta.web.db.svc.wikimedia.cloud',
			port = 4711 if config.getboolean('General', 'dev') else 3306,
			user = config['Database']['user'],
			password = config['Database']['pass'],
			db = 'meta_p'
		)
		cursor = db.cursor()

		query = 'SELECT dbname, url FROM wiki WHERE dbname = %s OR url = %s LIMIT 1'

		project = request.args['project'] if 'project' in request.args else 'en.wikipedia.org'

		cursor.execute(query, (project, 'https://' + project))
		res = cursor.fetchone()

		return res

	def get_namespace_info():
		res = requests.get(project_url + '/w/api.php?action=query&meta=siteinfo&siprop=namespaces|namespacealiases&format=json&formatversion=2')
		query = res.json()['query']
		namespace_numbers = {}

		for namespace_index in query['namespaces']:
			namespace_info = query['namespaces'][namespace_index]
			namespace_numbers[namespace_info['name']] = namespace_info['id']

			if 'canonical' in namespace_info:
				namespace_numbers[namespace_info['canonical']] = namespace_info['id']

		for namespace_alias in query['namespacealiases']:
			namespace_numbers[namespace_alias['alias']] = namespace_alias['id']

		return (query['namespaces'], namespace_numbers)

	def replace_brackets(match):
		break_match = re.search(r'(.+?)\|(.+)', match.group(1))
		target = match.group(1)
		text = match.group(1)
		
		if break_match:
			target = break_match.group(1)
			text = break_match.group(2)
			
		return f'<a href="{project_url}/wiki/{urllib.parse.quote(target)}" target="_blank">{text}</a>'

	def process_comment(text):
		text = escape(text)
		return re.sub(r'\[\[(.+?)\]\]', replace_brackets, text)

	if 'page' not in request.args:
		return render_template('form.html')

	page_title = request.args['page']
	page_ns_name = ''
	project_info = get_project_info()

	if not project_info:
		return 'Project does not exist.'

	(project_db, project_url) = project_info

	db = mysql.connector.connect(
		host = 'localhost' if config.getboolean('General', 'dev') else project_db + '.web.db.svc.wikimedia.cloud',
		port = 4712 if config.getboolean('General', 'dev') else 3306,
		user = config['Database']['user'],
		password = config['Database']['pass'],
		db = project_db + '_p'
	)
	cursor = db.cursor()

	(namespaces, namespace_numbers) = get_namespace_info()

	if ':' in page_title:
		(page_ns_name, page_title) = page_title.split(':', 2)

	page_ns = namespace_numbers[page_ns_name.replace('_', ' ')]
	page_title = page_title.replace(' ', '_')

	query = 'SELECT page_id FROM page WHERE page_namespace = %s AND page_title = %s LIMIT 1'

	cursor.execute(query, (page_ns, page_title))
	page_info = cursor.fetchone()
	page_id = page_info[0]
	
	query = '''
SELECT
	revision.rev_timestamp,
	actor_name,
	log_namespace,
	log_title,
	comment_revision.comment_text,
	comment_logging.comment_text,
	log_params,
	log_id
FROM
	revision
JOIN page ON
	page_id = rev_page
	AND page_namespace = %s
	AND page_title = %s
# make sure revision didn't change the page's content
JOIN revision AS revision_parent
	ON revision_parent.rev_id = revision.rev_parent_id
	AND revision_parent.rev_sha1 = revision.rev_sha1
JOIN comment_revision ON
	revision.rev_comment_id = comment_revision.comment_id
JOIN logging_userindex ON
	log_actor = revision.rev_actor
	# log entry might have a larger timestamp than the revision entry since it's added after
	AND (
		log_timestamp = revision.rev_timestamp
		OR log_timestamp = revision.rev_timestamp + 1
	)
	AND log_type = 'move'
LEFT JOIN comment_logging ON
	log_comment_id = comment_logging.comment_id
LEFT JOIN actor_logging ON
	log_actor = actor_id
ORDER BY
	log_timestamp DESC
'''

	cursor.execute(query, (page_ns, page_title))
	move_entries = cursor.fetchall()
	items = []

	for move_entry in move_entries:
		from_page = display_page_name(move_entry[2], move_entry[3].decode())
		
		try:
			to_page = phpserialize.loads(move_entry[6])[b'4::target']
		except:
			to_page = move_entry[6].decode()

		revision_comment = move_entry[4].decode()
		
		if ('[[' + from_page + ']]' not in revision_comment or
			'[[' + to_page + ']]' not in revision_comment):
			continue

		items.append({
			'type': 'move',
			'from': from_page,
			'to': to_page,
			'time': dateutil.parser.parse(move_entry[0].decode()),
			'user': move_entry[1].decode(),
			'comment': move_entry[5].decode() and process_comment(move_entry[5].decode()),
			'id': str(move_entry[7])
		})

	return render_template(
		'result.html',
		items = items,
		project_url = project_url,
		page = display_page_name(page_ns, page_title),
		page_id = str(page_id),
		raw_page = request.args['page']
	)

if __name__ == '__main__':
	app.run(debug = config.getboolean('General', 'dev'))