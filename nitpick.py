#!/usr/bin/env python2.7
# 
# Copyright (C) 2012, 2013  Travis Brown (travisb@travisbrown.ca)
# 
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# version 2 as published by the Free Software Foundation.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

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
import gzip
import subprocess
import copy
import re
import base64
import cgi
import uuid
import cgi
import datetime
import json

DATEFORMAT = '%Y-%m-%d %H:%M:%S'
FILLWIDTH = 69
ISSUE_CACHE_FORMAT = 2
URL_REGEX = '([a-z]+://[a-zA-Z0-9-]+\.[a-zA-Z0-9.]+(:[0-9]+){0,1}[a-zA-Z0-9/\-.%&?=+_,#;]*)'
ISSUE_REGEX = '(?<= )([a-f0-9]{8,64})'
POSIX_CLI_BROWSERS = ['w3m', 'elinks', 'links', 'lynx']
POSIX_GUI_BROWSERS = [ ('chrome', 'google-chrome'), ('firefox-bin', 'firefox') ]
NUM_FIXBY_COLOURS = 13
USE_UPLOADED_NAME = 'filename.bin'

# Contains the defaults used to initalize a database
class config:
	issues = {
			'components' : ['Documentation'],
			'fix_by' : ['Next_Release'],
			'priority' : ['1', '2', '3', '4', '5'],
			'state' : ['New', 'Open', 'Diagnosed', 'Fixed', 'Closed'],
			'severity' : ['Blocker', 'Critical', 'Major', 'Minor', 'Trivial'],
			'resolution': ['None', 'Fixed', 'Duplicate', 'WontFix', 'Invalid', 'WorksForMe'],
			'type' : ['Bug', 'Feature', 'Regression'],
		}
	users = ['Unassigned']
	vcs = None
	project_name = 'Nitpick Project'
	use_schedule = False
	db_path = ''
	username = ''
	endweb = False
	uncommitted_changes = False
	readonly = False

default_users = """
Unassigned
"""

default_config = copy.deepcopy(config.issues)

db = None
def load_db():
	global db
	db = IssueDB()

class nitpick_web(BaseHTTPServer.BaseHTTPRequestHandler):
	def log_request(code = -1, size = -1):
		pass

	def css(self):
		self.send_response(200)
		self.send_header('Content-type', 'text/css')
		self.end_headers()

		self.output("""
			.issue_metadata {
				padding: 0.5 0.5 0.5em;
				margin: 1em;
				border-style: solid;
				border-width: 0.1em;
			}

			.issue_metadata p {
				margin: 0.5em;
			}

			.issue_comments {
				margin-bottom: 1em;
			}

			.issue_comment_content {
				padding: 0.5 0.5 0.5em;
				border-style: solid;
				border-width: 0.1em;
			}

			.issue_comment_content p {
				margin: 0.5em;
				white-space: pre-wrap;
				font-family: Monospace;
			}

			.issue_comment_children {
				padding-left: 3em;
			}

			.field_select_box {
				padding: 0.5 0.5 0.5em;
				margin: 1em;
				border-style: solid;
				border-width: 0.1em;
			}

			.field_select_item {
				display: inline-block;
			}

			.filter_select_box {
				padding: 0.5 0.5 0.5em;
				margin: 1em;
				border-style: solid;
				border-width: 0.1em;
			}

			.filter_select_item {
				margin: 0.5em;
				display: inline-block;
			}

			.issue_list table {
				border-style: solid;
				border-width: 0.1em;
				margin-top: 1em;
				margin-bottom: 1em;
				margin-left: auto;
				margin-right: auto;
				width: 90%%;
			}

			.issue_list td {
				padding-right: 0.5em;
				padding-left: 0.5em;
				text-align: center;
			}

			.issue_list th {
				padding-right: 0.5em;
				padding-left: 0.5em;
				text-align: center;
				font-size: 125%%;
			}

			.issue_list a:link { text-decoration: none; }
			.issue_list a:hover { text-decoration: underline; }

			/* Separate tr1 and tr2 to alternate colours */
			.issue_list_tr0 {
				background: White;
			}

			.issue_list_tr1 {
				background: LightGrey;
			}

			.add_comment p {
				margin: 0.5em;
			}

			.add_comment textarea {
				font-family: Monospace;
			}

			/* .new_issue_metadata {} */

			.new_issue {
				margin: 0.5em 0.5em 0.5em 0.5em;
			}

			.new_issue textarea {
				font-family: Monospace;
			}

			.new_issue_text_wrapper {
				width: 100%%;
				float: left;
				margin-bottom: 1em;
			}

			.new_issue_metadata_column {
				float: left;
				padding-right: 2em;
				margin: 0em;
			}

			.command_button {
				float: left;
			}

			.command_bar {
				width: 100%%;
			}

			.schedule table {
				border-style: solid;
				border-width: 0.1em;
				margin-top: 1em;
				margin-bottom: 1em;
				margin-left: auto;
				margin-right: auto;
			}

			.schedule td {
				padding-right: 0.5em;
				padding-left: 0.5em;
				text-align: center;
			}

			.schedule_td {
				overflow: hidden;
			}

			.schedule th {
				padding-right: 0.5em;
				padding-left: 0.5em;
				text-align: center;
				vertical-align: bottom;
				font-size: 125%%;
			}

			.schedule_user {
				width: 0.5em;
			}

			.schedule_user th {
				width: 1em;
				letter-spacing: 0.1em;
				text-align: center;
			}

			.schedule a:link { text-decoration: none; }
			.schedule a:hover { text-decoration: underline; }

			/* Separate col1 and col2 to alternate colours */
			.schedule_col0 {
				background: White;
			}

			.schedule_col1 {
				background: LightGrey;
			}

			.schedule_gap {
				background: Aquamarine;
			}

			.schedule_fixby0 {
				background: Aqua;
			}

			.schedule_fixby1 {
				background: BurlyWood;
			}

			.schedule_fixby2 {
				background: Chartreuse;
			}

			.schedule_fixby3 {
				background: Coral
			}

			.schedule_fixby4 {
				background: DarkKhaki;
			}

			.schedule_fixby5 {
				background: DarkSeaGreen;
			}

			.schedule_fixby6 {
				background: DarkTurquoise;
			}

			.schedule_fixby7 {
				background: GhostWhite;
			}

			.schedule_fixby8 {
				background: Gold;
			}

			.schedule_fixby9 {
				background: GreenYellow;
			}

			.schedule_fixby10 {
				background: Lavender;
			}

			.schedule_fixby11 {
				background: LightBlue;
			}

			.schedule_fixby12 {
				background: LightPink;
			}
		""")

	def html_preamble(self, title, onload_focus):
		if onload_focus is not None:
			focus_script = 'OnLoad="document.%s.focus();"' % onload_focus
		else:
			focus_script = ''

		return """
			<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
			<html xmlns="http://www.w3.org/1999/xhtml" lang="en">
				<head>
					<link rel="icon" href="http://localhost:18080/favicon.ico" />
					<link rel="stylesheet" href="/css.css" type="text/css" title="Default Style" media="screen" />
					<title>%s</title>
				</head>
			<body %s>
			<div style="width: 100%%;float: left;">
			""" % (title, focus_script)

	def html_postamble(self):
		if config.readonly:
			js = '<script src="/js.js"></script>'
		else:
			js = ''

		return """</div><br/>
			Tracked by <a href="http://travisbrown.ca/projects/nitpick/docs/nitpick.html">Nitpick</a>
			%s
			</body></html>""" % js

	def output(self, string):
		self.wfile.write(string)

	def start_doc(self, title, onload_focus = None):
		self.send_response(200)
		self.send_header('Content-type', 'text/html')
		self.end_headers()
		
		if title != '':
			title = title + ' - '

		self.output(self.html_preamble(title + 'Nitpick', onload_focus))

		if not config.readonly:
			self.output('<div class="command_bar">\n')
			self.output('<span class="command_button"><form action="/shutdown" method="post">')
			self.output('<input type="submit" value="Exit Web Interface"/></form></span>\n')
			if config.uncommitted_changes and config.vcs.real:
				self.output('<span class="command_button"><form action="/commit" method="post">')
				self.output('<input type="submit" value="Commit Changes"/></form></span>\n')
				self.output('<span class="command_button"><form action="/revert" method="post">')
				self.output('<input type="submit" value="Revert Changes"/></form></span>\n')
			self.output('</div>\n')

		self.output('<br/>\n')

	def end_doc(self):
		self.wfile.write(self.html_postamble())

	def favicon(self):
		self.send_response(200)
		self.send_header('Content-type', 'image/vnd.microsoft.icon')
		self.end_headers()
		self.output(base64.b64decode(
			'''AAABAAEAEBACAAAAAACwAAAAFgAAACgAAAAQAAAAIAAAAAEAAQAAAAAAQAAAAAAAAAAAAAAA
			AgAAAAAAAAAA/x4A/wgAAP//AAD//wAA5+cAAOfHAADnhwAA54cAAOcnAADnJwAA5mcAAOZn
			AADk5wAA5OcAAOHnAADj5wAA//8AAP//AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
			AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
			'''))

	# Format the issue as a link with useful information. If description is True then the
	# description will be used as the text instead of the partial hash.
	def format_issue(self, issue, description=False):
		leader = ''
		follower = ''

		issue2 = db.disambiguate_hash(issue)
		if issue2 != None and issue2 != '':
			issue = issue2

		if issue in db.issues() and db.issue(issue)['State'] == config.issues['state'][-1]:
			leader = '<strike>'
			follower = '</strike>'

		i = db.issue(issue)
		if i != None:
			title = '%s: %s' % (issue[:8], i['Title'])
		else:
			title = ''

		if not description or i == None or i['Title'] == '':
			desc = issue[:8]
		else:
			desc = i['Title']

		output = '%s<a title="%s" href="/issue/%s">%s</a>%s' % (leader, title, issue, desc, follower)
		return output

	def root(self):
		db.load_issue_db()

		self.start_doc('')

		if not config.readonly:
			self.output('<p><a href="/new_issue">Create new issue</a>\n')

		if config.use_schedule:
			self.output(' <a href="/schedule">Show Schedule</a></p>\n')

		if self.request_args == {}:
			# Use defaults since this is the first time here
			show_repo          = db.has_nonclones()
			show_ID            = True
			show_type          = False
			show_date          = False
			show_severity      = True
			show_priority      = True
			show_component     = False
			show_fix_by        = False
			show_seen_in_build = False
			show_state         = True
			show_resolution    = False
			show_owner         = True
			show_title         = True
		else:
			# Use whatever the user provided
			show_repo          = False
			show_ID            = False
			show_type          = False
			show_date          = False
			show_severity      = False
			show_priority      = False
			show_component     = False
			show_fix_by        = False
			show_seen_in_build = False
			show_state         = False
			show_resolution    = False
			show_owner         = False
			show_title         = False

		filter_repo       = []
		filter_components = []
		filter_fix_by     = []
		filter_severity   = []
		filter_priority   = []
		filter_state      = config.issues['state'][:-1] # Don't show closed items by default
		filter_resolution = []
		filter_type       = []
		filter_owner      = []

		sort_field = 'State' # Sort by state by default
		reverse_sort = False

		def extract_show_field_arg(arg_name, arg_val):
			if arg_name in self.request_args.keys():
				arg_val = self.request_args[arg_name] == '1'
			return arg_val

		if db.has_foreign():
			show_repo  = extract_show_field_arg('show_repo',          show_repo)
		show_ID            = extract_show_field_arg('show_ID',            show_ID)
		show_type          = extract_show_field_arg('show_type',          show_type)
		show_date          = extract_show_field_arg('show_date',          show_date)
		show_severity      = extract_show_field_arg('show_severity',      show_severity)
		show_priority      = extract_show_field_arg('show_priority',      show_priority)
		show_component     = extract_show_field_arg('show_component',     show_component)
		show_fix_by        = extract_show_field_arg('show_fix_by',        show_fix_by)
		show_seen_in_build = extract_show_field_arg('show_seen_in_build', show_seen_in_build)
		show_state         = extract_show_field_arg('show_state',         show_state)
		show_resolution    = extract_show_field_arg('show_resolution',    show_resolution)
		show_owner         = extract_show_field_arg('show_owner',         show_owner)
		show_title         = extract_show_field_arg('show_title',         show_title)

		def extract_filter_arg(arg_name, arg_val):
			if arg_name in self.request_args.keys():
				if type(self.request_args[arg_name]) == type([]):
					arg_val = self.request_args[arg_name]
				else:
					arg_val = [self.request_args[arg_name]]
			return arg_val

		if db.has_foreign():
			filter_repo = extract_filter_arg('filter_repo',     filter_repo)
		filter_components = extract_filter_arg('filter_components', filter_components)
		filter_fix_by     = extract_filter_arg('filter_fix_by',     filter_fix_by)
		filter_severity   = extract_filter_arg('filter_severity',   filter_severity)
		filter_priority   = extract_filter_arg('filter_priority',   filter_priority)
		filter_state      = extract_filter_arg('filter_state',      filter_state)
		filter_resolution = extract_filter_arg('filter_resolution', filter_resolution)
		filter_type       = extract_filter_arg('filter_type',       filter_type)
		filter_owner      = extract_filter_arg('filter_owner',      filter_owner)

		if 'sort_field' in self.request_args.keys():
			sort_field = self.request_args['sort_field']

		reverse_sort = extract_show_field_arg('reverse_sort', reverse_sort)

		if config.readonly:
			self.output('<form>\n')
		else:
			self.output('<form action="/" method="get">\n')
		self.output('<input type="hidden" name="sort_field" value="%s"/>\n' % sort_field)
		self.output('<input type="hidden" name="reverse_sort" value="%s"/>\n' % reverse_sort)

		# Which fields to display
		def output_field_selectors(label, arg_name, bool):
			self.output('<div class="field_select_item"><label>%s:</label><input type="checkbox" name="%s" value="1" ' % (label, arg_name))
			if bool:
				self.output('checked="checked"')
			self.output('/></div>\n')

		self.output('<div class="field_select_box">\n')
		self.output('Select Fields to Display<br/>\n')
		if db.has_foreign():
			output_field_selectors('Project',  'show_repo',          show_repo)
		output_field_selectors('ID',            'show_ID',            show_ID)
		output_field_selectors('Type',          'show_type',          show_type)
		output_field_selectors('Date',          'show_date',          show_date)
		output_field_selectors('Severity',      'show_severity',      show_severity)
		output_field_selectors('Priority',      'show_priority',      show_priority)
		output_field_selectors('Component',     'show_component',     show_component)
		output_field_selectors('Fix_By',        'show_fix_by',        show_fix_by)
		output_field_selectors('Seen_In_Build', 'show_seen_in_build', show_seen_in_build)
		output_field_selectors('State',         'show_state',         show_state)
		output_field_selectors('Resolution',    'show_resolution',    show_resolution)
		output_field_selectors('Owner',         'show_owner',         show_owner)
		output_field_selectors('Title',         'show_title',         show_title)
		self.output('</div>\n')

		# Filters
		def output_filter_options(label, option_name, option_list, selected_list):
			self.output('<div class="filter_select_item"><label>%s:</label><select name="%s" multiple="multiple" size="5">\n' % (label, option_name))
			for option in option_list:
				self.output('<option ')
				if option in selected_list or selected_list == []:
					self.output('selected="selected" ')
				self.output('value="%s">%s</option>\n' % (option, option))
			self.output('</select></div>\n')

		self.output('<div class="filter_select_box">\n')
		if db.has_foreign():
			output_filter_options('Project', 'filter_repo', db.repos(),                filter_repo)
		output_filter_options('Components', 'filter_components', config.issues['components'], filter_components)
		output_filter_options('Fix_By',     'filter_fix_by',     config.issues['fix_by'],     filter_fix_by)
		output_filter_options('Severity',   'filter_severity',   config.issues['severity'],   filter_severity)
		output_filter_options('Priority',   'filter_priority',   config.issues['priority'],   filter_priority)
		output_filter_options('State',      'filter_state',      config.issues['state'],      filter_state)
		output_filter_options('Resolution', 'filter_resolution', config.issues['resolution'], filter_resolution)
		output_filter_options('Type',       'filter_type',       config.issues['type'],       filter_type)

		possible_owners = []
		if config.username != '':
			possible_owners = [config.username]
		possible_owners.extend(config.users)
		output_filter_options('Owner', 'filter_owner', possible_owners, filter_owner)
		self.output('</div>\n')

		if config.readonly:
			self.output('<input type="button" onclick="Sort_and_Filter()" value="Sort and Filter"/></form>')
		else:
			self.output('<input type="submit" value="Sort and Filter"/></form>')

		self.output('<div class="issue_list"><table class="issue_list" cellspacing="0" name="issue_list"> <tr class="issue_list"> ')
		
		page_args = {
				'show_repo'          : show_repo,
				'show_ID'            : show_ID,
				'show_type'          : show_type,
				'show_date'          : show_date,
				'show_severity'      : show_severity,
				'show_priority'      : show_priority,
				'show_component'     : show_component,
				'show_fix_by'        : show_fix_by,
				'show_seen_in_build' : show_seen_in_build,
				'show_state'         : show_state,
				'show_resolution'    : show_resolution,
				'show_owner'         : show_owner,
				'show_title'         : show_title,
				'filter_components'  : filter_components,
				'filter_fix_by'      : filter_fix_by,
				'filter_severity'    : filter_severity,
				'filter_priority'    : filter_priority,
				'filter_state'       : filter_state,
				'filter_resolution'  : filter_resolution,
				'filter_type'        : filter_type,
				'filter_owner'       : filter_owner,
				'sort_field'         : sort_field
			}

		def output_row_header(bool, label, request_args):
			if bool or config.readonly:
				if config.readonly:
					myargs = {}
				else:
					myargs = copy.copy(request_args)

				sort_token = '&nbsp;&nbsp;'

				if sort_field == label and not reverse_sort:
					myargs['sort_field'] = label
					myargs['reverse_sort'] = True
					sort_token = '^'
				elif sort_field == label and reverse_sort:
					myargs['sort_field'] = ''
					myargs['reverse_sort'] = False
					sort_token = 'v'
				elif sort_field != label:
					myargs['sort_field'] = label
					myargs['reverse_sort'] = False
				else:
					print 'Unknown sort_field/label/reverse combo %s/%s/%s' % (myargs['sort_field'], label, reverse_sort)

				arg_string = '?'
				for argname in myargs.keys():
					if type(myargs[argname]) == type([]):
						for argval in myargs[argname]:
							arg_string += '%s=%s&' % (urllib.quote(argname), urllib.quote_plus(argval))
					elif type(myargs[argname]) == type(True):
						if myargs[argname]:
							arg_string += '%s=1&' % (urllib.quote(argname))
						else:
							arg_string += '%s=0&' % (urllib.quote(argname))
					else:
						arg_string += '%s=%s&' % (urllib.quote(argname), urllib.quote_plus(myargs[argname]))
				arg_string = arg_string[:-1]

				self.output('<th class="issue_list"><a href="/%s">%s&nbsp;%s&nbsp;%s</a></th> ' % (arg_string, sort_token, label, sort_token))

		if db.has_foreign():
			output_row_header(show_repo,  'Project', page_args)
		output_row_header(show_ID,            'ID', page_args)
		output_row_header(show_type,          'Type', page_args)
		output_row_header(show_date,          'Date', page_args)
		output_row_header(show_severity,      'Severity', page_args)
		output_row_header(show_priority,      'Priority', page_args)
		output_row_header(show_component,     'Component', page_args)
		output_row_header(show_fix_by,        'Fix_By', page_args)
		output_row_header(show_seen_in_build, 'Seen_In_Build', page_args)
		output_row_header(show_state,         'State', page_args)
		output_row_header(show_resolution,    'Resolution', page_args)
		output_row_header(show_owner,         'Owner', page_args)
		output_row_header(show_title,         'Title', page_args)


		def skip_filter(issue, key, accept_list):
			if accept_list != [] and db.issue(issue)[key] not in accept_list:
				return True
			else:
				return False

		def output_field(issue, bool, field_data):
			if bool or config.readonly:
				self.output('<td class="issue_list"><a href="/issue/%s">%s</a></td> ' % (issue, cgi.escape(field_data)))


		def sort_issues(issue):
			issue_obj = db.issue(issue)

			if sort_field == 'Component':
				if issue_obj['Component'] not in config.issues['components']:
					return 0
				return config.issues['components'].index(issue_obj['Component'])

			if sort_field == 'Fix_By':
				if issue_obj['Fix_By'] not in config.issues['fix_by']:
					return 0
				return config.issues['fix_by'].index(issue_obj['Fix_By'])

			if sort_field == 'Severity':
				if issue_obj['Severity'] not in config.issues['severity']:
					return 0
				return config.issues['severity'].index(issue_obj['Severity'])

			if sort_field == 'Priority':
				if issue_obj['Priority'] not in config.issues['priority']:
					return 0
				return config.issues['priority'].index(issue_obj['Priority'])

			if sort_field == 'State':
				if issue_obj['State'] not in config.issues['state']:
					return 0
				return config.issues['state'].index(issue_obj['State'])

			if sort_field == 'Resolution':
				if issue_obj['Resolution'] not in config.issues['resolution']:
					return 0
				return config.issues['resolution'].index(issue_obj['Resolution'])

			if sort_field == 'Type':
				if issue_obj['Type'] not in config.issues['type']:
					return 0
				return config.issues['type'].index(issue_obj['Type'])

			if sort_field == 'Date':
                                return time.mktime(time.strptime(issue_obj['Date'], DATEFORMAT))

			if sort_field == 'Owner':
				return issue_obj['Owner']

			if sort_field == 'Seen_In_Build':
				return issue_obj['Seen_In_Build']

			if sort_field == 'Title':
				return issue_obj['Title']

			if sort_field == 'Project':
				return db.repos().index(issue_obj['repo'])

			if sort_field == 'ID':
				return issue

			print 'Unhandled sort_field "%s"' % sort_field
			return issue


		self.output('</tr>\n')
		issues = db.issues()

                # Perform a presort so the output will always be stable
                issues.sort()

		if sort_field != '':
			issues.sort(key = sort_issues)
		if reverse_sort:
			issues.reverse()

		row_colour = 1
		for issue in issues:
			if issue == 'format':
				continue

			if not config.readonly:
				if db.has_foreign() and skip_filter(issue, 'repo', filter_repo):
					continue
				if skip_filter(issue, 'Component',  filter_components):
					continue
				if skip_filter(issue, 'Fix_By',     filter_fix_by):
					continue
				if skip_filter(issue, 'Severity',   filter_severity):
					continue
				if skip_filter(issue, 'Priority',   filter_priority):
					continue
				if skip_filter(issue, 'State',      filter_state):
					continue
				if skip_filter(issue, 'Resolution', filter_resolution):
					continue
				if skip_filter(issue, 'Type',       filter_type):
					continue
				if skip_filter(issue, 'Owner',      filter_owner):
					continue

			self.output('<tr class="issue_list_tr%d">' % row_colour)
			row_colour = (row_colour + 1) % 2

			if db.has_foreign():
				output_field(issue, show_repo, db.issue(issue)['repo'])
			output_field(issue, show_ID,            issue[:8])
			output_field(issue, show_type,          db.issue(issue)['Type'])
			output_field(issue, show_date,          db.issue(issue)['Date'])
			output_field(issue, show_severity,      db.issue(issue)['Severity'])
			output_field(issue, show_priority,      db.issue(issue)['Priority'])
			output_field(issue, show_component,     db.issue(issue)['Component'])
			output_field(issue, show_fix_by,        db.issue(issue)['Fix_By'])
			output_field(issue, show_seen_in_build, db.issue(issue)['Seen_In_Build'])
			output_field(issue, show_state,         db.issue(issue)['State'])
			output_field(issue, show_resolution,    db.issue(issue)['Resolution'])
			output_field(issue, show_owner,         db.issue(issue)['Owner'])
			output_field(issue, show_title,         db.issue(issue)['Title'])

			self.output('</tr>\n')

		self.output('</table></div>')

		self.end_doc()

	def issue(self):
		issue_hash = self.path[7:]
		
		db.load_issue_db()

		issue = parse_file(db.issue(issue_hash)['path'] + '/issue')

		self.start_doc('%s [%s]' % (issue['Title'], issue_hash[:8]))

		if config.readonly:
			self.output('<p><a href="/?usejs=1">Back to issue list</a> ')
		else:
			self.output('<p><a href="/">Back to issue list</a> ')
		self.output('<a href="/export/%s.bug">Export</a></p>\n' % issue_hash)

		self.output('<form action="/update_issue" method="post">\n')
		self.output('<input type="hidden" name="issue" value="%s"/>\n' % issue_hash)

		self.output('<div class="issue_metadata">\n')
		if db.has_foreign():
			self.output('<p>Project: %s</p>\n' % db.issue(issue_hash)['repo'])
		self.output('<p>Issue: %s</p>\n' % issue_hash)
		self.output('<p>Title: %s</p>\n' % cgi.escape(issue['Title']))
		self.output('<p>Date: %s</p>\n' % issue['Date'])
		self.output('<p>Reported_By: %s</p>\n' % cgi.escape(issue['Reported_By']))
		self.output('<p>Seen_In_Build: %s</p>\n' % cgi.escape(issue['Seen_In_Build']))

		def output_metadata(label, arg_name, option_list, selected):
			self.output('<p>%s: <select name="%s">\n' % (label, arg_name))
			for item in option_list:
				self.output('<option ')
				if item == selected:
					self.output('selected="selected" ')
				self.output('value="%s">%s</option>\n' % (item, item))
			self.output('</select></p>\n')

		output_metadata('Severity', 'severity', config.issues['severity'], issue['Severity'])
		output_metadata('Priority', 'priority', config.issues['priority'], issue['Priority'])
		output_metadata('State', 'state', config.issues['state'], issue['State'])
		output_metadata('Resolution', 'resolution', config.issues['resolution'], issue['Resolution'])
		output_metadata('Type', 'type', config.issues['type'], issue['Type'])
		output_metadata('Owner', 'owner', config.users, issue['Owner'])
		output_metadata('Fix_By', 'fix_by', config.issues['fix_by'], issue['Fix_By'])
		output_metadata('Component', 'component', config.issues['components'], issue['Component'])

		def shorten_and_link_issues(issue_list_string):
			issue_list = issue_list_string.split(' ')
			output = ''
			for issue in issue_list:
				output += '%s ' % (self.format_issue(issue))

			return output

		self.output('<p>Depends_On: %s</p>\n' % shorten_and_link_issues(issue['Depends_On']))
		self.output('<p>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<textarea rows="1" cols="70" name="depends_on">%s</textarea></p>\n' % issue['Depends_On'])

		dependents = db.issue_dependent_of(issue_hash)
		self.output('<p>Dependent_Of: %s</p>\n' % shorten_and_link_issues(dependents))

		duplicate_issues = db.get_issue_duplicates(issue_hash)

		self.output('<p>Duplicate_Of: %s</p>\n' % shorten_and_link_issues(duplicate_issues))
		self.output('<p>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<textarea rows="1" cols="70" name="duplicate_of">%s</textarea></p>\n' % issue['Duplicate_Of'])

		hide = ''
		if not config.use_schedule:
			hide = 'hidden="yes"'

		if config.use_schedule:
			self.output('<p>Units_of_Work: ')
		self.output('<input type="number" name="units_of_work" value="%s" min="0" %s/></p>\n' % (issue['Units_of_Work'], hide))

		if config.use_schedule:
			self.output('<p>Percent_Complete: ')
		self.output('<input type="number" name="percent_complete" value="%s" min="0" max="100" %s/></p>\n' % (issue['Percent_Complete'], hide))

		self.output('</div>\n')

		if not config.readonly:
			self.output('<input type="submit" value="Update" />\n')

		self.output('</form>\n')

		self.output('<div class="issue_comment">\n')
		self.output('<div class="issue_comment_content">\n')

		def link_issue(match):
			return self.format_issue(match.group(0))

		linked_content = cgi.escape(issue['content'])
		linked_content = re.sub(URL_REGEX, '<a href="\\1">\\1</a>', linked_content)
		linked_content = re.sub(ISSUE_REGEX, link_issue, linked_content)
		self.output('<p>%s</p>\n' % linked_content)

		self.output('<form action="/add_comment" method="get">\n')
		self.output('<input type="hidden" name="issue" value="%s"/>\n' % issue_hash)
		if not config.readonly:
			self.output('<input type="submit" value="Add Comment" /><br/>')
		self.output('</form>\n')
		self.output('</div>\n') # End the content

		self.output('<div class="issue_comments">\n')
		self.output('<div class="issue_comment_children">\n')

		comment_stack = db.produce_comment_tree(issue_hash)
		comment_stack.reverse()
		comment_depth = [1] * len(comment_stack)
		parent_children_stack = [2] * len(comment_stack)
		depth = 0

		while len(comment_stack) > 0:
			comment = comment_stack.pop()
			old_depth = depth
			depth = comment_depth.pop()
			parent_children = parent_children_stack.pop()

			if old_depth - depth >= 0:
				self.output('</div></div>\n' * (old_depth - depth + 1))

			self.output('<div class="issue_comment">\n')
			self.output('<div class="issue_comment_content">\n')
			for field in ['hash', 'Date', 'User', 'Attachment']:
				if field in ['content', 'children', 'Parent', 'Attachment-filename', 'Attachment-type']:
					continue
				if field == 'Attachment':
					if comment['Attachment'] != '': # Has a real attachment
						self.output('%s: <a href="/attachment/%s/%s/%s/%s">%s</a><br/>\n' %
								(field, issue_hash, comment['hash'], comment['Attachment'],comment['Attachment-filename'], comment['Attachment-filename']))
					continue

				self.output('%s: %s<br/>\n' % (field, cgi.escape(comment[field])))

			linked_content = cgi.escape(comment['content'])
			linked_content = re.sub(URL_REGEX, '<a href="\\1">\\1</a>', linked_content)
			linked_content = re.sub(ISSUE_REGEX, link_issue, linked_content)
			self.output('<p>%s</p>\n' % linked_content)

			self.output('<form action="/add_comment" method="get">\n')
			self.output('<input type="hidden" name="issue" value="%s"/>\n' % issue_hash)
			self.output('<input type="hidden" name="comment" value="%s"/>\n' % comment['hash'])
			if not config.readonly:
				self.output('<input type="submit" value="Reply" /><br/>')
			self.output('</form>\n')
			self.output('</div>\n') # end content
			self.output('<div class="issue_comment_children">\n')

			comment['children'].reverse()
			comment_stack.extend(comment['children'])
			if parent_children == 1 and len(comment['children']) == 1:
				comment_depth.extend([depth] * len(comment['children']))
			else:
				comment_depth.extend([depth + 1] * len(comment['children']))
			parent_children_stack.extend([len(comment['children'])] * len(comment['children']))
		self.output('</div></div>\n' * depth)

		self.output('</div></div>\n') # End the issue description children div and comment div
		self.output('</div>\n') # End the issue_comments

		self.end_doc()

	def add_comment(self):
		self.start_doc('Add Comment', 'comment.content')

		if not 'issue' in self.request_args.keys():
			self.output('Incorrect script arguments')
			self.end_doc()
			return
		else:
			issue = self.request_args['issue']

		self.output('<p><a href="/issue/%s">Back to issue %s</a></p>\n' % (issue, issue[:8]))

		if not 'comment' in self.request_args.keys():
			comment = None
		else:
			comment = self.request_args['comment']

		db.load_issue_db()

		comment_parent = db.find_comment_parent(issue, comment)

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
		self.output('<div class="add_comment">\n')
		self.output('<form name="comment" enctype="multipart/form-data" action="/add_comment" method="post">\n')
		self.output('<input type="hidden" name="issue" value="%s"/>\n' % issue)
		self.output('<input type="hidden" name="parent" value="%s"/>\n' % parent)

		date = time.strftime(DATEFORMAT, time.gmtime())
		self.output('<p>Date: %s<input type="hidden" name="date" value="%s"/></p>\n' % (date, date))

		self.output('<p>User: <select name="username">\n')
		for username in config.users:
			self.output('<option ')
			if username == config.username:
				self.output('selected="selected" ')
			self.output('value="%s">%s</option>\n' % (username, username))
		self.output('</select></p>\n')

		self.output('<p>Attachment: <input type="file" name="attachment"/> ')
		self.output('<input type="text" name="attachment_name" value="%s" size="40"/></p>\n' % USE_UPLOADED_NAME)

		self.output('<p><textarea name="content" rows="20" cols="80">Enter comment here</textarea></p>\n')

		self.output('<input type="submit" value="Submit"/><br/>\n')
		self.output('</form>\n')
		self.output('</div>\n')

		self.end_doc()

	def new_issue(self):
		self.start_doc('New Issue')

		self.output('<p><a href="/">Back to issue list</a></p>\n')

		self.output('<div class="new_issue">\n')
		self.output('<form action="/new_issue" method="post">\n')

		self.output('<div class="new_issue_metadata_column">\n')
		date = time.strftime(DATEFORMAT, time.gmtime())
		self.output('<p>Date: %s<input type="hidden" name="date" value="%s"/></p>\n' % (date, date))

		if db.has_foreign():
			self.output('<p>Project: <select name="repo">\n')
			for repo in db.repos():
				self.output('<option ')
				if repo == 'Local':
					self.output('selected="selected" ')
				self.output('value="%s">%s</option>\n' % (repo, repo))
			self.output('</select></p>\n')

		self.output('<p>Title: <input type="text" name="title" value="Issue Title"/></p>\n')

		self.output('<p>Type: <select name="type">\n')
		for type in config.issues['type']:
			self.output('<option value="%s">%s</option>\n' % (type, type))
		self.output('</select></p>\n')

		self.output('<p>Component: <select name="component">\n')
		for component in config.issues['components']:
			self.output('<option value="%s">%s</option>\n' % (component, component))
		self.output('</select></p>\n')

		self.output('<p>Severity: <select name="severity">\n')
		for severity in config.issues['severity']:
			self.output('<option value="%s">%s</option>\n' % (severity, severity))
		self.output('</select></p>\n')

		self.output('<p>Priority: <select name="priority">\n')
		for priority in config.issues['priority']:
			self.output('<option value="%s">%s</option>\n' % (priority, priority))
		self.output('</select></p>\n')
		self.output('<p>State: <select name="state">\n')
		for state in config.issues['state']:
			self.output('<option value="%s">%s</option>\n' % (state, state))
		self.output('</select></p>\n')

		self.output('</div>\n')
		self.output('<div class="new_issue_metadata_column">\n')

		self.output('<p>Resolution: <select name="resolution">\n')
		for resolution in config.issues['resolution']:
			self.output('<option value="%s">%s</option>\n' % (resolution, resolution))
		self.output('</select></p>\n')

		self.output('<p>Reported_By: <select name="reported_by">\n')
		for user in config.users:
			self.output('<option ')
			if config.username == user:
				self.output('selected="selected" ')
			self.output('value="%s">%s</option>\n' % (user, user))
		self.output('</select></p>\n')
		
		self.output('<p>Owner: <select name="owner">\n')
		for user in config.users:
			self.output('<option ')
			if config.users[0] == user:
				self.output('selected="selected" ')
			self.output('value="%s">%s</option>\n' % (user, user))
		self.output('</select></p>\n')

		self.output('<p>Seen_In_Build: <input type="text" name="seen_in_build" value=""/></p>\n')

		self.output('<p>Fix_By: <select name="fix_by">\n')
		for fix_by in config.issues['fix_by']:
			self.output('<option value="%s">%s</option>\n' % (fix_by, fix_by))
		self.output('</select></p>\n')

		self.output('<p>Depends_On: <input type="text" name="depends_on" value=""/></p>\n')
		self.output('<p>Duplicate_Of: <input type="text" name="duplicate_of" value=""/></p>\n')

		hide = ''
		if not config.use_schedule:
			hide = 'hidden="yes"'

		if config.use_schedule:
			self.output('<p>Units_of_Work: ')
		self.output('<input type="number" name="units_of_work" value="1000" min="0" %s/></p>\n' % hide)

		if config.use_schedule:
			self.output('<p>Percent_Complete: ')
		self.output('<input type="number" name="percent_complete" value="0" min="0" max="100" %s/></p>\n' % hide)

		self.output('</div>\n')

		self.output('<div class="new_issue_text_wrapper"><p><textarea name="content" rows="20" cols="80">Enter description here</textarea></p>\n')

		self.output('<input type="submit" value="Submit"/></div><br/>\n')
		self.output('</form>\n')
		self.output('</div>\n')

		self.end_doc()

	def attachment(self):
		db.load_issue_db()

		args = self.path.split('/')
		issue_hash = args[2]
		comment_hash = args[3]
		file_hash = args[4]

		issue = db.disambiguate_hash(issue_hash)

		if issue == None or issue == '':
			self.start_doc('Error')
			self.output('Invalid arguments')
			self.end_doc()
			return

		attachment_path = db.issue(issue)['path'] + '/' + file_hash + '.data'
		if not os.path.exists(attachment_path):
			self.start_doc('Error')
			self.output('Invalid arguments')
			self.end_doc()
			return

		self.send_response(200)

		comment = db.get_comment(issue, comment_hash)
		if comment == None or 'Attachment-type' not in comment:
			self.send_header('Content-Type', 'application/octet-stream')
		else:
			self.send_header('Content-Type', comment['Attachment-type'])
		self.end_headers()

		attachment = open(attachment_path, 'r')
		self.wfile.write(attachment.read())
		attachment.close()

	def schedule(self):
		db.load_issue_db()

		schedule = schedule_all_tasks()
		self.start_doc('Project Schedule')

		self.output('<p><a href="/">Back to issue list</a></p>\n')

		self.output('<div class="schedule"><table cellspacing="0" rules="all">\n')

		# Alternate column colours
		colour = 1
		self.output('<colgroup><col class="schedule_col0"/></colgroup>')
		for user in schedule.keys():
			self.output('<colgroup><col class="schedule_col%d"/></colgroup>' % colour)
			colour = (colour + 1) % 2

		self.output('<tr><th>Date</th> ')

		# Output usernames
		for user in schedule.keys():
			self.output('<th class="schedule_user"><div class="schedule_user">%s</div></th> ' % ' '.join(user))
		self.output('</tr>\n')

		one_day = datetime.timedelta(days=1)

		# Find the date range we'll need
		dates_start = schedule.values()[0][0].sched_start_date
		dates_end = dates_start
		for peruser in schedule.values():
			for task in peruser:
				if task.sched_start_date < dates_start:
					dates_start = task.sched_start_date
				if task.sched_end_date > dates_end:
					dates_end = task.sched_end_date

		# Create a reverse index keyed on date for the milestones. This is so we can
		# highlight and label the milestones.
		milestones = {}
		for fix_by in config.fix_by_dates.keys():
			times = config.fix_by_dates[fix_by].split('-')
			if times != ['']:
				times = map(int, times)
				milestones[datetime.date(times[0], times[1], times[2])] = fix_by

		# We need to precompute the entire table in order to know how many rows any
		# particular task should span.

		# Number of columns a user needs to handle their overlapping tasks
		num_columns = {}
		# The precomputed rows, a list of dictionaries. Each dictionary has one entry per
		# user who has a task or gap which starts in that row.
		rows = {}

		for user in schedule.keys():
			needed_columns = 1
			last_issue_end = dates_start - one_day

			for task in schedule[user]:
				if task.sched_start_date > last_issue_end + one_day:
					# Add a gap
					row_num = (last_issue_end + one_day - dates_start).days

					if row_num not in rows:
						rows[row_num] = {}

					rows[row_num][user] = ('gap', 
							(task.sched_start_date - one_day - last_issue_end).days)
					last_issue_end = task.sched_end_date - one_day

				row_num = (task.sched_start_date - dates_start).days

				if row_num not in rows:
					rows[row_num] = {}

				rows[row_num][user] = (task, 
						(task.sched_end_date + one_day - task.sched_start_date).days)
				last_issue_end = task.sched_end_date

			if last_issue_end < dates_end:
				# One last gap to the end of the schedule
				row_num = (last_issue_end + one_day - dates_start).days

				if row_num not in rows:
					rows[row_num] = {}

				rows[row_num][user] = ('gap', 
						(dates_end - last_issue_end).days)

			num_columns[user] = needed_columns

		# The fix_by colours are assigned as they are used in an attempt to make the colour order consistent.
		last_fixby_num = {'key' : -1} # Make sure we start at the first one
		fixby_colour = {}

		# Returns a string which is the correct class to use to get the proper fix_by colour
		def choose_fixby_colour(fix_by):
			if fix_by not in fixby_colour:
				fixby_colour[fix_by] = (last_fixby_num['key'] + 1) % NUM_FIXBY_COLOURS
				last_fixby_num['key'] = (last_fixby_num['key'] + 1) % NUM_FIXBY_COLOURS
			colour = 'schedule_fixby%d' % fixby_colour[fix_by]
			return colour

		d = dates_start
		while d <= dates_end:
			if d in milestones:
				colour = choose_fixby_colour(milestones[d])
				self.output('<tr class="%s"><th>%s %s</th> ' % (colour, milestones[d], d))
			else:
				self.output('<tr class="schedule"><th>%s</th> ' % d)

			row_num = (d - dates_start).days

			# Since tasks can cover multiple rows, it's quite likely that some rows
			# won't have any tasks whick start in them.
			try:
				row = rows[row_num]

				for user in schedule.keys():
					if user in row:
						task, num_rows = row[user]

						if task == 'gap':
							task_text = ''
							colour = 'schedule_gap'
						else:
							task_text = self.format_issue(task.hash, True)
							colour = choose_fixby_colour(task.issue['Fix_By'])

						self.output('<td rowspan="%d" class="%s"><div class="schedule_td" style="max-height: %fem">%s</div></td> ' % 
								(num_rows, colour, num_rows * 1.1, task_text))
			except:
				pass


			self.output('</tr>\n')
			d += one_day

		self.output('</table></div>\n')

		self.end_doc()

	def robots(self):
		self.send_response(404)
		self.end_headers()

	def export(self):
		db.load_issue_db()

		args = self.path.split('/')
		issue = db.disambiguate_hash(args[-1].split('.')[-2])

		if issue == None or issue == '':
			self.start_doc('Error')
			self.output('Invalid arguments')
			self.end_doc()
			return

		self.send_response(200)
		self.send_header('Content-Type', 'application/json')
		self.end_headers()

		self.wfile.write(format_issue_for_export(issue))

	def js(self):
		self.send_response(200)
		self.send_header('Content-type', 'application/javascript')
		self.end_headers()

		self.output("""
		function get_field(fieldname) {
			return document.getElementsByName(fieldname)[0];
		}

		/*
		 * Return a list of strings of the options which are selected in the multiselect.
		 */
		function selected_options(select) {
			var selected = new Array();
			var i = 0;

			for (i = 0; i < select.length; i++) {
				if (select[i].selected) {
					selected.push(select[i].value);
				}
			}

			return selected;
		}

		var row_filter = new Array(
			"filter_repo",
			"filter_type",
			"filter_severity",
			"filter_priority",
			"filter_components",
			"filter_fix_by",
			"filter_state",
			"filter_resolution",
			"filter_owner"
			);

		var column_filter = new Array(
			"show_repo",
			"show_ID",
			"show_type",
			"show_date",
			"show_severity",
			"show_priority",
			"show_component",
			"show_fix_by",
			"show_seen_in_build",
			"show_state",
			"show_resolution",
			"show_owner",
			"show_title"
			);

		function load_filters() {
			var have_settings = false;

			/*
			 * Did we get any settings with the html? We don't check the row_filters here because every HTML
			 * files has default settings for these.
			 */
			for (var i = 0; i < column_filter.length; i++) {
				if (get_field(column_filter[i]).checked) {
					have_settings = true;
					break;
				}
			}

			if (!have_settings) {
				/* We didn't get any settings, so load them from the session store */
				for (var i = 0; i < row_filter.length; i++) {
					var options = sessionStorage.getItem(row_filter[i]);
					if (options == undefined)
						continue; /* No values to set */
					else
						options = options.split("\\n");

					var field = get_field(row_filter[i]);
					var select_options = field.options;

					for (var j = 0; j < select_options.length; j++)
						select_options[j].selected = false;

					for (var option = 0; option < options.length; option++) {
						var option_text = options[option];

						for (var j = 0; j < select_options.length; j++) {
							if (select_options[j].text == option_text)
								select_options[j].selected = true;
						}
					}
				}

				for (var i = 0; i < column_filter.length; i++) {
					var option = sessionStorage.getItem(column_filter[i]);
					if (option == undefined)
						continue; /* No values to set */

					if (option == "false")
						option = false;
					else
						option = true;

					var field = get_field(column_filter[i]);
					field.checked = option;
				}
			}

		}

		function save_filters() {
			for (var i = 0; i < row_filter.length; i++) {
				sessionStorage.setItem(row_filter[i], selected_options(get_field(row_filter[i])).join("\\n"));
			}
			
			for (var i = 0; i < column_filter.length; i++) {
				sessionStorage.setItem(column_filter[i], get_field(column_filter[i]).checked);
			}
		}

		function Sort_and_Filter() {
			load_filters();
			save_filters();

			var rows = document.getElementsByName("issue_list")[0].rows;

			var row_filter = new Array(
				selected_options(get_field("filter_repo")),
				0, /* ID */
				selected_options(get_field("filter_type")),
				0, /* Date */
				selected_options(get_field("filter_severity")),
				selected_options(get_field("filter_priority")),
				selected_options(get_field("filter_components")),
				selected_options(get_field("filter_fix_by")),
				0, /* Seen_In_Build */
				selected_options(get_field("filter_state")),
				selected_options(get_field("filter_resolution")),
				selected_options(get_field("filter_owner")),
				0 /* Title */
				);

			var column_filter = new Array(
				"show_repo",
				"show_ID",
				"show_type",
				"show_date",
				"show_severity",
				"show_priority",
				"show_component",
				"show_fix_by",
				"show_seen_in_build",
				"show_state",
				"show_resolution",
				"show_owner",
				"show_title"
				);

			/* Skip the data rows based upon filtering */
			for (var i = 1; i < rows.length; i++) {
				var row = rows[i];
				var hide = false;

				for (var column = 0; column < row_filter.length; column++) {
					if (typeof(row_filter[column]) == "number")
						continue; /* We don't filter on this column */

					var val = row.cells[column];
					var content = val.textContent;
					if (row_filter[column].indexOf(content) == -1) {
						hide = true;
						break; /* We've hidden so we are done */
					}
				}

				if (hide)
					row.style.display = 'none';
				else
					row.style.display = '';

			}

			/* Hide columns based upon settings */
			for (var column = 0; column < column_filter.length; column++) {
				var show = get_field(column_filter[column]).checked;

				for (var i = 0; i < rows.length; i++) {
					var row = rows[i];

					if (show)
						row.cells[column].style.display = '';
					else
						row.cells[column].style.display = 'none';
				}
			}

			/* Fixup the row colouring */
			var colour = 0;
			for (var i = 0; i < rows.length; i++) {
				var row = rows[i];
				if (row.style.display != 'none') {
					row.className = "issue_list_tr" + colour;
					colour = (colour + 1) % 2;
				}
			}
		}

		Sort_and_Filter();
		""")

	def add_comment_post(self):
		db.load_issue_db()

		if 'date' not in self.request_args.keys() or \
		   'parent' not in self.request_args.keys() or \
		   'username' not in self.request_args.keys() or \
		   'content' not in self.request_args.keys() or \
		   'attachment' not in self.request_args.keys() or \
		   'attachment_name' not in self.request_args.keys() or \
		   'issue' not in self.request_args.keys():
			   self.start_doc('Error')
			   self.output('Invalid arguments')
			   self.end_doc()
			   return

		if self.request_args['attachment_name'] == '' and len(self.request_args['attachment']) > 0:
			self.start_doc('Attachment Requires filename')
			self.output('The attachment requires a filename')
			self.end_doc()
			return

		comment = {
				'Date' : self.request_args['date'],
				'Parent' : self.request_args['parent'],
				'User' : self.request_args['username'],
				'Attachment' : '',
				'Attachment-filename' : '',
				'Attachment-type' : 'application/octet-stream',
				'content' : self.request_args['content']
			}

		if 'attachment_type' in self.request_args.keys():
			comment['Attachment-type'] = self.request_args['attachment_type']

		attachment_hash = db.add_attachment(self.request_args['issue'],
						    self.request_args['attachment'])
		if attachment_hash != None:
			comment['Attachment'] = attachment_hash
			comment['Attachment-filename'] = self.request_args['attachment_name']

		if comment['Attachment-filename'] == USE_UPLOADED_NAME and \
				'upload_filename' in self.request_args.keys():
			comment['Attachment-filename'] = self.request_args['upload_filename']

		comment['Attachment-filename'] = comment['Attachment-filename'].replace('/', '_')
		comment['Attachment-filename'] = comment['Attachment-filename'].replace('\\', '_')

		comment_filename = db.add_comment(self.request_args['issue'], comment)

		self.start_doc('Comment %s added' % comment_filename)
		self.output('<p>Successfully added the comment</p>\n')
		self.output('<a href="/">Back to issue list</a> ')
		self.output('<a href="/issue/%s"> Back to issue %s</a>\n' % (self.request_args['issue'], self.request_args['issue'][:8]))
		self.end_doc()

		config.uncommitted_changes = True

	def update_issue_post(self):
		db.load_issue_db()

		if 'issue' not in self.request_args.keys() or \
		   'severity' not in self.request_args.keys() or \
		   'component' not in self.request_args.keys() or \
		   'owner' not in self.request_args.keys() or \
		   'priority' not in self.request_args.keys() or \
		   'state' not in self.request_args.keys() or \
		   'type' not in self.request_args.keys() or \
		   'resolution' not in self.request_args.keys() or \
		   'depends_on' not in self.request_args.keys() or \
		   'duplicate_of' not in self.request_args.keys() or \
		   'units_of_work' not in self.request_args.keys() or \
		   'percent_complete' not in self.request_args.keys() or \
		   'fix_by' not in self.request_args.keys():
			   self.start_doc('Error')
			   self.output('Invalid arguments')
			   self.end_doc()
			   return

		issue = db.disambiguate_hash(self.request_args['issue'])

		if db.issue(issue)['Severity'] == self.request_args['severity'] and \
			db.issue(issue)['Priority'] == self.request_args['priority'] and \
			db.issue(issue)['Owner'] == self.request_args['owner'] and \
			db.issue(issue)['State'] == self.request_args['state'] and \
			db.issue(issue)['Type'] == self.request_args['type'] and \
			db.issue(issue)['Component'] == self.request_args['component'] and \
			db.issue(issue)['Resolution'] == self.request_args['resolution'] and \
			db.issue(issue)['Depends_On'] == self.request_args['depends_on'] and \
			db.issue(issue)['Duplicate_Of'] == self.request_args['duplicate_of'] and \
			db.issue(issue)['Units_of_Work'] == self.request_args['units_of_work'] and \
			db.issue(issue)['Percent_Complete'] == self.request_args['percent_complete'] and \
			db.issue(issue)['Fix_By'] == self.request_args['fix_by']:
				self.start_doc('No change')
				self.output('<p>No change sent, no change made</p>')
				self.output('<a href="/issue/%s">Back to issue %s</a>\n' % (issue, issue[:8]))
				self.end_doc()
				return

		if db.issue(issue)['Severity'] != self.request_args['severity']:
			db.change_issue(issue, 'Severity', self.request_args['severity'])
		if db.issue(issue)['Priority'] != self.request_args['priority']:
			db.change_issue(issue, 'Priority', self.request_args['priority'])
		if db.issue(issue)['Owner'] != self.request_args['owner']:
			db.change_issue(issue, 'Owner', self.request_args['owner'])
		if db.issue(issue)['State'] != self.request_args['state']:
			db.change_issue(issue, 'State', self.request_args['state'])
		if db.issue(issue)['Type'] != self.request_args['type']:
			db.change_issue(issue, 'Type', self.request_args['type'])
		if db.issue(issue)['Component'] != self.request_args['component']:
			db.change_issue(issue, 'Component', self.request_args['component'])
		if db.issue(issue)['Resolution'] != self.request_args['resolution']:
			db.change_issue(issue, 'Resolution', self.request_args['resolution'])
		if db.issue(issue)['Fix_By'] != self.request_args['fix_by']:
			db.change_issue(issue, 'Fix_By', self.request_args['fix_by'])
		if db.issue(issue)['Units_of_Work'] != self.request_args['units_of_work']:
			if float(self.request_args['units_of_work']) < 0:
				self.start_doc('Invalid value')
				self.output('<p>Invalid value for Units_of_Work %s. Must be greater or equal to zero</p>' % self.request_args['units_of_work'])
				self.output('<a href="/issue/%s">Back to issue %s</a>\n' % (issue, issue[:8]))
				self.end_doc()
				return
			db.change_issue(issue, 'Units_of_Work', self.request_args['units_of_work'])
		if db.issue(issue)['Percent_Complete'] != self.request_args['percent_complete']:
			if float(self.request_args['percent_complete']) < 0 or float(self.request_args['percent_complete']) > 100:
				self.start_doc('Invalid value')
				self.output('<p>Invalid value for Percent_Complete %s. Must be between 0 and 100</p>' % self.request_args['percent_complete'])
				self.output('<a href="/issue/%s">Back to issue %s</a>\n' % (issue, issue[:8]))
				self.end_doc()
				return
			db.change_issue(issue, 'Percent_Complete', self.request_args['percent_complete'])

		# Returns a string of issues if valid, or None if invalid
		def check_issue_list_string(issues):
			issue_list = issues.split()

			output = ''
			for issue in issue_list:
				if issue in db.issues():
					output += '%s ' % issue
				else:
					disambiguated = db.disambiguate_hash(issue)
					if disambiguated is None or disambiguated == '':
						return None
					else:
						output += '%s ' % disambiguated
			return output

		if db.issue(issue)['Depends_On'] != self.request_args['depends_on']:
			issues = check_issue_list_string(self.request_args['depends_on'])
			if issues == None:
				self.start_doc('Invalid Issues to be dependend on')
				self.output('Error in Depends_On list. Perhaps you have something other than unambiguous issue hashes?')
				self.end_doc()
				return
			else:
				db.change_issue(issue, 'Depends_On', issues)

		if db.issue(issue)['Duplicate_Of'] != self.request_args['duplicate_of']:
			issues = check_issue_list_string(self.request_args['duplicate_of'])
			if issues == None:
				self.start_doc('Invalid Issues to be duplicate of')
				self.output('Error in Duplicate_Of list. Perhaps you have something other than unambiguous issue hashes?')
				self.end_doc()
				return
			else:
				db.change_issue(issue, 'Duplicate_Of', issues)

		issue_filename = db.issue(issue)['path'] + '/issue'

		self.start_doc('Issues %s updated' % issue[:8])
		self.output('<p>Successfully updated issue %s</p>\n' % issue[:8])
		self.output('<a href="/">Back to issue list</a> ')
		self.output('<a href="/issue/%s">Back to issue %s</a><br/>\n' % (issue, issue[:8]))
		self.end_doc()

		config.uncommitted_changes = True

	def new_issue_post(self):
		if 'date' not in self.request_args.keys() or \
		   'title' not in self.request_args.keys() or \
		   'severity' not in self.request_args.keys() or \
		   'priority' not in self.request_args.keys() or \
		   'type' not in self.request_args.keys() or \
		   'resolution' not in self.request_args.keys() or \
		   'component' not in self.request_args.keys() or \
		   'fix_by' not in self.request_args.keys() or \
		   'seen_in_build' not in self.request_args.keys() or \
		   'owner' not in self.request_args.keys() or \
		   'reported_by' not in self.request_args.keys() or \
		   'depends_on' not in self.request_args.keys() or \
		   'duplicate_of' not in self.request_args.keys() or \
		   'units_of_work' not in self.request_args.keys() or \
		   'percent_complete' not in self.request_args.keys() or \
		   (db.has_foreign() and ('repo' not in self.request_args.keys() or \
		   	self.request_args['repo'] not in db.repos())) or \
		   'content' not in self.request_args.keys():
			   self.start_doc('Error')
			   self.output('Invalid arguments')
			   self.end_doc()
			   return

		if float(self.request_args['units_of_work']) < 0:
			self.start_doc('Invalid value')
			self.output('<p>Invalid value for Units_of_Work %s. Must be greater or equal to zero</p>' % self.request_args['units_of_work'])
			self.end_doc()
			return

		if float(self.request_args['percent_complete']) < 0 or float(self.request_args['percent_complete']) > 100:
			self.start_doc('Invalid value')
			self.output('<p>Invalid value for Percent_Complete %s. Must be between 0 and 100</p>' % self.request_args['percent_complete'])
			self.end_doc()
			return

		issue = {
				'Title' : self.request_args['title'],
				'Severity' : self.request_args['severity'],
				'Priority' : self.request_args['priority'],
				'State' : self.request_args['state'],
				'Type' : self.request_args['type'],
				'Resolution' : self.request_args['resolution'],
				'Component' : self.request_args['component'],
				'Fix_By' : self.request_args['fix_by'],
				'Seen_In_Build' : self.request_args['seen_in_build'],
				'Date' : self.request_args['date'],
				'Owner' : self.request_args['owner'],
				'Reported_By' : self.request_args['reported_by'],
				'Depends_On' : self.request_args['depends_on'],
				'Duplicate_Of' : self.request_args['duplicate_of'],
				'Units_of_Work' : self.request_args['units_of_work'],
				'Percent_Complete' : self.request_args['percent_complete'],
				'content' : self.request_args['content']
			}

		if 'repo' in self.request_args.keys():
			repo = self.request_args['repo']
		else:
			repo = 'Local'
		issue_filename, issue_hash = db.add_issue(issue, repo)

		self.start_doc('Created Issue %s' % issue_filename)
		self.output('<p>Successfully create the issue</p>\n')
		self.output('<a href="/">Back to issue list</a> ')
		self.output('<a href="/issue/%s"> Back to issue %s</a>\n' % (issue_hash, issue_hash[:8]))
		self.end_doc()

		config.uncommitted_changes = True

	def shutdown_post(self):
		self.start_doc('Shutting Down')
		self.output('<p>Nitpick web interface has exited</p>')
		self.end_doc()

		config.endweb = True

	def commit_post(self):
		config.vcs.commit()
		config.uncommitted_changes = False

		self.start_doc('Committed Changes')
		self.output('<p>All changes to the Nitpick database have been committed</p>\n')
		self.output('<a href="/">Go back to issue index</a>\n');
		self.end_doc()

	def revert_post(self):
		config.vcs.revert()
		config.uncommitted_changes = False

		self.start_doc('Reverted Changes')
		self.output('<p>All changes to the Nitpick database have been reverted</p>\n')
		self.output('<a href="/">Go back to issue index</a>\n');
		self.end_doc()

	def do_GET(self):
		#print 'got get  path %s' % self.path

		self.request_args = {}
		args_start = self.path.find('?')
		if args_start != -1:
			# The path has arguments
			args = self.path[args_start + 1:]

			for var in args.split('&'):
				key_value = var.split('=')
				key = urllib.unquote(key_value[0])
				value = urllib.unquote_plus(key_value[1])

				if key in self.request_args.keys():
					if type(self.request_args[key]) != type([]):
						self.request_args[key] = [self.request_args[key], value]
					else:
						self.request_args[key].append(value)
				else:
					self.request_args[key] = value

		if '/' == self.path:
			self.root()
		elif '/robots.txt' == self.path:
			self.robots()
		elif '/issue/' in self.path:
			self.issue()
		elif '/add_comment' in self.path:
			self.add_comment()
		elif self.path == '/new_issue':
			self.new_issue()
		elif '/?' in self.path:
			self.root()
		elif '/attachment/' in self.path:
			self.attachment()
		elif '/favicon.ico' == self.path:
			self.favicon()
		elif '/export/' in self.path:
			self.export()
		elif '/schedule' == self.path:
			self.schedule()
		elif '/js.js' == self.path:
			self.js()
		elif '/css.css' == self.path:
			self.css()
		else:
			print "Got unhandled get path %s" % self.path
			self.root()

	def do_POST(self):
		#print 'got post path %s' % self.path

		self.request_args = {}

		if self.path != '/add_comment':
			args = self.rfile.read(int(self.headers['Content-Length']))
			if len(args) > 0:
				for var in args.split('&'):
					key_value = var.split('=')
					key = urllib.unquote(key_value[0])
					value = urllib.unquote_plus(key_value[1])

					self.request_args[key] = value
		else:
			# /add_comment receives form data as multi-part/form because it may have an attachment
			env = { 'REQUEST_METHOD' : 'POST' }
			args = cgi.FieldStorage(self.rfile, headers=self.headers, environ=env)

			for name in args.keys():
				self.request_args[name] = args[name].value

				if name == 'attachment':
					self.request_args['attachment_type'] = args[name].type
					self.request_args['upload_filename'] = args[name].filename

		if '/add_comment' == self.path:
			self.add_comment_post()
		elif '/update_issue' == self.path:
			self.update_issue_post()
		elif '/new_issue' == self.path:
			self.new_issue_post()
		elif '/shutdown' == self.path:
			self.shutdown_post()
		elif '/commit' == self.path:
			self.commit_post()
		elif '/revert' == self.path:
			self.revert_post()
		else:
			print 'Got unhandled post path %s' % self.path
			self.root()


# Root class of the VCS compatibility layer
class VCS:
	"""
	Simple VCS which uses basic unix filesystem commands
	"""

	name = 'file'
	real = False
	
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
	def commit():
		"""
		Ensure that all the registered changes are committed to the VCS repository.
		"""
		return

	@staticmethod
	def revert():
		"""
		Revert all uncommitted changes in the Nitpick database.

		Any newly created files should be deleted.
		"""
		return

	@staticmethod
	def ignore(path):
		"""
		Ensure that the given path will be ignored and not show up in any VCS show command as unknown"
		"""
		return

class SVN(VCS):
	name = 'svn'
	real = True

	@staticmethod
	def mkdir(path):
		os.system("svn mkdir -q --parents " + path)

	@staticmethod
	def add_changes(path):
		os.system("svn add -q " + path);

	@staticmethod
	def commit():
		os.system("svn ci -q -m \"Nitpick commit\" " + config.db_path)
		if db.has_foreign():
			os.system("for external in `svn stat %s | grep ^X | awk '{print $2}'`; do svn ci -q -m \"Nitpick commit\" $external;done" % config.db_path)

	@staticmethod
	def revert():
		os.system("svn revert -q -R " + config.db_path)
		if db.has_foreign():
			os.system("for external in `svn stat %s | grep ^X | awk '{print $2}'`; do svn revert -q -R $external;done" % config.db_path)
		os.system("svn stat " + config.db_path + " | grep ^?| xargs rm -rf")

	@staticmethod
	def ignore(path):
		dir = os.path.dirname(path)
		os.system('''svn propset -q svn:ignore "issue_cache\n\
		`svn propget svn:ignore %s`" %s''' % (dir, dir))

class GIT(VCS):
	name = 'git'
	real = True
	uncommitted_files=""

	@staticmethod
	def mkdir(path):
		os.system("mkdir -p " + path)

	@staticmethod
	def add_changes(path):
		GIT.uncommitted_files += " " + path
		return

	@staticmethod
	def commit():
		os.system("git add " + GIT.uncommitted_files)
		os.system("git commit -q -m \"Nitpick commit\" -- " + config.db_path + GIT.uncommitted_files)
		GIT.uncommitted_files = ""

	@staticmethod
	def revert():
		os.system("git checkout -- " + config.db_path)
		os.system("git status -s " + config.db_path + " | grep ^??| awk '{print $2}' | xargs rm -rf")
		GIT.uncommitted_files = ""

	@staticmethod
	def ignore(path):
		os.system('echo "issue_cache" >> %s/.gitignore' % (config.db_path))
		GIT.uncommitted_files += " %s/.gitignore" % config.db_path

class HG(VCS):
	name = 'hg'
	real = True

	@staticmethod
	def mkdir(path):
		os.system("mkdir -p " + path)

	@staticmethod
	def add_changes(path):
		os.system("hg add -q " + path);

	@staticmethod
	def commit():
		os.system("hg ci -q -m \"Nitpick commit\" " + config.db_path)

	@staticmethod
	def revert():
		os.system("hg revert -q " + config.db_path)
		os.system("hg stat " + config.db_path + " | grep ^?| xargs rm -rf")
		
		# Remove the empty directories. This is mostly to avoid problems with empty issue directories
		# but also keeps the number of cruft empty directories to a minimum
		os.system('find %s -type d -empty | xargs rm -rf' % config.db_path)

	@staticmethod
	def ignore(path):
		# Find the root of the clone because that's where the .hgignore must be
		root = ""
		while not os.path.exists(root + ".hg"):
			root = root + "../"
		os.system('echo ".nitpick/issue_cache$" >> %s.hgignore' % (root))

BACKENDS = { 'file': VCS, 'svn' : SVN, 'git' : GIT, 'hg' : HG}

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
        keylist = data.keys()
        keylist.sort()
	for key in keylist:
		if key != 'content':
			file.write("%s: %s\n" % (key, data[key]))
	file.write('--\n')
	if 'content' in data:
		file.write("%s" % data['content'])
	file.close()

def _load_config(repo_path):
	config.fix_by_dates = {}

	conf = parse_file(repo_path + 'config/config')
	for key in ['components', 'fix_by', 'priority', 'severity', 'state', 'resolution', 'type']:
		if config.issues[key] == []:
			first_run = True
		else:
			first_run = False
		
		if key in conf.keys():
			conf_items = string.split(conf[key], sep = ' ')
			conf_items.reverse()
			for item in conf_items:
				if key != 'fix_by':
					item_val = item
					item_date = ''
				else:
					due_date = re.search('(.*)\{([0-9]{4,}-(01|02|03|04|05|06|07|08|09|10|11|12)-([012][1-9]|10|20|30|31))\}', item)
					if due_date == None:
						item_val = item
						item_date = ''
					else:
						item_val = due_date.group(1)
						item_date = due_date.group(2)

				if item_val not in config.issues[key]:
					if first_run:
						config.issues[key].insert(0, item_val)
					else:
						config.issues[key].insert(-1, item_val)
					if key == 'fix_by':
						config.fix_by_dates[item_val] = item_date

	if config.vcs == None:
		for key in ['vcs']:
			if key in conf.keys() and conf[key] in BACKENDS:
				config.vcs = BACKENDS[conf[key]]
	if config.project_name == 'Nitpick Project':
		if 'project_name' in conf.keys():
			config.project_name = conf['project_name']

	if config.use_schedule == False and 'schedule' in conf.keys():
		if conf['schedule'] == 'True':
			config.use_schedule = True
		else:
			config.use_schedule = False

	config.users = []
	config.users_times = {}
	for line in fileinput.input(repo_path + 'config/users'):
		if line == '\n':
			continue

		work_units = re.search('(.*) \(([0-9.]+,[0-9.]+,[0-9.]+,[0-9.]+,[0-9.]+,[0-9.]+,[0-9.]+)\)', line)

		if work_units == None:
			name = line
			work_units = '0,0,0,0,0,0,0'
		else:
			name = work_units.group(1)
			work_units = work_units.group(2)

		name = string.strip(name)

		if name not in config.users:
			config.users.append(name)
			config.users_times[name] = work_units.split(',')


# Load the configuration out of the database.
#
# Returns True on success, False if the database couldn't be located
def load_config():
	# First we need to seek up until we find the database. It should be at the root of the project
	pwd = os.path.abspath('.')
	while pwd != '/':
		if os.path.exists(pwd + '/.nitpick') and os.path.isdir(pwd + '/.nitpick'):
			config.db_path = pwd + '/.nitpick/'
			break
		pwd = os.path.dirname(pwd)
	if config.db_path == '':
		return False

	for key in ['components', 'fix_by', 'priority', 'severity', 'state', 'resolution', 'type']:
		config.issues[key] = []
	
	_load_config(config.db_path)

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

class IssueDB:
	uuid = ''
	db = {}
	foreign_repos = False
	repo_list = {}
	repo_paths = {}

	def __init__(self):
		self.load_issue_db()

	def has_foreign(self):
		return self.foreign_repos

	def has_nonclones(self):
		if len(self.db) > 2:
			return True
		else:
			return False

	def repos(self):
		result = copy.copy(self.repo_list.keys())
		result.sort()
		return result

	def issues(self):
		issue_list = []
		for repo in self.db.keys():
			if repo == 'format':
				continue
			issue_list.extend(self.db[repo].keys())

		return issue_list

	def issue(self, hash):
		for repo in self.db.keys():
			if repo == 'format':
				continue
			if hash in self.db[repo]:
				return self.db[repo][hash]
		return None

	def issue_repo(self, hash):
		for repo in self.db.keys():
			if repo == 'format':
				continue
			if hash in self.db[repo]:
				return repo

	# Save the issue_db cache after modifying it
	def save_issue_db(self):
		cache_file = gzip.open(config.db_path + 'issue_cache', 'w')
		cPickle.dump(self.db, cache_file)
		cache_file.close()

	# Load the list of issues and some basic information about each one.
	# Returns a dict keyed on issue hash which contains the a dict with all the
	# fields in the issue files, except the content.
	#
	# An additional field of 'path' exists which is the directory of the issue
	# An additional field of 'repo' exists which is the name of the repository the issue is from
	# An additional field of 'repo_uuid' exists which is the uuid of the repository the issue is from
	# An internal field of 'issue_db_cached_date' also exists.
	def load_issue_db(self):
		uuid_file = open(config.db_path + 'uuid', 'r')
		self.uuid = uuid_file.read()
		uuid_file.close()

		self.repo_list = {'Local' : (self.uuid, config.db_path)}
		self.repo_paths = { self.uuid : [config.db_path] }

		try:
			cache_file = gzip.open(config.db_path + 'issue_cache', 'r')
			self.db = cPickle.load(cache_file)
			cache_file.close()
		except:
			# Something is wrong with the cache, so start again
			self.db = {'format' : ISSUE_CACHE_FORMAT}

		if 'format' not in self.db.keys() or self.db['format'] != ISSUE_CACHE_FORMAT:
			self.db = {'format' : ISSUE_CACHE_FORMAT}

		checked_issues = {}
		if os.path.exists(config.db_path + 'foreign') and os.path.isdir(config.db_path + 'foreign'):
			self.foreign_repos = True

			for foreign_repo in os.listdir(config.db_path + 'foreign'):
				if foreign_repo[0] == '.':
					# Skip VCS dotfiles
					continue

				foreign_path = config.db_path + 'foreign/' + foreign_repo + '/'

				uuid_file = open(foreign_path + 'uuid', 'r')
				foreign_uuid = uuid_file.read()
				uuid_file.close()


				if foreign_uuid not in checked_issues.keys():
					checked_issues[foreign_uuid] = []

				checked_issues[foreign_uuid].extend(
						self.update_cache_from_repo(foreign_path, foreign_uuid, foreign_repo))

				_load_config(foreign_path)

				self.repo_list[foreign_repo] = (foreign_uuid, foreign_path)
				if foreign_uuid in self.repo_paths:
					self.repo_paths[foreign_uuid].append(foreign_path)
				else:
					self.repo_paths[foreign_uuid] = [foreign_path]

		if self.uuid not in checked_issues.keys():
			checked_issues[self.uuid] = []

		checked_issues[self.uuid].extend(
				self.update_cache_from_repo(config.db_path, self.uuid, 'Local'))
		

		# Delete any issues which no longer exist
		for repo in checked_issues.keys():
			for issue in self.db[repo].keys():
				if issue not in checked_issues[repo]:
					del self.db[repo][issue]
					pass

		self.save_issue_db()

	def update_cache_from_repo(self, path, uuid, repo_name):
		if uuid not in self.db:
			self.db[uuid] = {}

		# Ensure that the cache is up to date
		checked_issues = []
		for outer_dir in os.listdir(path):
			if len(outer_dir) != 1 or not os.path.isdir(path + outer_dir):
				continue

			for inner_dir in os.listdir(path + outer_dir):
				if len(inner_dir) != 1 or not os.path.isdir(path + outer_dir + '/' + inner_dir):
					continue

				for hash in os.listdir(path + outer_dir + '/' + inner_dir):
					if hash[0] == '.': 
						# Some VCSes use dotfiles on a per directory basis
						continue

					hash_path = path + outer_dir + '/' + inner_dir + '/' + hash

					checked_issues.append(hash)

					if hash not in self.db[uuid] or \
						self.db[uuid][hash]['issue_db_cached_date'] < os.path.getmtime(hash_path + '/issue'):
						self.db[uuid][hash] = parse_file(hash_path + '/issue')
						del self.db[uuid][hash]['content']
						self.db[uuid][hash]['issue_db_cached_date'] = os.path.getmtime(hash_path + '/issue')
					self.db[uuid][hash]['path'] = hash_path
					self.db[uuid][hash]['repo'] = repo_name
					self.db[uuid][hash]['repo_uuid'] = uuid
		return checked_issues

	# Turn a partial hash into a full hash
	# Returns:
	# 	- None on hash not found
	# 	- '' on ambiguous result
	# 	- the hash on success
	def disambiguate_hash(self, partial_hash):
		fullhash = ''

		for hash in self.issues():
			if partial_hash in hash:
				if fullhash != '':
					return ''
				else:
					fullhash = hash
		if fullhash == '':
			return None
		return fullhash

	# Return the list of comments for the given issue
	def get_comment_list(self, issue):
		issue_obj = self.issue(issue)

		comments = []
		for repo_path in self.repo_paths[issue_obj['repo_uuid']]:
			issue_path = repo_path + issue[0] + '/' + issue[1] + '/' + issue + '/'

			if not os.path.exists(issue_path):
				# Don't fail if an issue doesn't have comments in a clone
				continue

			for file in os.listdir(issue_path):
				if not os.path.isfile(issue_path + file):
					continue
				if '.' in file or file == 'issue': # Only select comments, not attachments or the root issue
					continue

				comments.append(file)
		return comments

	def get_comment(self, issue, comment_hash):
		issue_obj = self.issue(issue)

		for repo_path in self.repo_paths[issue_obj['repo_uuid']]:
			issue_path = repo_path + issue[0] + '/' + issue[1] + '/' + issue + '/'
			if os.path.exists(issue_path + comment_hash):
				comment = parse_file(issue_path + comment_hash)
				comment['hash'] = comment_hash

				return comment
		return None

	# Load the entire comment tree for the given issue hash and return it as a tree.
	#
	# The direct object is a list of comments. Each comment is then a dictionary with all the usual
	# fields along with an additional field, 'children' which is a list of children comment.
	def produce_comment_tree(self, issue):
		issue_obj = self.issue(issue)

		# Load all the comments
		comments = {}
		for repo_path in self.repo_paths[issue_obj['repo_uuid']]:
			issue_path = repo_path + issue[0] + '/' + issue[1] + '/' + issue + '/'

			if not os.path.exists(issue_path):
				# Don't fail if an issue doesn't have comments in a clone
				continue

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
				if comment['Parent'] not in comments:
					comment['Parent'] = 'issue'
					comment_tree.append(comment)
				else:
					comments[comment['Parent']]['children'].append(comment)

		# Now order the tree based upon the dates
		for comment in comments.values():
			comment['children'].sort(key = lambda child: time.mktime(time.strptime(child['Date'], DATEFORMAT)))
		comment_tree.sort(key = lambda comment: time.mktime(time.strptime(comment['Date'], DATEFORMAT)))

		return comment_tree

	def _issue_referenced_in_field(self, issue, field):
		output = ''
		for hash in self.issues():
			if issue in self.issue(hash)[field]:
				output += '%s ' % hash
		return output

	# Return a space separated list of the issues the given issue is a dependent of.
	def issue_dependent_of(self, issue):
		return self._issue_referenced_in_field(issue, 'Depends_On')

	def issue_duplicate_of(self, issue):
		return self._issue_referenced_in_field(issue, 'Duplicate_Of')

	# Return a string of space separated issue hashes the given issue is a duplicate of
	def get_issue_duplicates(self, issue):
		duplicate_issues = ''
		if len(self.issue(issue)['Duplicate_Of']) > 10:
			duplicate_issues = self.issue(issue)['Duplicate_Of'] + ' '
		duplicate_issues += self.issue_duplicate_of(issue)

		issue_list = duplicate_issues.split(' ')
		for i in issue_list:
			if i == '':
				continue
			if len(self.issue(i)['Duplicate_Of']) > 10:
				duplicate_issues += self.issue(i)['Duplicate_Of'] + ' '
			duplicate_issues += self.issue_duplicate_of(i)

		issues = duplicate_issues.split(' ')

		try:
			issues.remove('')
		except:
			pass

		try:
			while True:
				issues.remove(issue)
		except:
			pass

		duplicate_issues = ' '.join(set(issues))

		return duplicate_issues

	# Take an issue dict and add it to the system. Does not commit.
	#
	# Returns (issue filename, issue hash)
	def add_issue(self, issue, repo = 'Local', hash = None):
		if hash == None:
			hash = hashlib.sha256(cPickle.dumps(issue)).hexdigest()

		repo_dir = self.repo_list[repo][1]
		issue_dir = repo_dir + hash[0] + '/' + hash[1] + '/' + hash
		config.vcs.mkdir(issue_dir)

		issue_filename = issue_dir + '/issue'
		format_file(issue_filename, issue)

		config.vcs.add_changes(issue_filename)

		return (issue_filename, hash)

	# Take a comment dict and add it to the system. Does not commit.
	#
	# Returns the comment filename
	def add_comment(self, issue, comment, hash = None):
		if hash == None:
			hash = hashlib.sha256(cPickle.dumps(comment)).hexdigest()

		comment_filename = self.issue(issue)['path'] + '/' + hash
		format_file(comment_filename, comment)

		config.vcs.add_changes(comment_filename)

		return comment_filename

	# Create an attachment. Returns the attachment hash or None if there is no attachment created.
	# The latter could happen if the empty string is passed in for the content.
	def add_attachment(self, issue, content):
		if len(content) == 0:
			return None

		hash = hashlib.sha256(content).hexdigest()

		data_file_name = self.issue(issue)['path'] + '/' + hash + '.data'

		data_file = open(data_file_name, 'w')
		data_file.write(content)
		data_file.close()
		config.vcs.add_changes(data_file_name)

		return hash


	# Check that the issue exists and that it has the comment to reply to if one is supplied.
	# Returns
	# 	(issue hash, parent id) - on Success
	# 	None                    - If the issue does not exist
	# 	''                      - If the issue is ambiguous
	# 	(issue hash, None)      - If a comment was specified and it doesn't exist
	# 	(issue hash, '')        - If the comment is ambiguous
	def find_comment_parent(self, partial_issue, partial_comment):
		issue = self.disambiguate_hash(partial_issue)
		if issue == None:
			return None
		elif issue == '':
			return ''
		issue_obj = self.issue(issue)

		parent = 'issue'

		if partial_comment:
			for repo_path in self.repo_paths[issue_obj['repo_uuid']]:
				issue_path = repo_path + issue[0] + '/' + issue[1] + '/' + issue + '/'
				try:
					for file in os.listdir(issue_path):
						if not os.path.isfile(issue_path + file):
							continue
						if '.' in file or file == 'issue': # Only support comments, not attachments or the root issue
							continue

						if partial_comment in file:
							if parent != 'issue' and parent != file:
								return (issue, '')
							else:
								parent = file
				except:
					pass
			if parent == 'issue':
				return (issue, None)
		
		return (issue, parent)

	def change_issue(self, issue, prop, newvalue):
		if config.db_path == '':
			return False

		self.load_issue_db()

		issue = self.disambiguate_hash(issue)
		if issue == None:
			print' No such issue'
			return False
		elif issue == '':
			print "Ambiguous issue ID. Please use a longer string"
			return False

		issue_filename = self.issue(issue)['path'] + '/issue'
		issue = parse_file(issue_filename)
		issue[prop] = newvalue
		format_file(issue_filename, issue)

		config.vcs.add_changes(issue_filename)

		return True

# The object which contains all the scheduling information for the task scheduling.
class SchedIssue():
	def __init__(self, issue):
		self.hash = issue
		self.issue = db.issue(issue)
		self.work_units = float(self.issue['Units_of_Work']) * (1 - float(self.issue['Percent_Complete'])/100)
		self.owner = self.issue['Owner']
		self.owner_production = config.users_times[self.owner]

		units_per_week = sum([float(i) for i in self.owner_production])
		if units_per_week == 0:
			units_per_week = 0.000001
		self.estimated_work_weeks = self.work_units / units_per_week

		self.critical_work_weeks = -1 # Total number of work weeks this must start before the deadline
		self.sched_start_date = None # The earliest this can start according to the plan
		self.sched_end_date = None # When this should be finished given correct estimates and it start at sched_start_date

		self.depends_on = []
		self.dependent_of = []

	def __repr__(self):
		return repr({
			'issue': self.issue,
			'owner' : self.owner,
			'owner_production' : self.owner_production,
			'estimated_work_weeks' : self.estimated_work_weeks,
			'critical_work_weeks' : self.critical_work_weeks,
			'sched_start_date' : self.sched_start_date,
			'sched_end_date' : self.sched_end_date,
			'depends_on' : self.depends_on,
			'dependent_of' : self.dependent_of,
			})

# Use the entire list of issues and return a dictionary of lists, keyed off the owner, of the order
# issues should be completed. Each of these issues will be a SchedIssue and have various scheduling
# pieces of information.
#
# Returns None if there is a loop.
def schedule_all_tasks():
	debug_scheduling = False

	load_db()

	# We only want issues which aren't closed
	def isnt_closed(issue):
		if db.issue(issue)['State'] != config.issues['state'][-1]:
			return True
		return False

	issue_list = filter(isnt_closed, db.issues())
	issues = {i: SchedIssue(i) for i in issue_list}

	# Now fill in the dependency graph, the depends_on issues first
	for issue in issues.values():
		def f(issue):
			return issue in issues
		issue.depends_on = [issues[i] for i in filter(f, issue.issue['Depends_On'].split(' '))]

	# Now fill in the dependent_of issues
	for issue in issues.values():
		for i in issue.depends_on:
			i.dependent_of.append(issue)

	# Compute the number of days each milestone must be completed before the latest milestone.
	# This will help order the tasks by making the root of their dependency tree (working
	# backwards in time) pegged to come so many days before the last milestone should happen.
	# This won't perform miracles however, if the schedule is impossible it still won't happen.
	fix_by_dates = filter(lambda d: d != '', config.fix_by_dates.values())
	last_fixby_date = max([datetime.datetime.strptime(d, '%Y-%m-%d') for d in fix_by_dates])
	fixby_critical_weeks = {}
	for fix_by in config.fix_by_dates.keys():
		if config.fix_by_dates[fix_by] == '':
                    fixby_critical_weeks[fix_by] = 0
                    continue
		fix_by_date = datetime.datetime.strptime(config.fix_by_dates[fix_by], '%Y-%m-%d')
		fixby_critical_weeks[fix_by] = (last_fixby_date - fix_by_date).days / 7
	
	# Now compute the total number of workweeks work must begin before the deadline in order to
	# make the deadline. We start with the set of tasks which are at the end of the line and
	# recurse from there.
	visited_issues = []
	task_stack = filter(lambda i: len(i.dependent_of) == 0, issues.values())
	task_stack = [(i, fixby_critical_weeks[i.issue['Fix_By']]) for i in task_stack]

	while len(task_stack) > 0:
		task_stack.append(task_stack[-1])
		i, parent_val = task_stack.pop()

		if len(visited_issues) > 0 and i.hash == visited_issues[-1].hash:
			# We've already processed this, pop the stack
			visited_issues.pop()
			task_stack.pop()
			continue

		work_weeks = max(0.00001, i.estimated_work_weeks)
		i.critical_work_weeks = max(i.critical_work_weeks, work_weeks + parent_val)

		if i in visited_issues:
			if debug_scheduling:
				print "Dependency loop detected in issues %s. Not recursing" % i.hash
			return None
		else:
			visited_issues.append(i)
			task_stack.extend([(child, i.critical_work_weeks) for child in i.depends_on])

	# Now we sort all the issues by the critical number of work weeks in descending order. This
	# does two things. First it is a topological sort because there are no cycles (tested above)
	# and issues always have a higher critical_work_weeks value than its dependents.
	priority_list = sorted(issues.values(), key=lambda i: i.critical_work_weeks, reverse=True)
	
	# Now we separate the tasks into a list for each owner. At this time we also configure
	# initial start and end dates for the tasks. We'll refine these in further steps. We are
	# careful to ensure that the start and end dates occur on days the owner will be working.
	timelines = {}
	today = datetime.date.today()
	one_day = datetime.timedelta(days=1)

	def move_to_workday(date, work_week):
		# Returns the actual date to use. This will be incrementally moved ahead to a work
		# day based upon the work hours of the owner.
		#
		# work_week is the owner_production list
		if work_week == ['0', '0', '0', '0', '0', '0', '0']:
			# This person never works, so we shouldn't move anything
			return date

		while work_week[date.weekday()] == '0':
			date = date + one_day

		return date

	def compute_task_end_date(issue):
		units_remaining = issue.work_units
		issue.sched_end_date = issue.sched_start_date
		first = True
		while units_remaining > 0:
			if not first:
				issue.sched_end_date = issue.sched_end_date + one_day
			else:
				first = False

			if issue.owner_production == ['0', '0', '0', '0', '0', '0', '0']:
				# The owner doesn't work, so take forever
				work_done = 0.001
			else:
				work_done = float(issue.owner_production[issue.sched_end_date.weekday()])
			units_remaining = units_remaining - work_done

	for issue in priority_list:
		if issue.owner not in timelines:
			timelines[issue.owner] = []

		# Compute start time
		if timelines[issue.owner] == []:
			# Start today because there are no tasks before this one
			issue.sched_start_date = today
		else:
			# Start one day after the last task
			last_issue = timelines[issue.owner][-1]
			issue.sched_start_date = last_issue.sched_end_date + one_day
		issue.sched_start_date = move_to_workday(issue.sched_start_date,
				issue.owner_production)

		timelines[issue.owner].append(issue)

		compute_task_end_date(issue)

	def print_schedule():
		if not debug_scheduling:
			return

		for user in timelines.keys():
			for issue in timelines[user]:
				print 'User: %s Issue %s Start: %s End: %s' % (user, issue.hash,
						issue.sched_start_date, issue.sched_end_date)
	print_schedule()

	# Now we go through, again following the topological sort, to fix up any dates which don't
	# match the dependency graph. This can happen if two dependent tasks are owned by different
	# people. Anytime we move something forward, we have to move everything behind it forward
	# for that same person to avoid overlaps.
	for issue in priority_list:
		dependency_finish_date = [i.sched_end_date for i in issue.depends_on]

		# We count the previous item in the person's queue as a dependency here to ensure
		# that we don't have any overlaps. Since we are iterating in sort order we only have
		# to be concerned with the previous task. Even if this task gets moved ahead several
		# other tasks they'll all be moved forward because of this dependency when the are
		# processed.
		queue_num = timelines[issue.owner].index(issue)
		if queue_num > 0:
			dependency_finish_date.append(timelines[issue.owner][queue_num - 1].sched_end_date)

		if debug_scheduling:
			print issue.hash, queue_num, dependency_finish_date
		
		if dependency_finish_date == []:
			dependency_finish_date = move_to_workday(today, issue.owner_production) - one_day
		else:
			dependency_finish_date = max(dependency_finish_date)

		while issue.sched_start_date <= dependency_finish_date:
			# For each day we have to shift this task, we make sure to shift both the
			# start and finish and to keep the start and finish on workdays
			def is_workday(owner, date):
				return float(owner[date.weekday()]) > 0

			if is_workday(issue.owner_production, issue.sched_start_date):
				issue.sched_end_date = issue.sched_end_date + one_day
				issue.sched_end_date = move_to_workday(issue.sched_end_date,
						issue.owner_production)

			issue.sched_start_date = issue.sched_start_date + one_day

		# Ensure that the start is a workday, since it may have been moved onto a weekend
		issue.sched_start_date = move_to_workday(issue.sched_start_date,
				issue.owner_production)

	print_schedule()

	# Now that we have the critical path laid out we will have a number of gaps due to the
	# dependency graph. We now try to move items backwards in time to fill these gaps. This
	# should pull unrelated items backwards in time. Unfortunately we have to do this in time
	# order across all the users, which makes the algorithm a bit annoying. We have to do this
	# to maximize the possibilities of depends_on items being moved earlier before a task is
	# moved, since we must at all times adhere to the dependency graph.
	
	# Find the next gap in the schedule of the given user and update user_list.
	#
	# Userlist is a dictionary of tuples, one per user. The tuple is (start date, index). The
	# start date is start date of the next gap. The index is the index of the next queue item
	# which the gap is before.
	#
	# If the user doesn't have anymore gaps they will be removed from the user_list.
	def get_next_gap(user, user_list, timelines):
		start_date = user_list[user][0]
		index = user_list[user][1]
		max_index = len(timelines[user])

		if debug_scheduling:
			if index == -1:
				i = 0
			else:
				i = index
			print 'Starting %s at %s %s' % (user, start_date, timelines[user][i].sched_start_date)

		if index == -1:
			if timelines[user] == []:
				# The user_list as just been created and the user has no task assigned,
				# remove them
				if debug_scheduling:
					print "User %s has no tasks" % user
				del user_list[user]
				return
			else:
				index = 0
				if start_date < timelines[user][index].sched_start_date:
					if debug_scheduling:
						print 'There is a gap at the beginning, using it'
					user_list[user] = (start_date, index)
					return

		start_date = move_to_workday(start_date, timelines[user][0].owner_production)
		
		if debug_scheduling:
			print start_date, timelines[user][index].sched_start_date

		first_time = True # Ensure that we always make progress
		while first_time or start_date >= timelines[user][index].sched_start_date:
			first_time = False
			start_date = timelines[user][index].sched_end_date + one_day
			start_date = move_to_workday(start_date, timelines[user][0].owner_production)
			index += 1

			if index >= max_index:
				# There are no scheduled tasks beyond the last gap, so this user is
				# done. Remove them.
				if debug_scheduling:
					print "Reached end of queue for user %s" % user
				del user_list[user]
				return

			user_list[user] = (start_date, index)
		if debug_scheduling:
			print 'Finishing at %s' % start_date

	user_list = {user: (today, -1) for user in timelines.keys()}
	for user in user_list.keys():
		get_next_gap(user, user_list, timelines)

	if debug_scheduling:
		print "starting userlist", user_list

	while len(user_list.keys()) > 0:
		# Find the user with the nearest gap start
		user = user_list.keys()[0]
		for u in user_list.keys():
			if user_list[u][0] < user_list[user][0]:
				user = u

		if debug_scheduling:
			print 'Traverting user %s' % user

		gap_start = user_list[user][0]
		gap_index = user_list[user][1]

		# Compute length of gap
		gap_end = gap_start
		gap_length = 0
		while gap_end < timelines[user][gap_index].sched_start_date:
			gap_length += float(timelines[user][0].owner_production[gap_end.weekday()])
			gap_end += one_day
		gap_end -= one_day

		if debug_scheduling:
			print "gap start", gap_start, 'gap end', gap_end, 'gap length', gap_length
		
		# Find first task which will fit into this gap and is allowed by the dependency
		# graph. This is suboptimal, but an optimal choice would likely require dynamic
		# programming. It is perhaps possible to do better by finding the longest task which
		# will fit, but that doesn't take into account that a shorter task may be on a
		# longer path than a longer task.
		task = None
		new_task_start = gap_start
		for i in range(gap_index, len(timelines[user])):
			t = timelines[user][i]

			if debug_scheduling:
				print 'checking task %s' % t.hash[:8]

			if t.work_units > gap_length:
				if debug_scheduling:
					print 'Rejecting due to gap length %f %f' % (t.work_units, gap_length)
				continue

			dependency_dates = [j.sched_end_date for j in t.depends_on]
			if len(dependency_dates) > 0 and max(dependency_dates) >= gap_end:
				if debug_scheduling:
					print 'Rejecting due to dependency', max(dependency_dates), gap_end
				continue

			# We now know that the task will fit if it starts at the beginning of the
			# gap and that it can start before the end of the gap, so we need to test if
			# it can be finished inside the gap given the earliest the it can start due
			# to the dependencies.
			dependency_dates.append(gap_start)
			new_task_start = max(dependency_dates)
			d = new_task_start
			l = 0
			while d <= gap_end:
				l += float(timelines[user][0].owner_production[d.weekday()])
				d += one_day
			if l < t.work_units:
				# Turns out it can't be finished
				if debug_scheduling:
					print 'Rejecting due to mid-gap length', t.work_units, l
				continue
		
			# This task fits, use it
			task = t
                        task_index = i
			break

	
		if task != None:
			if debug_scheduling:
				print 'using task %s' % task.hash[:8]

			# Put the task we found into the gap and continue
			del timelines[user][task_index]
			timelines[user].insert(gap_index, task)

			task.sched_start_date = move_to_workday(new_task_start,
					task.owner_production)
			compute_task_end_date(task)
		else:
			if debug_scheduling:
				print 'No task fits this gap'

		print_schedule()
		get_next_gap(user, user_list, timelines)

	# Extend any task which ends just before a break in work (such as a
	# weekend) through the weekend.  This is to not leave scheduling gaps
	# in the display when a task happens to end the day before a weekend
	# and there isn't really any such gap.
	for user in timelines.keys():
		for task in timelines[user]:
			task.sched_end_date += one_day
			task.sched_end_date = move_to_workday(task.sched_end_date, task.owner_production)
			task.sched_end_date -= one_day

	if debug_scheduling:
		print "Final schedule"
		print_schedule()
	return timelines

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

def cmd_init(args):
	backend = BACKENDS[args.vcs]
	config.db_path = args.dir + '/'

	def_config = {
			'vcs'          : args.vcs,
			'project_name' : 'Nitpick Project',
			'schedule'     : False,
		}

	for key in default_config.keys():
		def_config[key] = ' '.join(default_config[key])

	backend.mkdir(args.dir + '/config')

	config_filename = args.dir + '/config/config'
	format_file(config_filename, def_config)
	backend.add_changes(config_filename)

	users_filename = args.dir + '/config/users'
	users = open(users_filename, 'w')
	users.write(default_users)
	users.close()
	backend.add_changes(users_filename)

	uuid_filename = args.dir + '/uuid'
	uuid_file = open(uuid_filename, 'w')
	uuid_file.write(uuid.uuid4().hex)
	uuid_file.close()
	backend.add_changes(uuid_filename)

	backend.ignore(args.dir + '/issue_cache')

	load_db()

	backend.commit()

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
			'Depends_On'    : '',
			'Duplicate_Of'  : '',
			'Units_of_Work' : '1000', # A large default value to force people to estimate if they use that feature
			'Completion'    : '0',
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

	issue_filename, issue_hash = db.add_issue(issue)

	config.vcs.commit()

	return True

def cmd_list(args):
	if config.db_path == '':
		return False

	load_db()

	for hash in db.issues():
		if hash == 'format':
			continue

		if not args.all and args.state != db.issue(hash)['State']:
			continue

		if not args.all and args.component and args.component != db.issue(hash)['Component']:
			continue

		if args.fullhash:
			printhash = hash
		else:
			printhash = hash[:8]
		print "%s (%s): %s" % (printhash, db.issue(hash)['State'], db.issue(hash)['Title'])
	return True

def cmd_cat(args):
	if config.db_path == '':
		return False

	load_db()

	hash = db.disambiguate_hash(args.issue)
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
		if key in ['content', 'Duplicate_Of']:
			continue

		if not args.noformat:
			print '|',
		print "%s: %s" % (key, issue[key])

	if not args.noformat:
		print '|',
	print "Dependent_Of: %s" % db.issue_dependent_of(hash)

	if not args.noformat:
		print '|',
	print "Duplicate_Of: %s" % db.get_issue_duplicates(hash)

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

	comment_stack = db.produce_comment_tree(hash)
	comment_stack.reverse()
	comment_depth = [1] * len(comment_stack)
	parent_children_stack = [2] * len(comment_stack)
	depth = 0

	while len(comment_stack) > 0:
		comment = comment_stack.pop()
		old_depth = depth
		depth = comment_depth.pop()
		parent_children = parent_children_stack.pop()


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

		if parent_children == 1 and len(comment['children']) == 1:
			comment_depth.extend([depth] * len(comment['children']))
		else:
			comment_depth.extend([depth + 1] * len(comment['children']))
		parent_children_stack.extend([len(comment['children'])] * len(comment['children']))

	return True

def cmd_comment(args):
	if config.db_path == '':
		return False

	editor = editor_found()
	if editor == None:
		return False

	if config.username == '':
		print 'Failed to determine username. Please set NITPICK_USERNAME'
		return False

	load_db()

	comment_parent = db.find_comment_parent(args.issue, args.comment)
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
	comment_filename = db.issue(issue)['path'] + '/comment.tmp'
	format_file(comment_filename, comment)
	result = os.system(editor + ' ' + comment_filename)

	if result != 0:
		print 'Comment aborted'
		os.unlink(comment_filename)
		return True

	comment = {}
	comment = parse_file(comment_filename)
	os.unlink(comment_filename)

	comment_filename = db.add_comment(issue, comment)

	config.vcs.commit()
	return True

def cmd_state(args):
	if db.change_issue(args.issue, 'State', args.newstate):
		config.vcs.commit()
		return True
	else:
		return False

def cmd_severity(args):
	if db.change_issue(args.issue, 'Severity', args.newseverity):
		config.vcs.commit()
		return True
	else:
		return False

def cmd_component(args):
	if db.change_issue(args.issue, 'Component', args.newcomponent):
		config.vcs.commit()
		return True
	else:
		return False

def cmd_priority(args):
	if db.change_issue(args.issue, 'Priority', args.newpriority):
		config.vcs.commit()
		return True
	else:
		return False

def cmd_resolution(args):
	if db.change_issue(args.issue, 'Resolution', args.newresolution):
		config.vcs.commit()
		return True
	else:
		return False

def cmd_type(args):
	if db.change_issue(args.issue, 'Type', args.newtype):
		config.vcs.commit()
		return True
	else:
		return False

def cmd_fixby(args):
	if db.change_issue(args.issue, 'Fix_By', args.newfixby):
		config.vcs.commit()
		return True
	else:
		return False

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

	if db.change_issue(args.issue, 'Owner', fulluser):
		config.vcs.commit()
		return True
	else:
		return False

def cmd_users(args):
	if config.db_path == '':
		return False

	for user in config.users:
		print user
	return True

def cmd_web(args):
	if config.db_path == '':
		return False

	load_db()

	server = BaseHTTPServer.HTTPServer(('localhost', args.port), nitpick_web)

	if args.readonly:
		config.readonly = True

	print 'Starting server on localhost:%d' % args.port

	def get_process_list():
		ps = subprocess.Popen("ps -u$USER", shell=True, stdout=subprocess.PIPE)
		pslist = ps.stdout.read()
		ps.stdout.close()
		ps.wait()

		return pslist

        url = 'http://localhost:%d' % args.port
        browser = None

        if not args.noopen:
            # Try to start a webbrowser to look at the UI
            if sys.platform == 'darwin': # Assume OSX
                    os.system('open %s' % url)
            elif os.name == 'posix': # Assume Unix-like
                    if 'DISPLAY' in os.environ.keys() and os.environ['DISPLAY'] != "":
                            # Try a graphical browser first
                            
                            # If there is one running, it's the preferred one
                            ps = get_process_list()
                            for prog in POSIX_GUI_BROWSERS:
                                    if prog[0] in ps:
                                            try:
                                                    browser = subprocess.Popen([prog[1], url])
                                                    break
                                            except:
                                                    pass

                            # No known browser was running, try starting one
                            if not browser:
                                    for prog in POSIX_GUI_BROWSERS:
                                            try:
                                                    browser = subprocess.Popen([prog[1], url])
                                                    break
                                            except:
                                                    pass
                            
                    # We haven't started a GUI browser, try a CLI browser
                    if not browser:
                            for prog in POSIX_CLI_BROWSERS:
                                    try:
                                            browser = subprocess.Popen([prog, url])
                                            break
                                    except:
                                            pass
	
	while not config.endweb:
		server.handle_request()

	if browser:
		browser.wait()

	return True

nitpick_to_bug = {
	'Title'         : 'title',
	'Date'          : 'created_at',
	'State'         : 'status',
	'Severity'      : 'severity',
	'Component'     : 'component',
	'Reported_By'   : 'reporter',
	'Seen_In_Build' : 'seen_in',
	'Owner'         : 'owner',
	'content'       : 'description',
	'Depends_On'    : '_depends_on',
	'Duplicate_Of'  : '_duplicate_of',
	'Priority'      : '_priority',
	'Fix_By'        : '_fix_by',
	'Resolution'    : '_resolution',
	'Type'          : '_type',
	'Project_Name'  : 'project_name',
	'Project_ID'    : 'project_id',
}

bug_to_nitpick = {
	'title'         : 'Title',
	'created_at'    : 'Date',
	'status'        : 'State',
	'severity'      : 'Severity',
	'component'     : 'Component',
	'reporter'      : 'Reported_By',
	'seen_in'       : 'Seen_In_Build',
	'owner'         : 'Owner',
	'description'   : 'content',
	'_depends_on'   : 'Depends_On',
	'_duplicate_of' : 'Duplicate_Of',
	'_priority'     : 'Priority',
	'_fix_by'       : 'Fix_By',
	'_resolution'   : 'Resolution',
	'_type'         : 'Type',
	'project_name'  : 'Project_Name',
	'project_id'    : 'Project_ID',
}

def format_issue_for_export(hash):
	issue = parse_file(config.db_path + hash[0] + '/' + hash[1] + '/' + hash + '/issue')

	def format_date(date):
		return datetime.datetime.fromtimestamp(time.mktime(time.strptime(date, DATEFORMAT))).isoformat()

	unsafe_hash = urllib.unquote(hash)

	bug = {}
	bug['format'] = 'http://travisbrown.ca/projects/bug_interchange.txt'
	bug[unsafe_hash] = {}
	bug[unsafe_hash]['metadata'] = {}
	bug[unsafe_hash]['metadata']['metadata_modified_at'] = datetime.datetime.now().isoformat()
	bug[unsafe_hash]['metadata']['project_name'] =  config.project_name
	bug[unsafe_hash]['metadata']['project_id'] =  db.issue_repo(hash)


	for key in issue.keys():
		if key == 'Date':
			bug[unsafe_hash]['metadata'][nitpick_to_bug[key]] = format_date(issue[key])
		elif key == 'Depends_On' or key == 'Duplicate_Of':
			if len(issue[key]) > 0:
				bug[unsafe_hash]['metadata'][nitpick_to_bug[key]] = issue[key].split(' ')
			else:
				bug[unsafe_hash]['metadata'][nitpick_to_bug[key]] = []
		else:
			if key not in nitpick_to_bug:
				# Not every key gets exported. The scheduling data for example
				continue

			bug[unsafe_hash]['metadata'][nitpick_to_bug[key]] = issue[key]

	comment_stack = db.produce_comment_tree(hash)
	comment_stack.reverse()
	comment_depth = [1] * len(comment_stack)
	parent_children_stack = [2] * len(comment_stack)
	parent_stack = ['issue']
	depth = 0

	while len(comment_stack) > 0:
		comment = comment_stack.pop()
		old_depth = depth
		depth = comment_depth.pop()
		parent_children = parent_children_stack.pop()

		while parent_stack[-1] != comment['Parent']:
			parent_stack.pop()

		chash = urllib.unquote(comment['hash'])
		bug[unsafe_hash][chash] = {}
		bug[unsafe_hash][chash]['name'] = comment['User']
		bug[unsafe_hash][chash]['created_at'] = format_date(comment['Date'])
		bug[unsafe_hash][chash]['comment'] = comment['content']
		bug[unsafe_hash][chash]['in-reply-to'] = copy.copy(parent_stack)[-5:]
		bug[unsafe_hash][chash]['in-reply-to'].reverse()

		comment['children'].reverse()
		comment_stack.extend(comment['children'])

		if parent_children == 1 and len(comment['children']) == 1:
			comment_depth.extend([depth] * len(comment['children']))
		else:
			comment_depth.extend([depth + 1] * len(comment['children']))
		parent_children_stack.extend([len(comment['children'])] * len(comment['children']))

		parent_stack.append(comment['hash'])

	return json.dumps(bug, sort_keys=True, indent=4)

def cmd_export(args):
	if config.db_path == '':
		return False

	load_db()

	hash = db.disambiguate_hash(args.issue)
	if hash == None:
		print "No such issue"
		return False
	elif hash == '':
		print "Ambiguous issue ID. Please use a longer string"
		return False

	print format_issue_for_export(hash)

	return True

def cmd_import(args):
	if config.db_path == '':
		return False

	load_db()

	bug_file = open(args.bugfile, 'r')
	bugs = json.load(bug_file)

	def format_date(date):
		timestamp = None

		if len(date) == len('2012-09-05T05:48:39'):
			# local time
			timestamp = datetime.datetime.strptime(date[:19], '%Y-%m-%dT%H:%M:%S')
		elif len(date) == len('2012-09-05T05:48:39Z'):
			# UTC time
			timestamp = datetime.datetime.strptime(date[:19], '%Y-%m-%dT%H:%M:%S')
		else:
			print 'Unsupported timestamp format "%s".' % date

		return time.strftime(DATEFORMAT, timestamp.timetuple())

	for bugid in bugs.keys():
		if bugid == 'format':
			continue

		bug = bugs[bugid]

		safe_bugid = urllib.quote(bugid, '')

		new_issue = False
		issue = db.issue(safe_bugid)
		if issue == None:
			# Create a new issue
			new_issue = True
			issue = {
				'Title'            : 'Issue title',
				'Severity'         : config.issues['severity'][0],
				'Priority'         : config.issues['priority'][0],
				'State'            : config.issues['state'][0],
				'Type'             : config.issues['type'][0],
				'Resolution'       : config.issues['resolution'][0],
				'Component'        : config.issues['components'][0],
				'Fix_By'           : config.issues['fix_by'][0],
				'Seen_In_Build'    : '',
				'Date'             : time.strftime(DATEFORMAT, time.gmtime()),
				'Owner'            : config.users[0],
				'Reported_By'      : config.username,
				'Depends_On'       : '',
				'Duplicate_Of'     : '',
				'Units_of_Work'    : '1000',
				'Percent_Complete' : '0',
				'content'          : 'Enter description here'
				}

		# First process metadata (if it exists) to ensure that the issue exists before handling the comments
		if 'metadata' in bug.keys():
			for key in bug['metadata'].keys():
				if key in ['metadata_modified_at']:
					continue

				if key in ['_depends_on', '_duplicate_of']:
					issue[bug_to_nitpick[key]] = ' '.join(bug['metadata'][key])
				elif key in ['created_at']:
					issue[bug_to_nitpick[key]] = format_date(bug['metadata'][key])
				else:
					issue[bug_to_nitpick[key]] = bug['metadata'][key]
		if new_issue:
			db.add_issue(issue, hash=safe_bugid)

		db.save_issue_db()
		db.load_issue_db()

		if new_issue:
			existing_comments = []
		else:
			existing_comments = db.get_comment_list(safe_bugid)

		for commentid in bug.keys():
			if commentid == 'metadata':
				continue

			if commentid in existing_comments:
				# Comments are immutable and so don't get updated
				continue

			comment = bug[commentid]

			issue_comment = {}
			issue_comment['Attachment'] = ''
			issue_comment['User'] = comment['name']
			issue_comment['Date'] = format_date(comment['created_at'])
			issue_comment['content'] = comment['comment']
			issue_comment['Parent'] = comment['in-reply-to'][0]

			safe_commentid = urllib.quote(commentid, '')
			db.add_comment(safe_bugid, issue_comment, hash = safe_commentid)

	db.save_issue_db()
	return True

def cmd_schedule(args):
	if config.db_path == '':
		return False

	schedule = schedule_all_tasks()
	for user in schedule.keys():
		for issue in schedule[user]:
			if db.issue(issue.hash)['Percent_Complete'] == '0':
				action = 'Start'
			else:
				action = 'Continue'

			print 'User: %-25s Issue: %s %s: %s End: %s' % (user, issue.hash[:8], action,
					issue.sched_start_date, issue.sched_end_date)
	
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
        web_cmd.add_argument('--noopen', action='store_true', help='Do not open a browser')
	web_cmd.add_argument('--readonly', action='store_true', help='Present a readonly view suitable for a public dump')
	web_cmd.set_defaults(func=cmd_web)

	export_cmd = subcmds.add_parser('export', help='Export given bug')
	export_cmd.add_argument('issue')
	export_cmd.set_defaults(func=cmd_export)

	import_cmd = subcmds.add_parser('import', help='Import all bugs in bug file')
	import_cmd.add_argument('bugfile')
	import_cmd.set_defaults(func=cmd_import)

	if config.use_schedule:
		schedule_cmd = subcmds.add_parser('sched', help='Display computed project schedule')
		schedule_cmd.set_defaults(func=cmd_schedule)

	args = parser.parse_args()
	result = args.func(args)

	if not result:
		print "Command failed"
		sys.exit(1)
	else:
		sys.exit(0)

