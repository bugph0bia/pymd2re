pymd2re
===

![Software Version](http://img.shields.io/badge/Version-v0.1.0-green.svg?style=flat)
![Python Version](http://img.shields.io/badge/Python-3.6-blue.svg?style=flat)
[![MIT License](http://img.shields.io/badge/license-MIT-blue.svg?style=flat)](LICENSE)

## Overview
Convert Markdown file to Re:VIEW file. (Markdown parser is included.)

## Version
v0.1.0

## Requirements
- Python 3.6 or later.
- - No dependent libraries other than the standard library.

## License
MIT License

## Usage
Run `pymd2re.py`.

    usage: pymd2re.py [-h] input_path output_path
    
    Convert Markdown file to Re:VIEW file.
    
    positional arguments:
      input_path     Input File Path. (Markdown file)
      output_path    Output File Path. (Re:VIEW file)
    
    optional arguments:
      -h, --help     show this help message and exit

## Samples
- Output results from `pymd2re.py`.
    - Input file : [sample_input.md](sample/sample_input.md)
    - Output file : [sample_output.re](sample/sample_output.re)
    - Warning during conversion : [warning_stdout.txt](sample/warning_stdout.txt)
- Visualization of intermediate data with `debug.py`.
    - Input file : [sample_input.md](sample/sample_input.md)
    - Contribution content : [debug_stdout.txt](sample/debug_stdout.txt)

## Restrictions
- Cases in which multiple types of blocks exist on the same line are not allowed.
    - Cases where a multi-line comment starts in the middle of a line, for example.
    - Multiple types of inline elements on the same line are allowed.

## Memo
- Parsing was implemented using regular expressions.
- The document structure is maintained as an intermediate representation.
    - It is assumed that output to formats other than Re:VIEW is possible if a separate renderer is prepared.
