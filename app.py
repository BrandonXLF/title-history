import mysql.connector
import requests
from flask import Flask, request, render_template
import dateutil.parser
import phpserialize
from configparser import ConfigParser

app = Flask(__name__)
config = ConfigParser('')
config.read('config.ini')

@app.route('/')
def movehist():
	def decode_bytes(x):
		return x.decode() if x else None
	
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

	if 'page' not in request.args:
		return 'Page required.'

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
SELECT revision.rev_timestamp, actor_name, log_namespace, log_title, comment_text, log_params, log_id FROM revision
JOIN page ON page_id = rev_page AND page_namespace = %s AND page_title = %s
# log entry might have a larger timestamp than the revision entry since it's added after
JOIN logging_userindex ON log_actor = rev_actor AND (log_timestamp = rev_timestamp OR log_timestamp = rev_timestamp + 1) AND log_type = 'move'
JOIN revision AS revision_parent ON revision_parent.rev_id = revision.rev_parent_id AND revision_parent.rev_len = revision.rev_len
LEFT JOIN comment_logging ON log_comment_id = comment_id
LEFT JOIN actor_logging ON log_actor = actor_id
ORDER BY log_timestamp DESC
'''

	cursor.execute(query, (page_ns, page_title))
	move_entries = cursor.fetchall()
	items = []

	for move_entry in move_entries:
		try:
			to_page = phpserialize.loads(move_entry[5])[b'4::target']
		except:
			to_page = move_entry[5]

		items.append({
			'type': 'move',
			'from': display_page_name(move_entry[2], decode_bytes(move_entry[3])),
			'to': decode_bytes(to_page),
			'time': dateutil.parser.parse(decode_bytes(move_entry[0])),
			'user': decode_bytes(move_entry[1]),
			'comment': decode_bytes(move_entry[4]),
			'id': str(move_entry[6])
		})

	return render_template(
		'index.html',
		items = items,
		project_url = project_url,
		page = display_page_name(page_ns, page_title),
		page_id = str(page_id)
	)

if __name__ == '__main__':
	app.run(debug = True)