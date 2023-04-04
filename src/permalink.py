import mysql.connector
from flask import render_template
from datetime import datetime
import os
import phpserialize
import re
from .projectinfo import get_project_info
from .projectformatter import ProjectFormatter
from .config import config
from .error import ProcessError

def page_in_comment(page, comment):
	return re.compile('(\[\[| |^)' + re.escape(page) + '(\]\]| |$)').search(comment)

def permalink(project, page_id):
	project_info = get_project_info(project)

	if not project_info:
		raise ProcessError(f'Project {project} does not exist.', 404, project)

	(project_db, project_url) = project_info
	formatter = ProjectFormatter(project_url)

	db = mysql.connector.connect(
		host = 'localhost' if config.getboolean('General', 'dev') else project_db + '.web.db.svc.wikimedia.cloud',
		port = 4712 if config.getboolean('General', 'dev') else 3306,
		user = config['Database']['user'],
		password = config['Database']['pass'],
		db = project_db + '_p'
	)
	cursor = db.cursor()

	cursor.execute(
		'SELECT page_namespace, page_title FROM page WHERE page_id = %s LIMIT 1',
		(page_id,)
	)

	page_info = cursor.fetchone()

	if not page_info:
		raise ProcessError(f'Page with ID {page_id} does not exist.', 404, project)

	page_name = formatter.format_title(page_info[0], page_info[1].decode())

	# Considerations:
	# - Compare against parent revision to make sure content hasn't changed
	# - Log entry might have a larger timestamp than the revision since it's added after
	cursor.execute(
		'''
		SELECT
			log_timestamp,
			actor_name,
			log_namespace,
			log_title,
			comment_revision.comment_text,
			comment_revision.comment_text,
			log_params,
			log_id
		FROM revision_userindex
		JOIN logging_userindex ON
			log_type = 'move'
			AND log_actor = rev_actor
			AND log_timestamp BETWEEN rev_timestamp AND CAST(CAST(rev_timestamp AS DATETIME) + 30 AS BINARY)
		JOIN comment_revision ON
			rev_comment_id = comment_revision.comment_id
		JOIN comment_logging ON
			log_comment_id = comment_logging.comment_id
		JOIN actor_logging ON
			log_actor = actor_id
		WHERE
			rev_page = %s
			AND EXISTS (
				SELECT *
				FROM revision_userindex AS p_rev
				WHERE
					p_rev.rev_id = revision_userindex.rev_parent_id
					AND p_rev.rev_sha1 = revision_userindex.rev_sha1
			)
		ORDER BY log_timestamp DESC
		''',
		(page_id,)
	)

	items = []
	prev_from = None

	for move_entry in cursor.fetchall():
		from_page = formatter.format_title(move_entry[2], move_entry[3].decode())
		
		try:
			to_page = phpserialize.loads(move_entry[6])[b'4::target'].decode()
		except:
			to_page = move_entry[6].decode().partition('\n')[0]

		rev_comment = move_entry[4].decode()

		# Filter out talk pages and subpages moved at the same time
		if not page_in_comment(from_page, rev_comment) or not page_in_comment(to_page, rev_comment):
			continue

		time = datetime.strptime(move_entry[0].decode(), '%Y%m%d%H%M%S')

		items.append({
			'type': 'move',
			'from': from_page,
			'to': to_page,
			'time': f'{time:%#I:%M:%S %p, %#d %B %Y}' if os.name == 'nt' else f'{time:%-I:%M:%S %p, %-d %B %Y}',
			'user': move_entry[1].decode(),
			'comment': move_entry[5].decode() and formatter.format_comment(move_entry[5].decode()),
			'id': str(move_entry[7])
		})
		
		if prev_from and prev_from != to_page:
			items[len(items) - 2]['gap'] = True
		
		prev_from = from_page

	return render_template(
		'results.html',
		items = items,
		project = project,
		project_url = project_url,
		page = page_name,
		page_id = page_id
	)