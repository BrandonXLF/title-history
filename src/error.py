from werkzeug.exceptions import HTTPException

class ProcessError(HTTPException):
	def __init__(self, msg: str, code: int, project: str = None, page: str = None):
		self.description = msg
		self.code = code
		self.project = project
		self.page = page
