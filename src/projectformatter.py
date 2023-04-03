import requests
import re
import urllib.parse
from flask import escape
from cachelib import SimpleCache

namespace_cache = SimpleCache()

class ProjectFormatter:
	def __init__(self, project_url):
		self.project_url = project_url
		
		self.get_namespaces()

	def get_namespaces(self):
		self.namespaces = namespace_cache.get(self.project_url)

		if self.namespaces:
			return

		self.namespaces = {}
		
		res = requests.get(f'{self.project_url}/w/api.php?action=query&meta=siteinfo&siprop=namespaces&format=json&formatversion=2')\
			.json()['query']['namespaces']

		for namespace in res.values():
			self.namespaces[namespace['id']] = namespace['name']

		namespace_cache.set(self.project_url, self.namespaces, 86400)

	def replace_brackets(self, match):
		break_match = re.search(r'(.+?)\|(.+)', match.group(1))
		target = match.group(1)
		text = match.group(1)
		
		if break_match:
			target = break_match.group(1)
			text = break_match.group(2)
			
		return f'<a href="{self.project_url}/wiki/{urllib.parse.quote(target)}" target="_blank">{text}</a>'
		
	def format_comment(self, text):
		text = escape(text)
		return re.sub(r'\[\[(.+?)\]\]', self.replace_brackets, text)
	
	def format_title(self, namespace, title):
		if namespace == None or title == None:
			return None

		title = title.replace('_', ' ')
		ns_text = self.namespaces[namespace]
		
		if ns_text:
			return ns_text + ':' + title
			
		return title