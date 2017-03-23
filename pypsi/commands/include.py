#
# Copyright (c) 2015, Adam Meily <meily.adam@gmail.com>
# Pypsi - https://github.com/ameily/pypsi
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#

from pypsi.core import Command, PypsiArgParser, CommandShortCircuit
from pypsi.utils import safe_open
from pypsi.completers import path_completer
import os


class IncludeFile(object):

    def __init__(self, path, line=1):
        self.name = os.path.basename(path)
        self.abspath = os.path.abspath(path)
        self.line = line
        self.ifile = None
        self.lines = []


class IncludeCommand(Command):
    '''
    Execute a script file. This entails reading each line of the given file and
    processing it as if it were typed into the shell.
    '''

    def __init__(self, name='include', topic='shell',
                 brief='execute a script file', **kwargs):
        self.parser = PypsiArgParser(
            prog=name,
            description=brief
        )

        self.parser.add_argument(
            'path', metavar='PATH', action='store', help='file to execute'
        )

        super(IncludeCommand, self).__init__(
            name=name, topic=topic, brief=brief,
            usage=self.parser.format_help(), **kwargs
        )
        self.stack = []

    def complete(self, shell, args, prefix):
        return path_completer(args[-1])

    def run(self, shell, args):
        try:
            ns = self.parser.parse_args(args)
        except CommandShortCircuit as e:
            return e.code

        return self.include_file(shell, ns.path)

    def include_file(self, shell, path):
        fp = None
        self.ifile = IncludeFile(path)

        if self.stack:
            for i in self.stack:
                if i.abspath == self.ifile.abspath:
                    self.error(shell, "recursive include for file ",
                               self.ifile.abspath, '\n')
                    return -1

        self.stack.append(self.ifile)

        try:
            fp = safe_open(path, 'r')
        except (OSError, IOError) as e:
            self.error(shell, "error opening file ", path, ": ", str(e), '\n')
            self.stack.pop()
            return -1

        try:
            self.lines = [line for line in fp]
        except UnicodeDecodeError as e:
            # If line could not be read, file may be binary, so don't execute
            self.error(shell, 'An error occurred reading the file: ', e)
            return -1

        try:
            line = self.get_next_line()
            while line:
                shell.execute(line, input=self.get_next_line)
                line = self.get_next_line()
        except Exception as e:
            self.error(shell,
                       'An error occurred on line ', self.ifile.line, ': ', e)
            return -1

        # Cleanup
        self.ifile = None
        self.lines = []
        self.stack.pop()
        fp.close()

        return 0

    def get_next_line(self, *args):
        line = self.ifile.line - 1
        self.ifile.line += 1
        try:
            return self.lines[line]
        except:
            return None
