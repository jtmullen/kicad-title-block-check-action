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

def error(cause):
	print("::error::{}".format(cause))
	exit(1)
	
def fail(fileName, cause):
	global failed
	print("::error file={}::{}".format(fileName, cause))
	if not fileName in failed:
		failed += fileName
		failed += ","

def main():
	print("::group::Set Up")
	print("Python Version: {}".format(sys.version))

	try:
		from kicad_parser import KicadPCB
	except ImportError:
		error("Error importing KiCad PCB Dependency")

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
	
	if "all" in config:
		checkPCB = True
		checkSCH = True
		pcb_checks = sch_checks = config['all']
	
	if "pcb" in config:
		checkPCB = True
		for key in config['pcb']:
			if key in pcb_checks:
				print("::warning file={}::Field {} specified for ALL and PCB", key)
			else:
				pcb_checks[key] = config[pcb][key]
						
	if "schematic" in config:
		checkSCH = True
		for key in config['sch']:
			if key in sch_checks:
				print("::warning file={}::Field {} specified for ALL and sch", key)
			else:
				sch_checks[key] = config[sch][key]
	
	if checkPCB:
		print("Checking PCBs for:")
		pcb_checks = config['pcb']
		print(pcb_checks)
		
	if checkSCH:
		print("Checking schematics for:")
		sch_checks = config['schematic']
		print(sch_checks)

	pcbsToCheck = []
	schToCheck = []

	if os.environ["INPUT_CHECK_ALL"] != "false":
		print("Checking all files in Repo")
		allFiles = list(Path(".").rglob("*.*"))
		for file in allFiles:
			if checkPCB and file.name.endswith(".kicad_pcb"):
				pcbsToCheck.append(str(file))
			elif checkSCH and file.name.endswith(".sch"):
				schToCheck.append(str(file))
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
			elif checkSCH and file.endswith(".sch"):
				schToCheck.append(file)


	print("::endgroup::")

	if not pcbsToCheck:
		print("No PCBs to Check")
	else:
		print("::group::PCB Checks")

		for field in pcb_checks:
			if field not in fields:
				print("::warning file={}::Unknown PCB Field: {}".format(regexFile, field))

		pcbCommentRegex = []
		pcbCommentRegex.append("(.*)" if not "comment1" in pcb_checks else pcb_checks["comment1"])
		pcbCommentRegex.append("(.*)" if not "comment2" in pcb_checks else pcb_checks["comment2"])
		pcbCommentRegex.append("(.*)" if not "comment3" in pcb_checks else pcb_checks["comment3"])
		pcbCommentRegex.append("(.*)" if not "comment4" in pcb_checks else pcb_checks["comment4"])
		for file in pcbsToCheck:
			print("Checking PCB: {}".format(file))

			pcb = KicadPCB.load(file)

			pcbError = False
			for e in pcb.getError():
				fail(file, "{}".format(e))
				pcbError = True
			
			if not pcbError:
				# Check Page
				if "pageSize" in pcb_checks:
					if "page" in pcb:
						page = pcb.page
						if not pcb_checks["pageSize"] in page:
							fail(file, "Expected Page Size {}, found {}".format(pcb_checks["pageSize"], page))
					else:
						fail(file, "Page size not found")
				
				if "title_block" in pcb:
					for field in ["title", "rev", "company", "date"]:
						if field in pcb_checks:
							if field in pcb.title_block:
								if not re.match(pcb_checks[field], pcb.title_block[field].strip("\"")):
									fail(file, "{}: \"{}\", does not match \"{}\"".format(field, pcb.title_block[field], pcb_checks[field])) 
							else:
								fail(file, "{} not found, expected match: {}".format(field, pcb_checks[field]))
				
					comments = ["", "", "", ""]
					
					if "comment" in pcb.title_block:
						pcbComments = pcb.title_block.comment
						if isinstance(pcbComments, list):
							comments[pcbComments[0]-1] = pcbComments[1]
						else:
							for item in pcbComments:
								comments[item[0]-1] = item[1]
								
					for i in range(0,4):
						if not re.match(pcbCommentRegex[i], comments[i].strip("\"")):
							fail(file, "Comment {}: \"{}\", does not match \"{}\"".format(i+1, comments[i], pcbCommentRegex[i]))
				else:
					fail(file, "Title Block Not Found")
		print("::endgroup::")
		
	if not schToCheck:
		print("No Schematics to Check")
	else:
		print("::group::Schematic Checks")
		
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

		for file in schToCheck:
			print("Checking Schematic: {}".format(file))

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

	print("::set-output name=fails::{}".format(failed))

	if failed:
		exit(1)

	print("All Checks Passed!")
	exit(0)


if __name__ == "__main__":
    main()