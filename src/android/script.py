"""
Copyright (c) 2011 Michael Elsdoerfer <michael@elsdoerfer.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import sys
from os import path
import logging

from build import AndroidProject, ProgramFailedError, LOGGER_NAME


def main(argv):
     scriptname = path.basename(sys.argv[0])
     if len(argv) != 1:
          print "Builds the Android project in the current directory."
          print "Usage: %s PATH_TO_SDK" % scriptname
          return 1

     # Setup logging
     log = logging.getLogger(LOGGER_NAME)
     sh = logging.StreamHandler()
     sh.setFormatter(logging.Formatter("> %(message)s"))
     log.addHandler(sh)

     p = AndroidProject('AndroidManifest.xml', sdk_dir=argv[0])
     try:
          apk = p.build()

          keystore = path.expanduser('~/.android/debug.keystore')
          if path.exists(keystore):
               print "Signing with debug key..."
               apk.sign(keystore, 'androiddebugkey', 'android')
               apk.align()
          else:
               print "Note: Package will be unsigned!"

          print "Created: %s" % apk.filename
     except ProgramFailedError, e:
          print u"ERROR: %s" % unicode(e)
          print
          if e.stdout:
               print "STDOUT"
               print "------"
               print e.stdout
          if e.stderr:
               print "STDERR"
               print "------"
               print e.stderr


def run():
     sys.exit(main(sys.argv[1:]) or 0)


if __name__ == '__main__':
    run()