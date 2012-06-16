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

default_users = """
Unassigned
"""

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

	for line in fileinput.input(config.db_path + 'config/users'):
		config.users.append(string.strip(line))

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

	editor = ''
	if 'EDITOR' in os.environ:
		editor = os.environ['EDITOR']
	elif 'VISUAL' in os.environ:
		editor = os.editor['VISUAL']
	else:
		print 'Editor not found in $EDITOR, please set this variable and try again'
		return False

	issue = {
			'Title' : 'Issue title',
			'Severity' : ' '.join(config.issues['severity']),
			'Priority' : ' '.join(config.issues['priority']),
			'State'    : ' '.join(config.issues['state']),
			'Type'     : ' '.join(config.issues['type']),
			'Resolution' : ' '.join(config.issues['resolution']),
			'Component' : ' '.join(config.issues['components']),
			'Fix_By' : ' '.join(config.issues['fix_by']),
			'Seen_In_Build' : '',
			'Date' : time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()),
			'Owner' : config.users[0],
			'content' : 'Enter description here'
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

	for key in issue.keys():
		if key == 'content':
			continue

		print "%s: %s" % (key, issue[key])

	if 'content' in issue.keys():
		print '--'
		print issue['content']
	return True

def cmd_debug(args):
	load_issue_db()
	pprint.pprint(config.issue_db)
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
	cat_cmd.set_defaults(func=cmd_cat)

	debug_cmd = subcmds.add_parser('debug', help='Run the latest test code')
	debug_cmd.set_defaults(func=cmd_debug)

	args = parser.parse_args()
	result = args.func(args)

	if not result:
		print "Command failed"
		sys.exit(1)
	else:
		sys.exit(0)

