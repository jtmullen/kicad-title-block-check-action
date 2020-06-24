# kicad-title-block-check-action
An action to check the the title block on KiCad schematics and/or PCBs meet specified requirements.
Currently, these requirements can only be specified using regex, however in the future it may allow requirements based on the things such as the file or directory name. 

*Please note: This is made for **KiCad v5** files. Additionally, the KiCad file types are not very stricly defined so this operates on my understanding from the spec (which doesn't address title blocks much) and my experimentation. If you find KiCad behaviors I don't cover please open an issue! Patches are always welcome*

## Inputs
*All* inputs to this action are optional. So just include the ones you care about! If you don't include any it will just check that your files have title blocks I suppose. 
### `onlyChanged`
Whether this action should check all files or just those changed in the this PR or Push. Defaults to false. Set to anything else (`true` would make the most sense) to only check changed files.

### `checkSchematics`
Whether to check schematic files. Defaults to true. Change to anything else (`false` would make the most sense) to not check schematics.

### `checkPCBs`
Whether to check PCB files. Defaults to true. Change to anything else (`false` would make the most sense) to not check PCBs.

### Regex Inputs
The following inputs set the regex for each of the fields. The field must be given a `sch` or `pcb` prefix which indicates if it is the regex for the schematic or PCB. So, for example, the `TitleRegex` should be used as `schTitleRegex` and/or `pcbTitleRegex`.

The Schematic ones default to `'(.*)'` allowing anything while the PCB ones default to `''`. This difference is because the schematic file includes the empty fields while the PCB leaves it out. 

#### `PageSizeRegex`
Page Size Field
#### `TitleRegex`
Title Field
#### `DateRegex`
Date Field
#### `RevRegex`
Revision Field
#### `CompRegex`
Company Field
#### `CommentXRegex`
Comment Fields for X [1..4]

## Outputs
### `fails`
A list of files that failed the title block check.

### `percent`
The percent of checked files that passed the title block check.

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
        - name: Check Title Blocks
          uses: jtmullen/kicad-title-block-check-action@v0.1-beta
          with:
            onlyChanged: true
            schPageSizeRegex: "US Letter"
            schCompRegex: "Company Name"
            pcbPageSizeRegex: "US Letter"
            pcbCompRegex: "Company Name"


You can also see [where this is used](https://github.com/search?l=YAML&q=kicad-title-block-check-action&type=Code)

*Note: this was developed for several private repos so many uses will not be listed above*

## TODOs
Potential improvements
- [ ] Allow inputs to be used in both sch and pcb
- [ ] Use path and/or file names in checking
- [ ] Blacklist or Whitelist directories to check
- [ ] Check first line of file for KiCad version
