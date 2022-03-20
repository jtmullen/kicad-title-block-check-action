#!/usr/bin/env python3

from subprocess import check_call, CalledProcessError
import os
import yaml
import re
import json
from pathlib import Path
import git
import sys

checkPCB = False
checkSCH = False
failed = ""
fields = ['pageSize','title','company','rev','date','comment1','comment2','comment3','comment4']


## There was an unrecoverable error running the action
## Immediately Exit
def error(cause):
	print("::error::{}".format(cause))
	exit(1)
	

## Add a failed file to the output
## Print the file name and fail reason
## If a file fails multiple times will print new case
##     but will not add duplicated to failed
def fail(fileName, cause):
	global failed
	print("::error file={}::{}".format(fileName, cause))
	if not fileName in failed:
		failed += fileName
		failed += ","


##  Check Title Blocks in a S Expression File
##  Used for PCBs in v5&6 and Schematics in v6
##  They are mostly the same
def checkSExpBlock(checks, commentRegex, sexp, file):
	if "pageSize" in checks:
		## For some reason page size is "page" in .kicad_pcb and "paper" in .kicad_sch
		if "page" in sexp or "paper" in sexp:
			if "page" in sexp:
				size = sexp.page
			else:
				size = sexp.paper
			if not checks["pageSize"] in size:
				fail(file, "Expected Page Size {}, found {}".format(checks["pageSize"], size))
		else:
			fail(file, "Page size not found")

	## Check the non-comment fields
	for field in ["title", "rev", "company", "date"]:
		if field in checks:
			if field in sexp.title_block:
				if not re.match(checks[field], str(sexp.title_block[field]).strip("\"")):
					fail(file, "{}: \"{}\", does not match \"{}\"".format(field, sexp.title_block[field], checks[field])) 
			else:
				fail(file, "{} not found, expected match: {}".format(field, checks[field]))

	## Check the comments
	comments = ["", "", "", ""]
	if "comment" in sexp.title_block:
		sexpComments = sexp.title_block.comment
		if isinstance(sexpComments, list):  ## If it is a list there is only 1 comment
			comments[sexpComments[0]-1] = sexpComments[1]
		else:
			for item in sexpComments:
				comments[item[0]-1] = item[1]
				
	for i in range(0,len(comments)):
		if not re.match(commentRegex[i], str(comments[i]).strip("\"")):
			fail(file, "Comment {}: \"{}\", does not match \"{}\"".format(i+1, comments[i], commentRegex[i]))


## Main function to run checks
def main():
	print("::group::Set Up")
	print("Python Version: {}".format(sys.version))

	try:
		from kicad_parser import KicadPCB
		from kicad_parser import KicadSCH
	except ImportError:
		error("Error importing KiCad Parser Dependency")

	try:
		eventStream = open(os.environ["GITHUB_EVENT_PATH"], 'r')
	except OSError:
		error("Could not Open Github Event Payload")

	eventInfo = json.load(eventStream)
	eventStream.close()

	repoName = eventInfo['repository']['full_name']

	isPR = False
	if "pull_request" in eventInfo:
		prNum = eventInfo['pull_request']['number']
		prBranch = eventInfo['pull_request']['head']['ref']
		prBase = eventInfo['pull_request']['base']['ref']
		prUser = eventInfo['pull_request']['user']['login']
		print("Run for PR#: {} in {} by {}".format(prNum, repoName, prUser))
		print("Branch {} into base {}".format(prBranch, prBase))
		isPR = True
	elif "after" in eventInfo:
		toHash = eventInfo['after']
		fromHash = eventInfo['before']
		branchName = eventInfo['ref']
		print("Run for push on branch: {}".format(branchName))
		print("Hash {} to {}".format(fromHash, toHash))
	else:
		error("Not push or pull request event")

	try:
		os.chdir(os.environ["GITHUB_WORKSPACE"])
	except OSError:
		error("Could not change to GitHub Workspace")

	regexFile = os.environ["INPUT_CONFIG_FILE"]
	print("Input file from: {}".format(regexFile))

	try:
		regexStream = open(regexFile, 'r')
	except OSError:
		error("Could not open the Config File at: {}".format(regexFile))

	try:
		config = yaml.safe_load(regexStream)
	except yaml.YAMLError:
		error("Could not parse the yaml config file")

	regexStream.close()
	
	print("Config is:")
	print(config)
	pcb_checks = {}
	sch_checks = {}
	checkSCH = False
	checkPCB = False
	
	if "all" in config:
		checkPCB = True
		checkSCH = True
		pcb_checks = config['all'].copy()
		sch_checks = config['all'].copy()
		print("Check PCB for:")
		print(pcb_checks)
		print("Schematic Checks is:")
		print(sch_checks)
	
	if "pcb" in config:
		print("PCB Checks is:")
		print(pcb_checks)
		checkPCB = True
		for key in config['pcb']:
			if key in pcb_checks:
				print("::warning::Field {} specified for ALL and PCB".format(key))
			else:
				pcb_checks[key] = config["pcb"][key]
		print("PCB Checks is:")
		print(pcb_checks)
						
	if "sch" in config:
		print("Schematic Checks is:")
		print(sch_checks)
		checkSCH = True
		for key in config['sch']:
			if key in sch_checks:
				print("::warning::Field {} specified for ALL and schematic".format(key))
			else:
				sch_checks[key] = config["sch"][key]
		print("Schematic Checks is:")
		print(sch_checks)
	
	if checkPCB:
		print("Checking PCBs for:")
		print(pcb_checks)
		
	if checkSCH:
		print("Checking schematics for:")
		print(sch_checks)

	pcbsToCheck = []
	schToCheck_v5 = []
	schToCheck_v6 = []

	if os.environ["INPUT_CHECK_ALL"] != "false":
		print("Checking all files in Repo")
		allFiles = list(Path(".").rglob("*.*"))
		for file in allFiles:
			if checkPCB and file.name.endswith(".kicad_pcb"):
				pcbsToCheck.append(str(file))
			elif checkSCH and file.name.endswith(".kicad_sch"):
				schToCheck_v6.append(str(file))
			elif checkSCH and file.name.endswith(".sch"):
				schToCheck_v5.append(str(file))
	else:
		print("Checking Changed Files")
		format = '--name-only'
		allFiles = []
		repo = git.Git(os.environ["GITHUB_WORKSPACE"])
		if isPR:
			diffed = repo.diff('origin/%s...origin/%s' % (prBase, prBranch), format).split('\n')
		else:
			diffed = repo.diff('%s...%s' % (fromHash, toHash), format).split('\n')
		for line in diffed:
			if len(line):
				allFiles.append(line)
		for file in allFiles:
			if checkPCB and file.endswith(".kicad_pcb"):
				pcbsToCheck.append(file)
			elif checkSCH and file.name.endswith(".kicad_sch"):
				schToCheck_v6.append(file)
			elif checkSCH and file.endswith(".sch"):
				schToCheck_v5.append(file)


	print("::endgroup::")

	if not pcbsToCheck:
		print("No PCBs to Check")
	else:
		print("::group::PCB Checks")

		for field in pcb_checks:
			if field not in fields:
				print("::warning file={}::Unknown PCB Field: {}".format(regexFile, field))
		
		## Turn the comments into something more useful
		pcbCommentRegex = []
		pcbCommentRegex.append("(.*)" if not "comment1" in pcb_checks else pcb_checks["comment1"])
		pcbCommentRegex.append("(.*)" if not "comment2" in pcb_checks else pcb_checks["comment2"])
		pcbCommentRegex.append("(.*)" if not "comment3" in pcb_checks else pcb_checks["comment3"])
		pcbCommentRegex.append("(.*)" if not "comment4" in pcb_checks else pcb_checks["comment4"])
		for file in pcbsToCheck:
			print("::group::{}".format(file))
			pcb = KicadPCB.load(file)
			pcbError = False
			for e in pcb.getError():
				print("::endgroup::")
				fail(file, "{}".format(e))
				pcbError = True
			
			if not pcbError:
				# Check Page
				if "title_block" in pcb:
					checkSExpBlock(pcb_checks, pcbCommentRegex, pcb, file)
					print("::endgroup::")
				else:
					print("::endgroup::")
					fail(file, "Title Block Not Found")
		print("::endgroup::")
		
	if not (schToCheck_v5 or schToCheck_v6):
		print("No Schematics to Check")
	else:
		print("::group::Schematic Checks")
		
		for field in sch_checks:
			if field not in fields:
				print("::warning file={}::Unknown Schematic Field: {}".format(regexFile, field))
				
		if schToCheck_v6:
			print("::group::{}".format(file))

			## Turn the comments into something more useful
			schCommentRegex = []
			schCommentRegex.append("(.*)" if not "comment1" in sch_checks else sch_checks["comment1"])
			schCommentRegex.append("(.*)" if not "comment2" in sch_checks else sch_checks["comment2"])
			schCommentRegex.append("(.*)" if not "comment3" in sch_checks else sch_checks["comment3"])
			schCommentRegex.append("(.*)" if not "comment4" in sch_checks else sch_checks["comment4"])
			for file in schToCheck_v6:
				print("::group::{}".format(file))
				sch = KicadSCH.load(file)
				schError = False
				for e in sch.getError():
					print("::endgroup::")
					fail(file, "{}".format(e))
					schError = True
				
				if not schError:
					# Check Page
					if "title_block" in sch:
						checkSExpBlock(sch_checks, schCommentRegex, sch, file)
						print("::endgroup::")
					else:
						print("::endgroup::")
						fail(file, "Title Block Not Found")
		
		if schToCheck_v5:
			schFieldMaps = {'title':'Title',
							'company':'Comp',
							'rev':'Rev',
							'date':'Date',
							'comment1':'Comment1',
							'comment2':'Comment2',
							'comment3':'Comment3',
							'comment4':'Comment4'}

			schExpectedFields = {}
			for field in fields:
				schExpectedFields[field] = False

			for field in sch_checks:
				if field in fields:
					schExpectedFields[field] = True
				else:
					print("::warning file={}::Unknown Schematic Field: {}".format(regexFile, field))

			for file in schToCheck_v5:
				print("::group::{}".format(file))

				thisCheck = schExpectedFields
				descrFound = False
				
				try:
					f = open(file, 'r')
				except OSError:
					fail(file, "Error Opening File")
					break;
				lines = f.readlines()
				for line in lines:
					if "$Descr" in line:
						descrFound = True
						if thisCheck['pageSize']:
							if not sch_checks["pageSize"] in line:
								fail(file, "Expected page size: {}, found: {}".format(sch_checks["pageSize"], line))
						thisCheck['pageSize'] = False
					elif "$EndDescr" in line:
						break
					elif descrFound:
						for field in thisCheck:
							if thisCheck[field]:
								if re.match("{} \"(.*)\"".format(schFieldMaps[field]), line):
									match = re.match("{} \"(.*)\"".format(schFieldMaps[field]), line)
									if not re.match(sch_checks[field], match.group(1)):
										fail(file, "{}: \"{}\", does not match: \"{}\"".format(field, match.group(1), sch_checks[field]))
									thisCheck[field] = False
									break
								
				# Make sure we found all we were looking for
				for field in schExpectedFields:
					if schExpectedFields[field]:
						fail(file, "Field {} Not Found in Schematic".format(field))
				
				f.close()
				print("::endgroup::")
		
		print("::endgroup::")

	print("::set-output name=fails::{}".format(failed))

	if failed:
		exit(1)

	print("All Checks Passed!")
	exit(0)


if __name__ == "__main__":
    main()