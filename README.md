# kicad-title-block-check-action
An action to check the the title block on KiCad schematics and/or PCBs meet specified requirements. This can be used to enforce functional or stylistic conventions for page size, titles, dates, revisions, etc. to ensure information is present and consistent across your organization. These requirements are specified with regular expressions. The action can be run on a PR and/or a push. Supports KiCad v5 & v6 formats.  

*Please note: KiCad File Type Formats are not very strictly designed, especially for title blocks and for v5 schematics. I have relied on some of my own experimentation to determine what is allowed, it is possible I have missed some edge cases. If you find one feel free to submit an issue or PR!*

## Inputs
Both Inputs are Optional, the defaults should be good for many use cases. 

### `check_all`
If you want to check all files in the repo, instead of just those changed on the PR/push. By default this is "false", change to "true" if you want all files checked. 

### `config_file`
This is the path to the config file for the check. By default it is `.github/title-blocks.yml`. Include a different path if you want to put the config file somewhere else. 

## Config File
The config File is a yml file that specifies the regex to use for the checks. For all fields, except page size, since they can be anything a user would type the action extracts the field and makes sure that it matches in entirely. For page size, since KiCad stores both the name and dimensions, the action just searches for the input in the field - you therefore can just specify the name such as "USLetter" or "A4". 

Any fields you leave out will not be checked - if you want a field to be empty you need to specify that. 

Specify the checks for `pcb`, `sch`, or both depending on what you want check as shown below. Any of the top level keys (all, sch, pcb) can be omitted. 

### Example Config File

```yml
all:
  pageSize: "USLetter"
  company: "Your Company"
  title: "(.+)"
  rev: "[0-9].[0-9]"
  date: "[0-9]{4}-(0[0-9]|1[0-2])-[0-3][0-9]"
sch:
  comment1: "Schematic Designer: (.*)"
pcb:
  comment1: "Layout Designer: (.*)"
  comment4: "^$" 
```

The above config file would do the same checks for each, except for comments. Comment 1 differs in text between them. Comments 4 would be forced to be empty in the pcb. Other comments would be unchecked. 

## Outputs
### `fails`
A comma separated list of files that failed the title block check. Includes a trailing comma. For example: `"test/kicad_files/test.kicad_sch,test/kicad_files/test.sch,"`


## Usage
To add this action to your repo create a workflow file (such as `.github/workflows/check-title-blocks.yml`) with the following content adjusted for your needs. The following example checks the changed files to make sure they have the company name and use US Letter page size.

```yml
name: check-kicad-title-blocks

on: [push, pull_request]

jobs:
  check-title-blocks:
    name: Check Title Blocks
    runs-on: ubuntu-latest
    steps:
    - name: Checkout
      uses: actions/checkout@v2
      with:
        fetch-depth: 0
    - name: Check Title Blocks
      uses: jtmullen/kicad-title-block-check-action@v2
```

You can also see [where this is used](https://github.com/search?l=YAML&q=kicad-title-block-check-action&type=Code)

*Note: this was developed for private repos, so it is in use in more places than will show above*

## TODOs
Potential improvements
- [ ] Use path and/or file names in checking
- [ ] Blacklist or Whitelist directories to check
