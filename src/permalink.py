import mysql.connector
from flask import render_template
from datetime import datetime
import os
import phpserialize
from .projectinfo import get_project_info
from .projectformatter import ProjectFormatter
from .config import config

def permalink(project, page_id):
	project_info = get_project_info(config, project)

	if not project_info:
		return render_template(
			'error.html',
			error = f'Project {project} does not exist.'
		)

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
		return render_template(
			'error.html',
			error = f'Page with ID {page_id} does not exist.'
		)
	
	page_name = formatter.format_title(page_info[0], page_info[1].decode())

	cursor.execute(
		'''
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
		WHERE
			revision.rev_page = %s
		ORDER BY
			log_timestamp DESC
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

		revision_comment = move_entry[4].decode()
		
		if (not (from_page in revision_comment or '[[' + from_page + ']]' in revision_comment) or
			not (to_page in revision_comment or ('[[' + to_page + ']]' in revision_comment))):
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