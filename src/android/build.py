"""Python routines to help build Android projects.

Implements the build process as outlined here:
    http://developer.android.com/guide/developing/building/index.html

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

import os, sys
import fnmatch
from os import path
import subprocess
import shutil


__all__ = ('AndroidProject',)


_DEBUG = False


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
        print [self.executable] + arguments
        if _DEBUG:
            return
        process = subprocess.Popen([self.executable] + arguments,
                                   stderr=subprocess.PIPE,
                                   stdout=subprocess.PIPE)
        process.wait()
        if process.returncode != 0:
            print process.stderr.read()
            print process.stdout.read()
            raise RuntimeError('%s: returned error code %s' % (
                " ".join([self.executable] + arguments),
                process.returncode))


class Aapt(Program):
    """Interface to the ``aapt`` tool used to package resources.
    """

    def __call__(self, command, manifest=None, resource_dir=None,
                 asset_dir=None, include=[], apk_output=None,
                 r_output=None, make_dirs=None, overwrite=None):
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
        for item in include:
            self.extend_args(args, ['-I', item])
        self.extend_args(args, ['-F', apk_output])
        self.extend_args(args, ['-J', r_output])
        Program.__call__(self, args)


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
        Program.__call__(self, args)


class JavaC(Program):
    """Interface to the Java command line compiler, ``javac``.
    """

    def __call__(self, files, destdir=None, encoding=None,
                 target=None, bootclasspath=None, debug=None):
        """
        files
            Files to be compiled (<source files>).

        destdir
            Where to place generated class files (-d).

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
        self.extend_args(args, ['-bootclasspath', bootclasspath])
        args.extend(['-g' if debug else '-g:none'])
        args.extend(files)
        Program.__call__(self, args)


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
        Program.__call__(self, args)


class ApkBuilder(Program):
    """Interface to the ``apkbuilder`` command line tool.

    The version of ``apkbuilder`` included with the Android SDK is
    currently deprecated, consult the README for information on where
    to find a version better suited to be used.
    """

    def __call__(self, outputfile, dex=None, zips=[], source_dirs=[]):
        """
        outputfile
            The APK file to create (<out archive>).

        dex
            The code of the app (optional if no code) (-f).

        zips
            List of zip archives to add (-z).

        source_dirs
            Adds the java resources found in that folder (-rf).
        """
        args = [outputfile]
        args.extend(['-u'])  # unsigned
        self.extend_args(args, ['-f', dex])
        for zip in zips:
            args.extend(['-z', zip])
        for source_dir in source_dirs:
            args.extend(['-rf', source_dir])
        Program.__call__(self, args)


class JarSigner(Program):
    """Interface to the ``jarsigner`` command line tool.
    """

    def __call__(self, jarfile, keystore, alias, password):
        args = []
        args.extend(['-keystore', keystore])
        args.extend(['-storepass', password])
        args.extend([jarfile])
        args.extend([alias])
        Program.__call__(self, args)


class ZipAlign(Program):
    """Interface to the ``zipalign`` command line tool.
    """

    def __call__(self, infile, outfile, align, force=None):
        args = []
        self.extend_args(args, ['-f'], force)
        args.extend(["%s" % align])
        args.extend([infile])
        args.extend([outfile])
        Program.__call__(self, args)


def get_target(sdk_path, target=None):
    """Return path and filename information for the given SDK target.

    If no target is given, the most recent target is chosen.

    The way these path's are officially constructed can be checked in
    ``com.android.sdklib.PlatformTarget`` and
    ``com.android.sdklib.SdkConstants``.
    """
    platforms = filter(lambda p: path.isdir(p),
                       map(lambda e: path.join(sdk_path, 'platforms', e),
                           os.listdir(path.join(sdk_path, 'platforms'))))
    # Gives us a dict like {'10': '/sdk/platforms/android-10'}
    platforms = dict([(p.rsplit('-', 1)[1], p) for p in platforms])
    if target:
        try:
            target_root = platforms[target]
        except KeyError:
            raise ValueError('target "%s" not found in "%s"' % (
                target, sdk_path))
    else:
        # Use the latest target - Python string sorting is smart
        # enough here to do the right thing.
        target_root = platforms[sorted(platforms.keys())[-1]]
    print target_root
    class Target(object):
        pass
    target = Target()
    target.framework_library = path.join(target_root, 'android.jar')
    target.framework_aidl = path.join(target_root, 'framework.aidl')
    target.aapt = path.join(sdk_path, 'platform-tools',
        'aapt.exe' if sys.platform=='win32' else 'aapt')
    target.aidl = path.join(sdk_path, 'platform-tools',
        'aidl.exe' if sys.platform=='win32' else 'aidl')
    target.dx = path.join(sdk_path, 'platform-tools',
        'dx.bat' if sys.platform=='win32' else 'dx')
    target.apkbuilder = path.join(sdk_path, 'tools',
        'apkbuilder.bat' if sys.platform=='win32' else 'apkbuilder')
    target.zipalign = path.join(sdk_path, 'tools',
        'zipalign.exe' if sys.platform=='win32' else 'zipalign')
    return target


def recursive_glob(treeroot, pattern):
    """From: http://stackoverflow.com/questions/2186525/2186639#2186639"""
    results = []
    for base, dirs, files in os.walk(treeroot):
        goodfiles = fnmatch.filter(files, pattern)
        results.extend(os.path.join(base, f) for f in goodfiles)
    return results


def mkdir(directory):
    if not path.exists(directory):
        os.mkdir(directory)


class AndroidProject(object):
    """Represents an Android project to be built.
    """

    # Can be used to define defaults.
    PATHS = {
        'sdk': None,
        'dx': None,
        'aapt': None,
        'aidl': None,
        'apkbuilder': None,
        'zipalign': None,
        'jarsigner': None,
        'javac': None,
    }

    def __init__(self, manifest, target=None, paths={}):
        # This is bascially what ``com.android.ant.SetupTask``
        # does in an Ant build (occasionally incorrectly
        # referenced as ``com.android.ant.AndroidInitTask``.
        config = self.PATHS.copy()
        config.update(paths)
        if not config['sdk']:
            raise ValueError('need Android SDK path')

        # Framework-specific paths
        self.target = target = get_target(config['sdk'], target)
        self.dx = Dx(config['dx'] or target.dx)
        self.aapt = Aapt(config['aapt'] or target.aapt)
        self.aidl = Aidl(config['aidl'] or target.aidl)
        self.zipalign = ZipAlign(config['zipalign'] or target.zipalign)
        self.apkbuilder = ApkBuilder(config['apkbuilder'] or target.apkbuilder)
        self.javac = JavaC(config['javac'] or 'javac')
        self.jarsigner = JarSigner(config['jarsigner'] or 'jarsigner')
        self.android_jar = self.target.framework_library
        self.framework_aidl = self.target.framework_aidl

        # Project-specific paths
        self.manifest = path.abspath(manifest)
        project_dir = path.dirname(self.manifest)
        self.resource_dir = path.join(project_dir, 'res')
        self.gen_dir = path.join(project_dir, 'gen')
        self.source_dir = path.join(project_dir, 'src')
        self.bin_dir = path.join(project_dir, 'bin')
        self.asset_dir = path.join(project_dir, 'asset')

    def make(self):
        """Shortcut to build everything into a final APK in one step.
        """
        # TODO: get basename from manifest file
        self.compile()
        self.package_res()
        apk = self.build_apk()
        return apk

    def compile(self):
        """Shortcut to get everything ready in order to start building
        APK files.

        Calls ``generate_java()`` and ``compile_java()`` and ``dex()``.
        """
        self.generate_java()
        self.compile_java()
        self.dex()

    def generate_java(self):
        """Shortcut to create all the auto-generated files so that
        we're ready to actually start compiling.

        Calls ``generate_r()`` and ``compile_aidl()``.
        """
        self.generate_r()
        self.compile_aidl()

    def generate_r(self):
        """Generate the R.java file.

        Final call will look something like this::

            $ aapt package -m -J gen/ -M AndroidManifest.xml -S res/
                -I android.jar
        """
        mkdir(self.gen_dir)
        self.aapt(
            command='package',
            make_dirs=True,
            manifest=self.manifest,
            resource_dir=self.resource_dir,
            r_output=self.gen_dir,
            include=[self.android_jar],)

    def compile_aidl(self):
        """Compile .aidl definitions into Java files.

        Final call will look something like this::

            $ aidl -pframework.aidl -Isrc/ -ogen/ Foo.aidl
        """
        for filename in recursive_glob(self.source_dir, '*.aidl'):
            self.aidl(
                filename,
                preprocessed=self.framework_aidl,
                search_path=self.source_dir,
                output_folder=self.gen_dir,
            )

    def compile_java(self, debug=False):
        files = recursive_glob(self.source_dir, '*.java')
        files += recursive_glob(self.gen_dir, '*.java')
        # TODO: check if files are up-to-date?
        # TODO: Include libs/*.jar as -classpath
        mkdir(self.bin_dir)
        classes_dir = path.join(self.bin_dir, 'classes')
        mkdir(classes_dir)
        self.javac(
            files,
            target='1.5',
            debug=debug,
            destdir=classes_dir,
            bootclasspath=self.android_jar)

    def dex(self):
        """Dexing is the process of converting Java bytecode to Dalvik
        bytecode.

        Final call will look somethin like this::

            $ dx --dex --output=bin/classes.dex bin/classes libs/*.jar
        """
        # TODO: Include libs/*.jar
        self.dx(
            [path.join(self.bin_dir, 'classes')],
            output=path.join(self.bin_dir, 'classes.dex'),
        )

    def package_res(self, configurations=None, output=None):
        """Package all the resource files.

        ``configurations`` may be a list of configuration values to be
        included. For example: "de" to make a German-only build, or
        "port,land,en_US". By default, all configurations are built.

            $ aapt package -f -M AndroidManifest.xml -S res/
                -A assets/ -I android.jar -F out/BASE-CONFIG.ap_
        """
        if not output:
            output = path.join(self.bin_dir, 'resources.ap_')
        kwargs = dict(
            command='package',
            overwrite=True,
            manifest=self.manifest,
            resource_dir=self.resource_dir,
            include=[self.android_jar],
            apk_output=output)
        if path.exists(self.asset_dir):
            kwargs['asset_dir'] = self.asset_dir
        self.aapt(**kwargs)

    def build_apk(self, resources=None, output=None):
        """Build an APK file, using the given resource package.
        """
        # TODO: Add libs/ (rj, nf options).
        if not resources:
            resources = path.join(self.bin_dir, 'resources.ap_')
        self.apkbuilder(
            outputfile=path.join(self.bin_dir, 'output.apk'),
            dex=path.join(self.bin_dir, 'classes.dex'),
            zips=[resources]
        )

    def sign(self, keystore, alias, password):
        """Sign an APK file.
        """
        self.jarsigner(
            path.join(self.bin_dir, 'output.apk'),
            keystore=keystore, alias=alias, password=password)

    def align(self, apk=None):
        """Align an APK file.
        """
        if not apk:
            apk = path.join(self.bin_dir, 'output.apk')
        temp = "%s.temp" % apk
        self.zipalign(apk, temp, align=4, force=True)
        os.rename(temp, apk)

    def clean(self):
        if path.exists(self.bin_dir):
            shutil.rmtree(self.bin_dir)
        if path.exists(self.bin_dir):
            shutil.rmtree(self.gen_dir)
