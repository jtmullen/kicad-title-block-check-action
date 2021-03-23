# kicad-title-block-check-action
An action to check the the title block on KiCad schematics and/or PCBs meet specified requirements. This can be used to enforce stylistic conventions for page size, titles, dates, revisions, etc. The action can only be run on a Pull Request or a push, otherwise it will fail. Currently, these requirements can be specified using regex.

*Please note: This is made for **KiCad v5** files, a v6 version will follow for the schematic file type update. Additionally, the KiCad file types are not very stricly defined so this operates on my understanding from the spec (which doesn't address title blocks much) and my experimentation. If you find KiCad behaviors I don't cover please open an issue! PRs are always welcome*

## Inputs
Both Inputs are Optional. 

### `check_all`
If you want to check all files in the repo, instead of just those changed on the PR/push. By default this is "false", change to "true" if you want all files checked. 

### `config_file`
This is the path to the config file for the check. By default it is `.github/title-blocks.yml`. Include a different path if you want to put the config file somewhere else. 

## Config File
The config File is a yml file that specifies the regex to use for the checks. For all fields, except page size, since they can be anything a user would type the action extracts the field and makes sure that it matches in entirely. For page size, since KiCad stores both the name and dimensions, the action just searches for the input in the field - you therefore can just specify the name such as "USLetter" or "A4". 

Any fields you leave out will not be checked - if you want a field to be empty you need to specify that. 

Specify the checks for `pcb`, `schematic`, or both depending on what you want check as shown below. Any of the top level keys (all, schematic, pcb) can be omitted. 

### Example Config File

```yml
all:
  pageSize: "USLetter"
  company: "Your Company"
  title: "(.+)"
  rev: "[0-9].[0-9]"
  date: "[0-9]{4}-(0[0-9]|1[0-2])-[0-3][0-9]"
schematic:
  comment1: "Schematic Designer: (.*)"
pcb:
  comment1: "Layout Designer: (.*)"
  comment2: ""
  comment3: ""
  comment4: "" 
```

The above config file would do the same checks for each, except for comments. Comment 1 differs in text between them. Comments 2-4 in the schematic could be anything, while in the pcb they would be enforced as empty. 

## Outputs
### `fails`
A comma separated list of files that failed the title block check.


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
      uses: jtmullen/kicad-title-block-check-action@v1-preview
```

You can also see [where this is used](https://github.com/search?l=YAML&q=kicad-title-block-check-action&type=Code)

*Note: this was developed for private repos, so it is in use in more places than will show above*

## TODOs
Potential improvements
- [ ] Use path and/or file names in checking
- [ ] Blacklist or Whitelist directories to check
- [ ] Add v6 schematic support
