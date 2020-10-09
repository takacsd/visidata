from visidata import *

def open_rec(p):
    return RecIndexSheet(p.name, source=p)

def get_multiline(line, fp):
    'Parse *line* and lookahead into *fp* as iterator for continuing lines.  Return (multiline, next_line) where *multiline* can contain newlines and *next_line is the line after the combined *multiline*.  Handle "\\" at end and "+" at beginning of lines.  *next_line* will be None iff iterator is exhausted.'
    while True:
        try:
            next_line = next(fp)
        except StopIteration:
            return line, None

        if line.endswith('\\'):
            line = line[:-1] + next_line
        elif next_line.startswith('+'):
            # strip leading r'+ ?'
            next_line = next_line[2:] if next_line.startswith('+ ') else next_line[1:]
            line += '\n' + next_line
        else:
            return line, next_line

def get_kv(line):
    return re.split(r':[ \t]?', line, maxsplit=1)

class RecSheet(TableSheet):
    def addColumn(self, c, index=None):
        super().addColumn(c, index=index)
        self.colnames[c.name] = c

RecSheet.init('colnames', dict)

class RecIndexSheet(IndexSheet):
    def iterload(self):
        sheet = None
        row = None
        newRecord = True
        name = None
        next_line = ''
        comments = []

        fp = iter(self.source)
        while next_line is not None:
            line, next_line = get_multiline(next_line, fp)
            line = line.lstrip()

            if not line:  # end of record separator
                newRecord = True
                continue

            elif line[0] == '#':
                comments.append(line)
                continue

            if not sheet or (newRecord and line[0] == '%'):
                sheet = RecSheet('', columns=[], rows=[], source=self, comments=comments)
                comments = []
                yield sheet
                newRecord = False

            if line[0] == '%':
                desc, rest = get_kv(line[1:])
                if desc == 'rec':
                    sheet.name = rest
                elif desc in 'mandatory allowed':
                    for colname in rest.split():
                        sheet.addColumn(ItemColumn(colname))
                elif desc in ['key', 'unique']:
                    for i, colname in enumerate(rest.split()):
                        sheet.addColumn(ItemColumn(colname, keycol=i+1))
                elif desc in ['sort']:
                    sheet.orderBy([sheet.column(colname) for colname in rest.split()])
                elif desc in ['type', 'typedef']:
                    pass
                elif desc in ['auto']:  # autoincrement columns should be present already
                    pass
                elif desc in ['size', 'constraint']:  # ignore constraints
                    pass
                elif desc in ['confidential']:  # encrypted
                    pass
                else:
                    vd.warning('Unhandled descriptor: ' +line)
            else:
                if newRecord:
                    row = None
                    newRecord = False

                if not row:
                    row = {}
                    sheet.addRow(row)

                name, rest = get_kv(line)
                if name not in sheet.colnames:
                    sheet.addColumn(ColumnItem(name))

                if name in row:
                    if not isinstance(row[name], list):
                        row[name] = [row[name]]
                    row[name].append(rest)
                else:
                    row[name] = rest

        for sheet in Progress(self.rows):
            sheet.sort()
