import re


modifiers = ['public', 'static', 'final', 'protected', 'private']

class JavaClass:

  '''
  Seek a line containing the begin marker and then return the
  new advanced line pointer as well as the index the next char
  right after the begin marker
  '''
  @staticmethod
  def seek_line(contents, line_pointer, line_matcher):

    marker = None
    curr = None
    while True:
      curr = contents[line_pointer].strip()
      [matched, matchMarker] = line_matcher(curr)

      if matched:
        marker = matchMarker
        break

      line_pointer += 1

      # Cannot go any further
      if line_pointer == len(contents):
        return [line_pointer, line_pointer]


    return [line_pointer, curr.index(marker) + len(marker)]

  '''
  Simplifies a field declaration down to it's type
  '''
  @staticmethod
  def simplify_field(line):
    kwords = line.split(' ')

    # Not interested in any static members
    if 'static' in kwords:
      return None

    # pop all modifier keywords
    while len(kwords) > 0 and kwords[0] in modifiers:
      kwords.pop(0)

    while len(kwords) > 0 and kwords[0].startswith('@'):
      kwords.pop(0)

    # Truncate after (including) = on direct assignments
    if '=' in kwords:
      kwords = kwords[:kwords.index('=')]

    if (len(kwords)) == 0:
      return None

    # Splice off last word (field name)
    return ' '.join(kwords[:-1])

  '''
  Matches a constructor declaration, either without any
  modifiers or with any prepended modifier
  '''
  @staticmethod
  def constructor_matcher(class_name, line):
    curr = f'{class_name}('
    if line.startswith(curr):
      return [True, curr]

    for modifier in modifiers:
      curr = f'{modifier} {class_name}('
      if curr in line:
        return [True, curr]

    return [False, None]

  def __init__(self, path, contents):
    self.contents = contents
    self.path = path
    self.not_a_class = False

    # Parse package
    [line_pointer, offs] = JavaClass.seek_line(contents, 0, lambda line: ['package' in line, 'package'])
    curr = contents[line_pointer]
    self.package = curr[offs + 1:curr.index(';', offs + 2)]

    # Parse class name
    [line_pointer, offs] = JavaClass.seek_line(contents, 0, lambda line: ['class' in line, 'class'])

    # Could not locate class name
    if line_pointer == len(contents):
      self.not_a_class = True
      return

    curr = contents[line_pointer]
    self.class_name = curr[offs + 1:curr.index(' ', offs + 2)]

    # Cannot be a class, as it's identifier is invalid
    # The class keyword must've come from somewhere else
    if re.match(r'^([a-zA-Z_$][a-zA-Z\d_$]*)$', self.class_name) is None:
      self.not_a_class = True
      return

    # Field area starts on the next line
    field_area_start = line_pointer + 1

    # Go till constructor
    [line_pointer, offs] = JavaClass.seek_line(contents, line_pointer, lambda line: JavaClass.constructor_matcher(self.class_name, line))

    self.fields = []

    # Loop lines of field area
    brackets = 0
    for i in range (field_area_start, line_pointer):
      line = contents[i].strip()

      if line == '':
        continue

      # This line opens/closes codeblock(s)
      if '{' in line or '}' in line:
        for c in line:
          if c == '{':
            brackets += 1
          if c == '}':
            brackets -= 1

        # Skip current line
        continue

      # Only look at fields while not in any code-blocks
      if brackets == 0:
        field = JavaClass.simplify_field(line)
        if field != None:
          self.fields.append(field)

  def __str__(self):
    return self.package + '.' + self.class_name + ' -> ' + ', '.join(self.fields) + '\n  at ' + self.path