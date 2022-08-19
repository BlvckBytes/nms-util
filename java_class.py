class JavaClass:

  '''
  Seek a line containing the begin marker and then return the
  new advanced line pointer as well as the index the next char
  right after the begin marker
  '''
  @staticmethod
  def seek_line(contents, line_pointer, begin_marker):

    curr = None
    while True:
      curr = contents[line_pointer].strip()
      if begin_marker in curr:
        break
      line_pointer += 1

    return [line_pointer, curr.index(begin_marker) + len(begin_marker)]

  def __init__(self, contents):
    self.contents = contents

    # Parse package
    [line_pointer, offs] = JavaClass.seek_line(contents, 0, 'package')
    curr = contents[line_pointer]
    self.package = curr[offs + 1:curr.index(';', offs + 2)]

    # Parse class name
    [line_pointer, offs] = JavaClass.seek_line(contents, line_pointer, 'class')
    curr = contents[line_pointer]
    self.class_name = curr[offs + 1:curr.index(' ', offs + 2)]

  def __str__(self):
    return self.package + "." + self.class_name