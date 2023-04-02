import mysql.connector
from flask import render_template, abort
from datetime import datetime
import os
import phpserialize
import re
from .projectinfo import get_project_info
from .projectformatter import ProjectFormatter
from .config import config

def get_log_param_sql(formatter: ProjectFormatter, page_ns, page_title):
	page = formatter.format_title(page_ns, page_title)
	
	# Formats for log_param
	#
	# Very old Format:			[TITLE]
	# Old format:				[TITLE]\n
	# Old format (no redirect):	[TITLE]\n1
	# New format:				...s:9:"4::target";s:[TITLE LENGTH]:"[TITLE]";...
	return '(log_params = %s OR log_params = %s OR log_params = %s OR log_params LIKE %s)', (
		page,
		f"{page}\n",
		f"{page}\n1",
		f'%s:9:"4::target";s:{len(page)}:"{page}";%'
	)

def get_item(formatter: ProjectFormatter, move_entry):
	try:
		to_page = phpserialize.loads(move_entry[5])[b'4::target'].decode()
	except:
		to_page = move_entry[5].decode().split('\n', 1)[0]
		
	time = datetime.strptime(move_entry[0].decode(), '%Y%m%d%H%M%S')

	return {
		'type': 'move',
		'from': formatter.format_title(move_entry[2], move_entry[3].decode()),
		'to': to_page,
		'time': f'{time:%#I:%M:%S %p, %#d %B %Y}' if os.name == 'nt' else f'{time:%-I:%M:%S %p, %-d %B %Y}',
		'user': move_entry[1].decode(),
		'comment': move_entry[4].decode() and formatter.format_comment(move_entry[4].decode()),
		'id': str(move_entry[6])
	}

def crawl_entries(cursor, formatter: ProjectFormatter, starting_entry):
	items = []
	process_entry = starting_entry
	
	while process_entry:
		items.append(get_item(formatter, process_entry))
		
		log_param_sql, log_param_params = get_log_param_sql(formatter, process_entry[2], process_entry[3].decode())
		
		cursor.execute(
			f'''
			SELECT
				log_timestamp,
				actor_name,
				log_namespace,
				log_title,
				comment_text,
				log_params,
				log_id
			FROM logging_logindex
			LEFT JOIN comment_logging ON
				log_comment_id = comment_id
			LEFT JOIN actor_logging ON
				log_actor = actor_id
			WHERE
				log_id < %s
				AND log_type = 'move'
				AND {log_param_sql}
			ORDER BY log_id DESC
			LIMIT 1
			''',
			(process_entry[6],) + log_param_params
		)

		process_entry = cursor.fetchone()

	return items

def permalink(project, page_id):
	project_info = get_project_info(project)

	if not project_info:
		abort(404, f'Project {project} does not exist.')

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
		abort(404, f'Page with ID {page_id} does not exist.')
	
	page_ns = page_info[0]
	page_title = page_info[1].decode()
	log_param_sql, log_param_params = get_log_param_sql(formatter, page_ns, page_title)

	# TODO: this ignores moves before deleted log entry
	cursor.execute(
		f'''
		SELECT
			log_timestamp,
			actor_name,
			log_namespace,
			log_title,
			comment_text,
			log_params,
			log_id
		FROM logging_logindex
		LEFT JOIN comment_logging ON
			log_comment_id = comment_id
		LEFT JOIN actor_logging ON
			log_actor = actor_id
		WHERE
			log_type = 'move'
			AND {log_param_sql}
			AND NOT EXISTS(
				SELECT *
				FROM logging_logindex AS prev_log
				WHERE
					log_type = 'move'
					AND prev_log.log_namespace = %s
					AND prev_log.log_title = %s
					AND prev_log.log_id > logging_logindex.log_id
			)
		ORDER BY log_id DESC
		''',
		log_param_params + (page_ns, page_title)
	)

	items = []
	first = True
	
	for entry in cursor.fetchall():
		if not first:
			items[len(items) - 1]['gap'] = True
		
		items += crawl_entries(cursor, formatter, entry)
		first = False

	return render_template(
		'results.html',
		items = items,
		project = project,
		project_url = project_url,
		page = formatter.format_title(page_ns, page_title),
		page_id = page_id
	)