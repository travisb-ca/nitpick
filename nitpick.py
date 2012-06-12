#!/usr/bin/python
import os
import fileinput
import string

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
	
	def mkdir(self, path):
		"""
		Create a directory, creating any parent directories if necessary
		"""
		os.system("mkdir -p " + path)

	def add_changes(self, path):
		"""
		Ensure that any changes made are registered with the VCS
		"""
		return

	def commit(self, path_list):
		"""
		Ensure that all the registered changes are committed to the VCS repository.

		This method receives a list of paths which must be committed.
		"""
		return

class SVN(VCS):
	def mkdir(self, path):
		os.system("svn mkdir --parents " + path)

	def add_changes(self, path):
		os.system("svn add " + path);

	def commit(self, path_list):
		os.system("svn ci -m \"Nitpick commit\" " + " ".join(path_list))

# A function which parses the given file into a dictionary with one entry for each piece of metadata
# and a 'content' entry for the open ended content.
def parse_file(path):
	data = {}
	for line in fileinput.input(path):
		if 'content' not in data: # Process metadata
			if line != '--\n':
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

def load_config():
	conf = parse_file('.nitpick/config/config')
	for key in ['components', 'fix_by', 'priority', 'severity', 'state', 'resolution', 'type']:
		if key in conf.keys():
			config.issues[key] = string.split(conf[key], sep = ' ')

	for line in fileinput.input('.nitpick/config/users'):
		config.users.append(string.strip(line))

