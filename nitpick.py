#!/usr/bin/python
import os
import fileinput
import string


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


