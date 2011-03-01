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

import subprocess


__all__ = ('ProgramFailedError', 'Aapt', 'Aidl', 'ApkBuilder',
           'Dx', 'JarSigner', 'JavaC', 'ZipAlign',)


class ProgramFailedError(RuntimeError):
    """Holds information about the failure.
    """

    def __init__(self, cmdline, returncode, stdout=None, stderr=None):
        if isinstance(cmdline, (tuple, list)):
            cmdline = " ".join(cmdline)
        self.cmdline = cmdline
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    @property
    def message(self):
        return self.__str__()

    def __unicode__(self):
        return u'%s failed with code %s' % (
            self.cmdline, self.returncode)

    def __str__(self):
        return self.__unicode__().encode('ascii', '?')


class Program(object):

    def __init__(self, executable):
        self.executable = executable

    def extend_args(self, args, new, condition=True):
        """Helper which will extend the argument list ``args``
        with the list ``new``, but only if ``new`` contains
        no ``None`` items, and only if a specifiied ``condition``
        is ``True``.
        """
        if not None in new and condition:
            args.extend(new)

    def __repr__(self):
        return '%s <%s>' % (
            self.__class__.__name__, repr(self.executable))

    def __call__(self, arguments):
        """Note that this returns the command line that was executed,
        so it can be logged.

        Child implementations must not forget to pass this return value
        along to their caller.
        """
        cmdline = " ".join([self.executable] + arguments)
        process = subprocess.Popen([self.executable] + arguments,
                                   stderr=subprocess.PIPE,
                                   stdout=subprocess.PIPE)
        process.wait()
        if process.returncode != 0:
            raise ProgramFailedError(
                cmdline,
                process.returncode, process.stderr.read(),
                process.stdout.read())

        return cmdline


class Aapt(Program):
    """Interface to the ``aapt`` tool used to package resources.
    """

    def __call__(self, command, manifest=None, resource_dir=None,
                 asset_dir=None, include=[], apk_output=None,
                 r_output=None, configurations=None,
                 rename_manifest_package=None, overwrite_version_code=None,
                 overwrite_version_name=None,
                 make_dirs=None, overwrite=None):
        """
        command
            The APPT command to execute.

        manifest
            AndroidManifest.xml to include in zip (-M).

        resource_dir
            Directory in which to find resources (-S).

        asset_dir
            Additional directory in which to find raw asset files (-A).

        include
            List of packages to include in the base set (-I).

        apk_output
            The apk file to output (-F).

        r_output
            Where to output R.java resource constant definitions (-J).

        make_dirs
            Make package directories for ``r_output`` option (-m).
        """

        args = [command]
        self.extend_args(args, ['-m'], make_dirs)
        self.extend_args(args, ['-M', manifest])
        self.extend_args(args, ['-S', resource_dir])
        self.extend_args(args, ['-A', asset_dir])
        self.extend_args(args, ['-c', configurations])
        self.extend_args(
            args, ['--version-code', "%s" % overwrite_version_code])
        self.extend_args(args, ['--version-code', overwrite_version_name])
        self.extend_args(
            args, ['--rename-manifest-package', rename_manifest_package])
        for item in include:
            self.extend_args(args, ['-I', item])
        self.extend_args(args, ['-F', apk_output])
        self.extend_args(args, ['-J', r_output])
        self.extend_args(args, ['-f'], overwrite)
        return Program.__call__(self, args)


class Aidl(Program):
    """Interface to the ``aidl`` tool used to compile .aidl files.
    """

    def __call__(self, aidl_file, preprocessed=None, search_path=None,
                 output_folder=None):
        """
        aidl_file
            An aidl interface file (INPUT).

        preprocessed
            File created by --preprocess to import (-p).

        search_path
            Search path for import statements (-I).

        output_folder
            Base output folder for generated files (-o).
        """
        args = []
        self.extend_args(args, ['-p%s' % preprocessed], preprocessed)
        self.extend_args(args, ['-I%s' % search_path], search_path)
        self.extend_args(args, ['-o%s' % output_folder], output_folder)
        self.extend_args(args, [aidl_file])
        return Program.__call__(self, args)


class JavaC(Program):
    """Interface to the Java command line compiler, ``javac``.
    """

    def __call__(self, files, destdir=None, encoding=None,
                 target=None, classpath=[], bootclasspath=None,
                 debug=None):
        """
        files
            Files to be compiled (<source files>).

        destdir
            Where to place generated class files (-d).

        classpath
            Where to find user class files and annotation
            processors (-classpath). Expected to be a list.

        bootclasspath
            Location of bootstrap class files (-bootclasspath).

        encoding
            Character encoding used by source files (-encoding).

        target
            Generate class files for specific VM version (-target).
        """
        args = []
        self.extend_args(args, ['-encoding', encoding])
        self.extend_args(args, ['-target', target])
        self.extend_args(args, ['-source', target])
        self.extend_args(args, ['-d', destdir])
        self.extend_args(
            args, ['-classpath', ":".join(classpath)], classpath)
        self.extend_args(args, ['-bootclasspath', bootclasspath])
        args.extend(['-g' if debug else '-g:none'])
        args.extend(files)
        return Program.__call__(self, args)


class Dx(Program):
    """Interface to the ``dx`` command line tool which converts Java
    bytecode to Android's Dalvik bytecode.
    """

    def __call__(self, files, output=None):
        """
        files
            A set of class files, .zip/.jar/.apk archives or
            directories.

        output
            Target output file (--output).
        """
        args = ['--dex']
        self.extend_args(args, ["--output=%s" % output])
        args.extend(files)
        return Program.__call__(self, args)


class ApkBuilder(Program):
    """Interface to the ``apkbuilder`` command line tool.

    The version of ``apkbuilder`` included with the Android SDK is
    currently deprecated, consult the README for information on where
    to find a version better suited to be used.
    """

    def __call__(self, outputfile, dex=None, zips=[], source_dirs=[],
                 jar_paths=[], native_dirs=[]):
        """
        outputfile
            The APK file to create (<out archive>).

        dex
            The code of the app (optional if no code) (-f).

        zips
            List of zip archives to add (-z).

        source_dirs
            Adds the java resources found in that folder (-rf).

        jar_paths
            List of jar files or folders containing jar files to add (-rj).

        native_dirs
            List of folders containing native libraries to add (-nf).
        """
        args = [outputfile]
        args.extend(['-u'])  # unsigned
        self.extend_args(args, ['-f', dex])
        for zip in zips:
            args.extend(['-z', zip])
        for source_dir in source_dirs:
            args.extend(['-rf', source_dir])
        for item in jar_paths:
            args.extend(['-rj', item])
        for item in native_dirs:
            args.extend(['-nf', item])
        return Program.__call__(self, args)


class JarSigner(Program):
    """Interface to the ``jarsigner`` command line tool.
    """

    def __call__(self, jarfile, keystore, alias, password):
        args = []
        args.extend(['-keystore', keystore])
        args.extend(['-storepass', password])
        args.extend([jarfile])
        args.extend([alias])
        return Program.__call__(self, args)


class ZipAlign(Program):
    """Interface to the ``zipalign`` command line tool.
    """

    def __call__(self, infile, outfile, align, force=None):
        args = []
        self.extend_args(args, ['-f'], force)
        args.extend(["%s" % align])
        args.extend([infile])
        args.extend([outfile])
        return Program.__call__(self, args)