#!/bin/sh -l

error () {
	echo "::error::$1"
	exit 1
}

REPO=`jq -r ".repository.full_name" "${GITHUB_EVENT_PATH}"`

if [[ $(jq -r ".pull_request.head.ref" "${GITHUB_EVENT_PATH}") != "null" ]]; then
	PR=`jq -r ".number" "${GITHUB_EVENT_PATH}"`
	TO_REF=`jq -r ".pull_request.head.ref" "${GITHUB_EVENT_PATH}"`
	FROM_REF=`jq -r ".pull_request.base.ref" "${GITHUB_EVENT_PATH}"`
	echo "Run for PR # ${PR} of ${TO_REF} into ${FROM_REF} on ${REPO}"
elif [[ $(jq -r ".after" "${GITHUB_EVENT_PATH}") != "null" ]]; then
	TO_REF=`jq -r ".after" "${GITHUB_EVENT_PATH}"`
	FROM_REF=`jq -r ".before" "${GITHUB_EVENT_PATH}"`
	BRANCH_NAME=`jq -r ".ref" "${GITHUB_EVENT_PATH}"`
	echo "Run for push of ${BRANCH_NAME} from ${FROM_REF} to ${TO_REF} on ${REPO}"
else
	error "Unknown Github Event Path"
fi

#cd "${GITHUB_WORKSPACE}" || die "Error: Cannot change directory to Github Workspace"

if [ "$INPUT_ONLYCHANGED" == "false" ]; then
	echo "Checking All Files"
	FILES_TO_CHECK=`find . -name '*.sch' -o -name '*.kicad_pcb'`
else
	echo "Checking Changed Files from ${FROM_REF} to ${TO_REF}"
	FILES_TO_CHECK=`git diff --name-only ${FROM_REF} ${TO_REF}`
fi

ret=0
failed=""

COUNT=0;
FAIL_COUNT=0;

## Handle failures. Input 1: File Name; Input 2: Expected value
fail () {
	failed="$failed$1"
	echo "::error file=$1::$2"
	FAIL_COUNT=$((FAIL_COUNT+1))
	ret=1
}

OPTIONAL_TITLE="0";
OPTIONAL_DATE="0";
OPTIONAL_REV="0";
OPTIONAL_COMP="0";
OPTIONAL_COMMENT1="0";
OPTIONAL_COMMENT2="0";
OPTIONAL_COMMENT3="0";
OPTIONAL_COMMENT4="0";

if [[ -z "${INPUT_PCBTITLEREGEX}" ]]; then	OPTIONAL_TITLE="1"; fi
if [[ -z "${INPUT_PCBDATEREGEX}" ]]; then	OPTIONAL_DATE="1"; fi
if [[ -z "$INPUT_PCBREVREGEX" ]]; then	OPTIONAL_REV="1"; fi
if [[ -z "$INPUT_PCBCOMPREGEX" ]]; then	OPTIONAL_COMP="1"; fi
if [[ -z "$INPUT_PCBCOMMENT1REGEX" ]]; then	OPTIONAL_COMMENT1="1"; fi
if [[ -z "$INPUT_PCBCOMMENT2REGEX" ]]; then	OPTIONAL_COMMENT2="1"; fi
if [[ -z "$INPUT_PCBCOMMENT3REGEX" ]]; then	OPTIONAL_COMMENT3="1"; fi
if [[ -z "$INPUT_PCBCOMMENT4REGEX" ]]; then	OPTIONAL_COMMENT4="1"; fi


for file in $FILES_TO_CHECK
do
	
	## Schematic Files
	if [[ (${file: -4} == ".sch") && ("${INPUT_CHECKSCHEMATICS}" == "true") ]]; then
		COUNT=$((COUNT+1))
		echo "Checking Schematic $file..."
		awk '
			BEGIN{ lastLine=0; pass=0; failedAt="";}
			/\$Descr '"$INPUT_SCHPAGESIZEREGEX"' (.*)/ { lastLine=1; next;}
			/encoding (.*)/ { if( lastLine == 1){lastLine = 2; next;}else{failedAt="Encoding";exit}}
			/Sheet (.*)/ { if( lastLine == 2){lastLine = 3;	next;}else{failedAt="Sheet";exit}}
			/Title \"'"$INPUT_SCHTITLEREGEX"'\"/ {if( lastLine == 3){lastLine = 4; next;}else{failedAt="Title";exit}}
			/Date \"'"$INPUT_SCHDATEREGEX"'\"/ { if( lastLine == 4){lastLine = 5; next;}else{failedAt="Date";exit}}
			/Rev \"'"$INPUT_SCHREVREGEX"'\"/ { if( lastLine == 5){lastLine = 6; next;}else{failedAt="Rev";exit}}
			/Comp \"'"$INPUT_SCHCOMPREGEX"'\"/ { if( lastLine == 6){lastLine = 7; next;}else{failedAt="Company";exit}}
			/Comment1 \"'"$INPUT_SCHCOMMENT1REGEX"'\"/ { if( lastLine == 7){lastLine = 8; next;}else{failedAt="Comment 1";exit}}
			/Comment2 \"'"$INPUT_SCHCOMMENT2REGEX"'\"/ { if( lastLine == 8){lastLine = 9; next;}else{failedAt="Comment 2";exit}}
			/Comment3 \"'"$INPUT_SCHCOMMENT3REGEX"'\"/ { if( lastLine == 9){lastLine = 10; next;}else{failedAt="Comment 3";exit}}
			/Comment4 \"'"$INPUT_SCHCOMMENT4REGEX"'\"/ { if( lastLine == 10){lastLine = 11; next;}else{failedAt="Comment 4"; exit;}}
			/\$EndDescr/ {if( lastLine == 11){pass=1; exit}else{failedAt="Unexpected EndDescr";exit;}}
			/\$EndSCHEMATC/ {failedAt="No Title Block Found or Bad Page Size"; exit}
			/(.*)/ {lastLine = 0}
			END{if(pass){exit 0}else{print "Error Before: ", failedAt; exit 1}} ' "$file" || fail "$file" "Schematic"
	
	## PCB Files
	elif [[ (${file: -10} == ".kicad_pcb") && ("${INPUT_CHECKPCBS}" == "true") ]]; then
		COUNT=$((COUNT+1))
		echo "Checking PCB $file..."
		awk '
			BEGIN{ pageSize=0; titleBlock=0; title=0; date=0; rev=0; company=0; comment1=0; comment2=0; comment3=0; comment4=0; }
			/[\r\n\t\f\v *]\)/ {if (titleBlock) { exit }}
			/[\r\n\t\f\v *]\(page '"$INPUT_PCBPAGESIZEREGEX"'\)/ { pageSize = 1; next;}
			/[\r\n\t\f\v *]\(title_block/ { titleBlock = 1; next;}
			/[\r\n\t\f\v *]\(title \"?'"$INPUT_PCBTITLEREGEX"'\"?\)/ { if(titleBlock){title = 1;}; next;}
			/[\r\n\t\f\v *]\(date '"$INPUT_PCBDATEREGEX"'\)/ { if(titleBlock){date = 1; next;}}
			/[\r\n\t\f\v *]\(rev \"?'"$INPUT_PCBREVREGEX"'\"?\)/ { if(titleBlock){rev = 1; next;}}
			/[\r\n\t\f\v *]\(company \"?'"$INPUT_PCBCOMPREGEX"'\"?\)/ { if(titleBlock){company = 1; next;}}
			/[\r\n\t\f\v *]\(comment 1 \"?'"$INPUT_PCBCOMMENT1REGEX"'\"?\)/ { if(titleBlock){comment1 = 1; next;}}
			/[\r\n\t\f\v *]\(comment 2 \"?'"$INPUT_PCBCOMMENT2REGEX"'\"?\)/ { if(titleBlock){comment2 = 1; next;}}
			/[\r\n\t\f\v *]\(comment 3 \"?'"$INPUT_PCBCOMMENT3REGEX"'\"?\)/ { if(titleBlock){comment3 = 1; next;}}
			/[\r\n\t\f\v *]\(comment 4 \"?'"$INPUT_PCBCOMMENT4REGEX"'\"?\)/ { if(titleBlock){comment4 = 1; next;}}
			END{if (pageSize && titleBlock && (title || '"$OPTIONAL_TITLE"') && (date || '"$OPTIONAL_DATE"') && (rev || '"$OPTIONAL_REV"') && (company || '"$OPTIONAL_COMP"') && (comment1 || '"$OPTIONAL_COMMENT1"') && (comment2 || '"$OPTIONAL_COMMENT2"') && (comment3 || '"$OPTIONAL_COMMENT3"') && (comment4 || '"$OPTIONAL_COMMENT4"')) { exit 0 } else {exit 1 }}' "$file" || fail "$file" "PCB"
	fi
	
done


if [ $ret -eq 0 ]; then
	echo "All checked files meet title block requirements!"
fi
if [ $COUNT -eq 0 ]; then
	PERCENT=100
else
	PASS_COUNT=$((COUNT-FAIL_COUNT))
	PERCENT=$(((100*PASS_COUNT)/COUNT))
fi
echo "::set-output name=fails::$failed"
echo "::set-output name=percent::$PERCENT"

exit $ret
