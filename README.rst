Pyinclude - text preprocessor
===================================

Text preprocessor for use in comments

Console usage:

    usage: pyinclude [-h] [--version] [--encoding [ENCODING]] [--quiet [QUIET]]
                     [--out FILE] [--start_end START END]
                     [--exclude_start_end START END]
                     [--definition VARS [VARS ...]]
                     FILE

    Text preprocessor for use in comments

    positional arguments:
      FILE                  Enter point preprocessor FILE

    optional arguments:
      -h, --help            show this help message and exit
      --version, -v         show program's version number and exit
      --encoding [ENCODING], --charset [ENCODING], -ch [ENCODING], -scs [ENCODING]
                            Work files encoding
      --quiet [QUIET], -q [QUIET]
                            No questions
      --out FILE, -o FILE   Out file
      --start_end START END, -se START END
                            Start and end of used blocks
      --exclude_start_end START END, -ese START END
                            Start and end of excluded blocks
      --definition VARS [VARS ...], -D VARS [VARS ...]
                            Add macros

    pyinclude 0.1.0a0 Copyright 2018, SigDev
