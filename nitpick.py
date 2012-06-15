#!/opt/local/bin/python2.7
import os
import os.path
import fileinput
import string
import argparse

class config:
	issues = {
			'components' : ['Documentation'],
			'fix_by' : ['Next_Release'],
			'priority' : ['1', '2', '3', '4', '5'],
			'state' : ['New', 'Confirmed', 'Open', 'Diagnosed', 'Fixed', 'Closed'],
			'severity' : ['Blocker', 'Critical', 'Major', 'Minor', 'Trivial'],
			'resolution': ['Fixed', 'WontFix', 'Invalid', 'WorksForMe'],
			'type' : ['Bug', 'Feature', 'Regression'],
		}
	users = ['Unassigned']
	db_path = ''

default_config = """
components: Documentation
fix_by: Next_Release
priority: 1 2 3 4 5
severity: Blocker Critical Major Minor Trivial
state: New Confirmed Open Diagnosed Fixed Closed
resolution: Fixed WontFix Invalid WorksForMe
type: Bug Feature Regression
"""

default_users = """
Unassigned
"""

# Root class of the VCS compatibility layer
class VCS:
	"""
	Simple VCS which uses basic unix filesystem commands
	"""
	
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
			config.db_path = pwd + '/.nitpick'
		pwd = os.path.dirname(pwd)
	if config.db_path == '':
		return False

	conf = parse_file(config.db_path + '/config/config')
	for key in ['components', 'fix_by', 'priority', 'severity', 'state', 'resolution', 'type']:
		if key in conf.keys():
			config.issues[key] = string.split(conf[key], sep = ' ')

	for line in fileinput.input(config.db_path + '/config/users'):
		config.users.append(string.strip(line))

	return True

def cmd_init(args):
	backend = BACKENDS[args.vcs]

	backend.mkdir(args.dir + '/config')

	config_filename = args.dir + '/config/config'
	config = open(config_filename, 'w')
	config.write(default_config)
	config.close()
	backend.add_changes(config_filename)

	users_filename = args.dir + '/config/users'
	users = open(users_filename, 'w')
	users.write(default_users)
	users.close()
	backend.add_changes(users_filename)

	backend.commit([config_filename, users_filename])

def cmd_debug(args):
	print load_config()

if __name__ == '__main__':
	parser = argparse.ArgumentParser(prog='nitpick', description='Distributed Bug Tracker')
	subcmds = parser.add_subparsers(help='commands help')

	init_cmd = subcmds.add_parser('init', help='Initialize nitpick database')
	init_cmd.add_argument('--vcs', default='file', help='Which VCS backend to use', choices=BACKENDS.keys())
	init_cmd.add_argument('--dir', default='./.nitpick', required=False,
			help='Directory to use as database, default ./.nitpick')
	init_cmd.set_defaults(func=cmd_init)

	debug_cmd = subcmds.add_parser('debug', help='Run the latest test code')
	debug_cmd.set_defaults(func=cmd_debug)

	args = parser.parse_args()
	args.func(args)
