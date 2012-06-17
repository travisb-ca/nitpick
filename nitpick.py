#!/opt/local/bin/python2.7
import os
import os.path
import fileinput
import string
import argparse
import time
import sys
import hashlib
import cPickle
import pprint
import BaseHTTPServer
import urllib

DATEFORMAT = '%Y-%m-%d %H:%M:%S'
FILLWIDTH = 69

# Contains the defaults used to initalize a database
class config:
	issues = {
			'components' : ['Documentation'],
			'fix_by' : ['Next_Release'],
			'priority' : ['1', '2', '3', '4', '5'],
			'state' : ['New', 'Confirmed', 'Open', 'Diagnosed', 'Fixed', 'Closed'],
			'severity' : ['Blocker', 'Critical', 'Major', 'Minor', 'Trivial'],
			'resolution': ['None', 'Fixed', 'WontFix', 'Invalid', 'WorksForMe'],
			'type' : ['Bug', 'Feature', 'Regression'],
		}
	users = ['Unassigned']
	vcs = None
	db_path = ''
	username = ''
	endweb = False

default_users = """
Unassigned
"""

class nitpick_web(BaseHTTPServer.BaseHTTPRequestHandler):
	def html_preamble(self, title):
		return """
			<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
			<html xmlns="http://www.w3.org/1999/xhtml" lang="en">
				<head>
					<title>%s</title>
				</head>
			<body>
			""" % (title)

	def html_postamble(self):
		return """</body></html>"""

	def start_doc(self, title):
		self.send_response(200)
		self.send_header('Content-type', 'text/html')
		self.end_headers()
		
		if title != '':
			title = ' - ' + title

		self.wfile.write(self.html_preamble('Nitpick' + title))

	def output(self, string):
		self.wfile.write(string)

	def end_doc(self):
		self.wfile.write(self.html_postamble())

	def root(self):
		load_issue_db()

		self.start_doc('')

		self.output('<table> <tr> <th>ID</th> <th>State</th> <th>Severity</th> <th>Priority</th> <th>Owner</th> <th>Title</th> </tr>\n')
		for issue in config.issue_db.keys():
			self.output('<tr>')
			self.output('<td><a href="/issue/%s">%s</a></td> ' % (issue, issue[:8]))
			self.output('<td><a href="/issue/%s">%s</a></td> ' % (issue, config.issue_db[issue]['State']))
			self.output('<td><a href="/issue/%s">%s</a></td> ' % (issue, config.issue_db[issue]['Severity']))
			self.output('<td><a href="/issue/%s">%s</a></td> ' % (issue, config.issue_db[issue]['Priority']))
			self.output('<td><a href="/issue/%s">%s</a></td> ' % (issue, config.issue_db[issue]['Owner']))
			self.output('<td><a href="/issue/%s">%s</a></td> ' % (issue, config.issue_db[issue]['Title']))
			self.output('</tr>\n')

		self.output('</table>')

		self.end_doc()

	def issue(self):
		issue_hash = self.path[7:]
		
		load_issue_db()

		self.start_doc('Issue %s' % issue_hash)

		issue = parse_file(config.issue_db[issue_hash]['path'] + '/issue')

		self.output('<form action="/update_issue" method="put">\n')
		self.output('<input type="hidden" name="issue" value="%s"/>\n' % issue_hash)

		self.output('Title: %s<br/>\n' % issue['Title'])
		self.output('Date: %s<br/>\n' % issue['Date'])
		self.output('Reported_By: %s<br/>\n' % issue['Reported_By'])
		self.output('Seen_In_Build: %s<br/>\n' % issue['Seen_In_Build'])

		# Severity
		self.output('Severity: <select name="severity">\n')
		for severity in config.issues['severity']:
			self.output('<option ')
			if severity == issue['Severity']:
				self.output('selected="selected" ')
			self.output('value="%s">%s</option>\n' % (severity, severity))
		self.output('</select><br/>\n')

		# Priority
		self.output('Priority: <select name="priority">\n')
		for priority in config.issues['priority']:
			self.output('<option ')
			if priority == issue['Priority']:
				self.output('selected="selected" ')
			self.output('value="%s">%s</option>\n' % (priority, priority))
		self.output('</select><br/>\n')

		# State
		self.output('State: <select name="state">\n')
		for state in config.issues['state']:
			self.output('<option ')
			if state == issue['State']:
				self.output('selected="selected" ')
			self.output('value="%s">%s</option>\n' % (state, state))
		self.output('</select><br/>\n')

		# Resolution
		self.output('Resolution: <select name="resolution">\n')
		for resolution in config.issues['resolution']:
			self.output('<option ')
			if resolution == issue['Resolution']:
				self.output('selected="selected" ')
			self.output('value="%s">%s</option>\n' % (resolution, resolution))
		self.output('</select><br/>\n')

		# Type
		self.output('Type: <select name="type">\n')
		for type in config.issues['type']:
			self.output('<option ')
			if type == issue['Type']:
				self.output('selected="selected" ')
			self.output('value="%s">%s</option>\n' % (type, type))
		self.output('</select><br/>\n')

		# Owner
		self.output('Owner: <select name="owner">\n')
		for owner in config.users:
			self.output('<option ')
			if owner == issue['Owner']:
				self.output('selected="selected" ')
			self.output('value="%s">%s</option>\n' % (owner, owner))
		self.output('</select><br/>\n')

		# Fix_By
		self.output('Fix_By: <select name="fix_by">\n')
		for fix_by in config.issues['fix_by']:
			self.output('<option ')
			if fix_by == issue['Fix_By']:
				self.output('selected="selected" ')
			self.output('value="%s">%s</option>\n' % (fix_by, fix_by))
		self.output('</select><br/>\n')

		# Component
		self.output('Component: <select name="component">\n')
		for component in config.issues['components']:
			self.output('<option ')
			if component == issue['Component']:
				self.output('selected="selected" ')
			self.output('value="%s">%s</option>\n' % (component, component))
		self.output('</select><br/>\n')

		self.output('<input type="submit" value="Update" />\n')

		self.output('</form>\n')

		self.output('<form action="/add_comment" method="get">\n')
		self.output('<input type="hidden" name="issue" value="%s"/>\n' % issue_hash)
		self.output('<input type="submit" value="Add Comment" /><br/>')
		self.output('</form>\n')

		comment_stack = produce_comment_tree(issue_hash)
		comment_stack.reverse()
		comment_depth = [1] * len(comment_stack)
		depth = 0

		while len(comment_stack) > 0:
			comment = comment_stack.pop()
			old_depth = depth
			depth = comment_depth.pop()

			for field in comment.keys():
				if field in ['content', 'children', 'Parent']:
					continue
				if field == 'Attachment' and comment['Attachment'] == '':
					continue

				self.output('%s: %s<br/>\n' % (field, comment[field]))

			self.output('<pre>\n')
			self.output(comment['content'])
			self.output('</pre>\n')

			self.output('<form action="/add_comment" method="get">\n')
			self.output('<input type="hidden" name="issue" value="%s"/>\n' % issue_hash)
			self.output('<input type="hidden" name="comment" value="%s"/>\n' % comment['hash'])
			self.output('<input type="submit" value="Reply" /><br/>')
			self.output('</form>\n')

			comment['children'].reverse()
			comment_stack.extend(comment['children'])
			comment_depth.extend([depth + 1] * len(comment['children']))

		self.end_doc()

	def add_comment(self):
		self.start_doc('Add Comment')

		if not 'issue' in self.request_args.keys():
			self.output('Incorrect script arguments')
			self.end_doc()
			return
		else:
			issue = self.request_args['issue']

		if not 'comment' in self.request_args.keys():
			comment = None
		else:
			comment = self.request_args['comment']

		load_issue_db()

		comment_parent = find_comment_parent(issue, comment)

		if comment_parent == None:
			self.output('No such issue')
			self.end_doc()
			return
		elif comment_parent == '':
			self.output('Ambiguous issue ID. Please use a longer string')
			self.end_doc()
			return
		else:
			issue = comment_parent[0]
			parent = comment_parent[1]
			if parent == None:
				self.output('No such comment.')
				self.end_doc()
				return
			elif parent == '':
				self.output('Ambiguous comment ID. Please use a longer string')
				self.end_doc()
				return

		# Here we know that the issue and parent are good to use
		self.output('<form action="/add_comment" method="post">\n')
		self.output('<input type="hidden" name="issue" value="%s"/>\n' % issue)
		self.output('<input type="hidden" name="parent" value="%s"/>\n' % parent)

		date = time.strftime(DATEFORMAT, time.gmtime())
		self.output('Date: %s<input type="hidden" name="date" value="%s"/><br/>\n' % (date, date))

		self.output('User: <select name="username">\n')
		for username in config.users:
			self.output('<option ')
			if username == config.username:
				self.output('selected="selected" ')
			self.output('value="%s">%s</option>\n' % (username, username))
		self.output('</select><br/>\n')

		self.output('Attachment: <br/>\n')

		self.output('<textarea name="content" rows="20" cols="80">Enter comment here</textarea><br/>\n')

		self.output('<input type="submit" value="Submit"/><br/>\n')
		self.output('</form>\n')

		self.end_doc()

	def add_comment_post(self):
		load_issue_db()

		print self.request_args

		if 'date' not in self.request_args.keys() or \
		   'parent' not in self.request_args.keys() or \
		   'username' not in self.request_args.keys() or \
		   'content' not in self.request_args.keys() or \
		   'issue' not in self.request_args.keys():
			   self.start_doc('Error')
			   self.output('Invalid arguments')
			   self.end_doc()
			   return

		comment = {
				'Date' : self.request_args['date'],
				'Parent' : self.request_args['parent'],
				'User' : self.request_args['username'],
				'Attachment' : '',
				'content' : self.request_args['content']
			}

		comment_filename = add_comment(self.request_args['issue'], comment)

		self.start_doc('Comment %s added' % comment_filename)
		self.output('Successfully added the comment<br/>\n')
		self.output('<a href="/">Back to issue list</a> ')
		self.output('<a href="/issue/%s"> Back to issue %s</a>\n' % (self.request_args['issue'], self.request_args['issue'][:8]))
		self.end_doc()

	def do_GET(self):
		print 'got get  path %s' % self.path

		self.request_args = {}
		args_start = self.path.find('?')
		if args_start != -1:
			# The path has arguments
			args = self.path[args_start + 1:]

			for var in args.split('&'):
				key_value = var.split('=')
				key = key_value[0]
				value = key_value[1]

				self.request_args[key] = value

		if self.path == '/':
			self.root()
		elif '/issue/' in self.path:
			self.issue()
		elif '/add_comment' in self.path:
			self.add_comment()
		else:
			print "Got unhandled path %s" % self.path
			self.root()

	def do_POST(self):
		print 'got post path %s' % self.path
		print self.headers

		self.request_args = {}
		args = self.rfile.read(int(self.headers['Content-Length']))
		for var in args.split('&'):
			key_value = var.split('=')
			key = urllib.unquote(key_value[0])
			value = urllib.unquote_plus(key_value[1])

			self.request_args[key] = value

		if '/add_comment' in self.path:
			self.add_comment_post()
		else:
			print 'Got unhandled path %s' % self.path
			self.root()


# Root class of the VCS compatibility layer
class VCS:
	"""
	Simple VCS which uses basic unix filesystem commands
	"""

	name = 'file'
	
	@staticmethod
	def mkdir(path):
		"""
		Create a directory, creating any parent directories if necessary
		"""
		os.system("mkdir -p " + path)

	@staticmethod
	def add_changes(path):
		"""
		Ensure that any changes made are registered with the VCS
		"""
		return

	@staticmethod
	def commit(path_list):
		"""
		Ensure that all the registered changes are committed to the VCS repository.

		This method receives a list of paths which must be committed.
		"""
		return

class SVN(VCS):
	name = 'svn'

	@staticmethod
	def mkdir(path):
		os.system("svn mkdir --parents " + path)

	@staticmethod
	def add_changes(path):
		os.system("svn add " + path);

	@staticmethod
	def commit(path_list):
		os.system("svn ci -m \"Nitpick commit\" " + " ".join(path_list))

BACKENDS = { 'file': VCS, 'svn' : SVN }

# A function which parses the given file into a dictionary with one entry for each piece of metadata
# and a 'content' entry for the open ended content.
def parse_file(path):
	data = {}
	for line in fileinput.input(path):
		if 'content' not in data: # Process metadata
			if line != '--\n' and len(line) > 1 and line[0] != '#':
				fields = string.split(line, sep = ':', maxsplit = 1)
				data[string.strip(fields[0])] = string.strip(fields[1])
			else:
				data['content'] = ""
		else: # Add to the content
			data['content'] += line

	return data

# Output to the given filename the data structure
def format_file(path, data):
	file = open(path, 'w')
	for key in data.keys():
		if key != 'content':
			file.write("%s: %s\n" % (key, data[key]))
	file.write('--\n')
	if 'content' in data:
		file.write("%s" % data['content'])
	file.close()

# Load the configuration out of the database.
#
# Returns True on success, False if the database couldn't be located
def load_config():
	# First we need to seek up until we find the database. It should be at the root of the project
	pwd = os.path.abspath('.')
	while pwd != '/':
		if os.path.exists(pwd + '/.nitpick') and os.path.isdir(pwd + '/.nitpick'):
			config.db_path = pwd + '/.nitpick/'
		pwd = os.path.dirname(pwd)
	if config.db_path == '':
		return False

	conf = parse_file(config.db_path + 'config/config')
	for key in ['components', 'fix_by', 'priority', 'severity', 'state', 'resolution', 'type']:
		if key in conf.keys():
			config.issues[key] = string.split(conf[key], sep = ' ')
	for key in ['vcs']:
		if key in conf.keys() and conf[key] in BACKENDS:
			config.vcs = BACKENDS[conf[key]]

	config.users = []
	for line in fileinput.input(config.db_path + 'config/users'):
		if line != '\n':
			config.users.append(string.strip(line))

	# Try to figure out the username to use.
	if 'NITPICK_USERNAME' in os.environ:
		config.username = os.environ['NITPICK_USERNAME']
	else:
		# Try to match the current user against the username list
		if 'USER' not in os.environ:
			print "Warning: Unable to determine username. Please set NITPICK_USERNAME"
		else:
			user = os.environ['USER']
			for row in config.users:
				if user in row:
					if config.username != '':
						print "Warning: Unable to determine username. Please set NITPICK_USERNAME"
						break
					else:
						config.username = row

	return True

# Save the issue_db cache after modifying it
def save_issue_db():
	cache_file = open(config.db_path + 'issue_cache', 'w')
	cPickle.dump(config.issue_db, cache_file)
	cache_file.close()

# Load the list of issues and some basic information about each one.
# Returns a dict keyed on issue hash which contains the a dict with all the
# fields in the issue files, except the content.
#
# An additional field of 'path' exists which is the directory of the issue
# An internal field of 'issue_db_cached_date' also exists.
def load_issue_db():
	try:
		cache_file = open(config.db_path + 'issue_cache', 'r')
		config.issue_db = cPickle.load(cache_file)
		cache_file.close()
	except:
		# Something is wrong with the cache, so start again
		config.issue_db = {}

	# Ensure that the cache is up to date
	for outer_dir in os.listdir(config.db_path):
		if len(outer_dir) != 1 or not os.path.isdir(config.db_path + outer_dir):
			continue

		for inner_dir in os.listdir(config.db_path + outer_dir):
			if len(inner_dir) != 1 or not os.path.isdir(config.db_path + outer_dir + '/' + inner_dir):
				continue

			for hash in os.listdir(config.db_path + outer_dir + '/' + inner_dir):
				hash_path = config.db_path + outer_dir + '/' + inner_dir + '/' + hash

				if hash not in config.issue_db or \
					config.issue_db[hash]['issue_db_cached_date'] != os.path.getmtime(hash_path + '/issue'):
					config.issue_db[hash] = parse_file(hash_path + '/issue')
					del config.issue_db[hash]['content']
					config.issue_db[hash]['issue_db_cached_date'] = os.path.getmtime(hash_path + '/issue')
				config.issue_db[hash]['path'] = hash_path
	save_issue_db()

# Turn a partial hash into a full hash
# Returns:
# 	- None on hash not found
# 	- '' on ambiguous result
# 	- the hash on success
def disambiguate_hash(partial_hash):
	fullhash = ''

	for hash in config.issue_db.keys():
		if partial_hash in hash:
			if fullhash != '':
				return ''
			else:
				fullhash = hash
	if fullhash == '':
		return None
	return fullhash

# Ensure that there is an editor to use for editing files
# Returns None and prints an error if no editor is found.
# Otherwise returns the editor to use
def editor_found():
	editor = ''
	if 'EDITOR' in os.environ:
		return os.environ['EDITOR']
	elif 'VISUAL' in os.environ:
		return os.editor['VISUAL']
	else:
		print 'Editor not found in $EDITOR, please set this variable and try again'
		return None

# Load the entire comment tree for the given issue hash and return it as a tree.
#
# The direct object is a list of comments. Each comment is then a dictionary with all the usual
# fields along with an additional field, 'children' which is a list of children comment.
def produce_comment_tree(issue):
	issue_path = config.issue_db[issue]['path'] + '/'

	# Load all the comments
	comments = {}
	for file in os.listdir(issue_path):
		if not os.path.isfile(issue_path + file):
			continue
		if '.' in file or file == 'issue': # Only select comments, not attachments or the root issue
			continue

		comments[file] = parse_file(issue_path + file)
		comments[file]['children'] = []
		comments[file]['hash'] = file

	# Pack them into a tree
	comment_tree = []
	for comment in comments.values():
		if comment['Parent'] == 'issue':
			comment_tree.append(comment)
		else:
			comments[comment['Parent']]['children'].append(comment)

	# Now order the tree based upon the dates
	for comment in comments.values():
		comment['children'].sort(key = lambda child: time.mktime(time.strptime(child['Date'], DATEFORMAT)))
	comment_tree.sort(key = lambda comment: time.mktime(time.strptime(comment['Date'], DATEFORMAT)))

	return comment_tree

def cmd_init(args):
	backend = BACKENDS[args.vcs]

	def_config = {'vcs' : args.vcs}
	for key in config.issues.keys():
		def_config[key] = ' '.join(config.issues[key])

	backend.mkdir(args.dir + '/config')

	config_filename = args.dir + '/config/config'
	format_file(config_filename, def_config)
	backend.add_changes(config_filename)

	users_filename = args.dir + '/config/users'
	users = open(users_filename, 'w')
	users.write(default_users)
	users.close()
	backend.add_changes(users_filename)

	backend.commit([config_filename, users_filename])

	return True

def cmd_new(args):
	if config.db_path == '':
		return False

	editor = editor_found()
	if editor == None:
		return False

	if config.username == '':
		print 'Failed to determine username, please set NITPICK_USERNAME'
		return False

	issue = {
			'Title'         : 'Issue title',
			'Severity'      : ' '.join(config.issues['severity']),
			'Priority'      : ' '.join(config.issues['priority']),
			'State'         : ' '.join(config.issues['state']),
			'Type'          : ' '.join(config.issues['type']),
			'Resolution'    : ' '.join(config.issues['resolution']),
			'Component'     : ' '.join(config.issues['components']),
			'Fix_By'        : ' '.join(config.issues['fix_by']),
			'Seen_In_Build' : '',
			'Date'          : time.strftime(DATEFORMAT, time.gmtime()),
			'Owner'         : config.users[0],
			'Reported_By'   : config.username,
			'content'       : 'Enter description here'
		}
	format_file(config.db_path + 'new.tmp', issue)
	result = os.system(editor + ' ' + config.db_path + 'new.tmp')

	if result != 0:
		print 'Creating issue aborted'
		os.unlink(config.db_path + 'new.tmp')
		return True

	issue = {}
	issue = parse_file(config.db_path + 'new.tmp')
	os.unlink(config.db_path + 'new.tmp')

	hash = hashlib.sha256(cPickle.dumps(issue)).hexdigest()

	issue_dir = config.db_path + hash[0] + '/' + hash[1] + '/' + hash
	config.vcs.mkdir(issue_dir)

	format_file(issue_dir + '/issue', issue)

	config.vcs.add_changes(issue_dir + '/issue')
	config.vcs.commit(issue_dir + '/issue')

	return True

def cmd_list(args):
	if config.db_path == '':
		return False

	load_issue_db()

	for hash in config.issue_db.keys():
		if not args.all and args.state != config.issue_db[hash]['State']:
			continue

		if not args.all and args.component and args.component != config.issue_db[hash]['Component']:
			continue

		if args.fullhash:
			printhash = hash
		else:
			printhash = hash[:8]
		print "%s (%s): %s" % (printhash, config.issue_db[hash]['State'], config.issue_db[hash]['Title'])
	return True

def cmd_cat(args):
	if config.db_path == '':
		return False

	load_issue_db()

	hash = disambiguate_hash(args.issue)
	if hash == None:
		print "No such issue"
		return False
	elif hash == '':
		print "Ambiguous issue ID. Please use a longer string"
		return False

	issue = parse_file(config.db_path + hash[0] + '/' + hash[1] + '/' + hash + '/issue')

	if not args.noformat:
		print '+' + '=' * FILLWIDTH

	for key in issue.keys():
		if key == 'content':
			continue

		if not args.noformat:
			print '|',
		print "%s: %s" % (key, issue[key])

	if 'content' in issue.keys():
		if not args.noformat:
			print '+' + '-' * FILLWIDTH
			print '|',
		else:
			print '--'

		if not args.noformat:
			print '\n| '.join(issue['content'].split('\n'))
		else:
			print issue['content']

		if not args.noformat:
			print '+' + '=' * FILLWIDTH

	comment_stack = produce_comment_tree(hash)
	comment_stack.reverse()
	comment_depth = [1] * len(comment_stack)
	depth = 0

	while len(comment_stack) > 0:
		comment = comment_stack.pop()
		old_depth = depth
		depth = comment_depth.pop()

		if not args.noformat and old_depth > depth:
			print '  ' * depth + '+' + '=' * FILLWIDTH

		for key in comment.keys():
			if key in ['content', 'children', 'Parent']:
				continue
			if key == 'Attachment' and comment['Attachment'] == '':
				continue

			if not args.noformat:
				print '  ' * depth + '|',

			print "%s: %s" % (key, comment[key])
		if 'content' in comment.keys():
			if not args.noformat:
				print '  ' * depth + '+' + '-' * FILLWIDTH
			else:
				print '--'

			if not args.noformat:
				print '  ' * depth + '| ',
				print ('\n' + '  ' * depth + '| ').join(comment['content'].split('\n'))
			else:
				print comment['content']

			if not args.noformat:
				print '  ' * depth + '+' + '=' * FILLWIDTH

		comment['children'].reverse()
		comment_stack.extend(comment['children'])
		comment_depth.extend([depth + 1] * len(comment['children']))

	return True

# Check that the issue exists and that it has the comment to reply to if one is supplied.
# Returns
# 	(issue hash, parent id) - on Success
# 	None                    - If the issue does not exist
# 	''                      - If the issue is ambiguous
# 	(issue hash, None)      - If a comment was specified and it doesn't exist
# 	(issue hash, '')        - If the comment is ambiguous
def find_comment_parent(partial_issue, partial_comment):
	issue = disambiguate_hash(partial_issue)
	if issue == None:
		return None
	elif issue == '':
		return ''

	parent = 'issue'

	if partial_comment:
		for file in os.listdir(config.issue_db[issue]['path']):
			if not os.path.isfile(config.issue_db[issue]['path'] + '/' + file):
				continue
			if '.' in file or file == 'issue': # Only support comments, not attachments or the root issue
				continue

			if partial_comment in file:
				if parent != 'issue':
					return (issue, '')
				else:
					parent = file
		if parent == 'issue':
			return (issue, None)
	
	return (issue, parent)

# Take a comment dict and add it to the system. Does not commit.
#
# Returns the comment filename
def add_comment(issue, comment):
	hash = hashlib.sha256(cPickle.dumps(comment)).hexdigest()

	comment_filename = config.issue_db[issue]['path'] + '/' + hash
	format_file(comment_filename, comment)

	config.vcs.add_changes(comment_filename)

	return comment_filename

def cmd_comment(args):
	if config.db_path == '':
		return False

	editor = editor_found()
	if editor == None:
		return False

	if config.username == '':
		print 'Failed to determine username. Please set NITPICK_USERNAME'
		return False

	load_issue_db()

	comment_parent = find_comment_parent(args.issue, args.comment)
	if comment_parent == None:
		print 'No such issue'
		return False
	elif comment_parent == '':
		print 'Ambiguous issue ID. Please use a longer string'
		return False
	else:
		issue = comment_parent[0]
		parent = comment_parent[1]
		if parent == None:
			print 'No such comment.'
			return False
		elif parent == '':
			print 'Ambiguous comment ID. Please use a longer string'
			return False

	comment = {
			'Attachment' : '',
			'Date'       : time.strftime(DATEFORMAT, time.gmtime()),
			'Parent'     : parent,
			'User'       : config.username,
			'content'    : 'Enter comment here'
		}
	comment_filename = config.issue_db[issue]['path'] + '/comment.tmp'
	format_file(comment_filename, comment)
	result = os.system(editor + ' ' + comment_filename)

	if result != 0:
		print 'Comment aborted'
		os.unlink(comment_filename)
		return True

	comment = {}
	comment = parse_file(comment_filename)
	os.unlink(comment_filename)

	comment_filename = add_comment(issue, comment)

	config.vcs.commit(comment_filename)
	return True

def change_issue(prop, newvalue):
	if config.db_path == '':
		return False

	load_issue_db()

	issue = disambiguate_hash(args.issue)
	if issue == None:
		print' No such issue'
		return False
	elif issue == '':
		print "Ambiguous issue ID. Please use a longer string"
		return False

	issue_filename = config.issue_db[issue]['path'] + '/issue'
	issue = parse_file(issue_filename)
	issue[prop] = newvalue
	format_file(issue_filename, issue)

	config.vcs.add_changes(issue_filename)
	config.vcs.commit(issue_filename)

	return True

def cmd_state(args):
	return change_issue('State', args.newstate)

def cmd_severity(args):
	return change_issue('Severity', args.newseverity)

def cmd_component(args):
	return change_issue('Component', args.newcomponent)

def cmd_priority(args):
	return change_issue('Priority', args.newpriority)

def cmd_resolution(args):
	return change_issue('Resolution', args.newresolution)

def cmd_type(args):
	return change_issue('Type', args.newtype)

def cmd_fixby(args):
	return change_issue('Fix_By', args.newfixby)

def cmd_owner(args):
	fulluser = ''
	for row in config.users:
		if args.newowner in row:
			if fulluser != '':
				print "Ambiguous user. Please be more specific"
				return False
			else:
				fulluser = row

	if fulluser == '':
		print "Unknown user"
		return False

	return change_issue('Owner', fulluser)

def cmd_users(args):
	if config.db_path == '':
		return False

	for user in config.users:
		print user
	return True

def cmd_web(args):
	if config.db_path == '':
		return False

	load_issue_db()

	server = BaseHTTPServer.HTTPServer(('localhost', args.port), nitpick_web)

	print 'Starting server on localhost:%d' % args.port

	while not config.endweb:
		server.handle_request()

	return True

if __name__ == '__main__':
	load_config()

	parser = argparse.ArgumentParser(prog='nitpick', description='Distributed Bug Tracker')
	subcmds = parser.add_subparsers(help='commands help')

	init_cmd = subcmds.add_parser('init', help='Initialize nitpick database')
	init_cmd.add_argument('--vcs', default='file', help='Which VCS backend to use', choices=BACKENDS.keys())
	init_cmd.add_argument('--dir', default='./.nitpick', required=False,
			help='Directory to use as database, default ./.nitpick')
	init_cmd.set_defaults(func=cmd_init)

	new_cmd = subcmds.add_parser('new', help='Create a new issue')
	new_cmd.set_defaults(func=cmd_new)

	list_cmd = subcmds.add_parser('list', help='Print filtered list of issues')
	list_cmd.add_argument('--all', action='store_true', help='List all issues')
	list_cmd.add_argument('--fullhash', action='store_true', help='Display the full hash instead of a truncation')
	list_cmd.add_argument('--state', default='Open', help='Display only issues in the given state',
			choices=config.issues['state'])
	list_cmd.add_argument('--component', help='Display only issues for the given component',
			choices=config.issues['components'])
	list_cmd.set_defaults(func=cmd_list)

	cat_cmd = subcmds.add_parser('cat', help='Print the given issue to the console')
	cat_cmd.add_argument('issue')
	cat_cmd.add_argument('--noformat', action='store_true', help='Disable formatting when displaying')
	cat_cmd.set_defaults(func=cmd_cat)

	comment_cmd = subcmds.add_parser('comment', help='Add a comment to an issue')
	comment_cmd.add_argument('issue')
	comment_cmd.add_argument('--comment', help='Respond to specific comment')
	comment_cmd.set_defaults(func=cmd_comment)

	state_cmd = subcmds.add_parser('state', help='Set the state of an issue')
	state_cmd.add_argument('issue')
	state_cmd.add_argument('newstate', choices=config.issues['state'])
	state_cmd.set_defaults(func=cmd_state)

	severity_cmd = subcmds.add_parser('severity', help='Set the severity of an issue')
	severity_cmd.add_argument('issue')
	severity_cmd.add_argument('newseverity', choices=config.issues['severity'])
	severity_cmd.set_defaults(func=cmd_severity)

	component_cmd = subcmds.add_parser('component', help='Set the component of an issue')
	component_cmd.add_argument('issue')
	component_cmd.add_argument('newcomponent', choices=config.issues['components'])
	component_cmd.set_defaults(func=cmd_component)

	priority_cmd = subcmds.add_parser('priority', help='Set the priority of an issue')
	priority_cmd.add_argument('issue')
	priority_cmd.add_argument('newpriority', choices=config.issues['priority'])
	priority_cmd.set_defaults(func=cmd_priority)

	resolution_cmd = subcmds.add_parser('resolution', help='Set the resolution of an issue')
	resolution_cmd.add_argument('issue')
	resolution_cmd.add_argument('newresolution', choices=config.issues['resolution'])
	resolution_cmd.set_defaults(func=cmd_resolution)

	type_cmd = subcmds.add_parser('type', help='Set the type of an issue')
	type_cmd.add_argument('issue')
	type_cmd.add_argument('newtype', choices=config.issues['type'])
	type_cmd.set_defaults(func=cmd_type)

	fixby_cmd = subcmds.add_parser('fixby', help='Set the fixby of an issue')
	fixby_cmd.add_argument('issue')
	fixby_cmd.add_argument('newfixby', choices=config.issues['fix_by'])
	fixby_cmd.set_defaults(func=cmd_fixby)

	owner_cmd = subcmds.add_parser('owner', help='Set the owner of an issue')
	owner_cmd.add_argument('issue')
	owner_cmd.add_argument('newowner')
	owner_cmd.set_defaults(func=cmd_owner)

	users_cmd = subcmds.add_parser('users', help='List configured users')
	users_cmd.set_defaults(func=cmd_users)

	web_cmd = subcmds.add_parser('web', help='Start nitpick web interface')
	web_cmd.add_argument('--port', type=int, default=18080, help='Start the web server on the given port. Default 18080')
	web_cmd.add_argument('--browser', help='Command to use to open web interface in browser')
	web_cmd.set_defaults(func=cmd_web)

	args = parser.parse_args()
	result = args.func(args)

	if not result:
		print "Command failed"
		sys.exit(1)
	else:
		sys.exit(0)

