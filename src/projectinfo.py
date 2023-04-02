import mysql.connector

def get_project_info(config, project):
	db = mysql.connector.connect(
		host = 'localhost' if config.getboolean('General', 'dev') else 'meta.web.db.svc.wikimedia.cloud',
		port = 4711 if config.getboolean('General', 'dev') else 3306,
		user = config['Database']['user'],
		password = config['Database']['pass'],
		db = 'meta_p'
	)
	cursor = db.cursor()

	cursor.execute(
		'SELECT dbname, url FROM wiki WHERE dbname = %s OR url = %s LIMIT 1',
		(project, 'https://' + project)
	)

	return cursor.fetchone()