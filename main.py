from kicad_parser import KicadPCB
import yaml
import re
import os
import json
from pathlib import Path
from git import Repo

checkPCB = False
checkSCH = False
failed = ""
GITHUB_WORKSPACE="test"

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

print("::group::Set Up")

try:
	os.chdir(GITHUB_WORKSPACE)
except OSError:
	error("Could not change to GitHub Workspace")

regexFile = "labeler.yml"

try:
	stream = open(regexFile, 'r')
except OSError:
	error("Could not open the Config File at: {}".format(regexFile))

try:
	config = yaml.safe_load(stream)
except yaml.YAMLError:
	error("Could not parse the yaml config file")

repo = Repo('''C:/Users/Jonathan/repos/personal/kicad-title-block-check-action''')
print(repo.git.diff("python_rewrite", "master"))
error("Done")

if "pcb" in config:
	checkPCB = True
	print("Checking PCBs for:")
	pcb_checks = config['pcb']
	print(pcb_checks)
	
if "schematic" in config:
	checkSCH = True
	print("Checking schematics for:")
	sch_checks = config['schematic']
	print(sch_checks)

pcbsToCheck = []
schToCheck = []

allFiles = list(Path(".").rglob("*.*"))

for file in allFiles:
	if checkPCB and ".kicad_pcb" in file.name:
		pcbsToCheck.append(file.name)
	elif checkSCH and ".sch" in file.name:
		schToCheck.append(file.name)

	
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
			
			for field in ["title", "rev", "company", "date"]:
				if field in pcb_checks:
					if field in pcb.title_block:
						if not re.match(pcb_checks[field], pcb.title_block[field].strip("\"")):
							fail(file, "{}: {}, does not match {}".format(field, pcb.title_block[field], pcb_checks[field])) 
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
					fail(file, "Comment {}: {}, does not match {}".format(i+1, comments[i], pcbCommentRegex[i]))
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

#fields = ['pageSize','title','company','rev','date','comment1','comment2','comment3','comment4']
	for file in schToCheck:
		print("Checking Schematic: {}".format(file))

		thisCheck = schExpectedFields
		descrFound = False
		f = open(file, 'r')
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
						if match := re.match("{} \"(.*)\"".format(schFieldMaps[field]), line):
							if not re.match(sch_checks[field], match.group(1)):
								fail(file, "{}: {}, does not match: {}".format(field, match.group(1), sch_checks[field]))
							thisCheck[field] = False
							break
						
		# Make sure we found all we were looking for
		for field in schExpectedFields:
			if schExpectedFields[field]:
				fail(file, "Field {} Not Found in Schematic".format(field))
			
	print("::endgroup::")
