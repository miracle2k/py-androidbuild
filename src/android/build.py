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

import os, sys
import time
import fnmatch
from os import path
import shutil
import tempfile
import logging

from tools import *


__all__ = ('AndroidProject', 'PlatformTarget', 'get_platform',
           'ProgramFailedError')


# Setup a logger for this library.
LOGGER_NAME = 'py-androidbuild'
log = logging.getLogger(LOGGER_NAME)
log.setLevel(logging.INFO)
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
log.addHandler(NullHandler())


class File(object):
    """To provide a common delete() method for subclasses.
    """

    def __init__(self, filename):
        self.filename = filename

    def delete(self):
        os.unlink(self.filename)

    def __repr__(self):
        return '%s <%s>' % (self.__class__.__name__, self.filename)


class CodeObj(File):
    """Represents a .dex code file.
    """


class ResourceObj(File):
    """Represents a packed resource package."""


class Apk(File):
    """Represents an APK file.

    Because apk.align() is just so nice as an API."""

    def __init__(self, platform, filename):
        File.__init__(self, filename)
        self.platform = platform

    def sign(self, *a, **kw):
        return self.platform.sign(self, *a, **kw)

    def align(self, *a, **kw):
        return self.platform.align(self, *a, **kw)


class PlatformTarget(object):
    """Represents a specific platform version provided by the
    Android SDK, and knows how to build Android projects targeting
    this platform.

    The tools and files we need to use as part of the build process
    are partly different in each version.
    """

    def __init__(self, version, sdk_dir, ndk_dir, platform_dir, custom_paths={}):
        self.version = version
        self.sdk_dir = sdk_dir
        self.platform_dir = platform_dir

        # The way these path's are officially constructed can be checked
        # in ``com.android.sdklib.PlatformTarget`` and
        # ``com.android.sdklib.SdkConstants``.
        paths = dict(
            aapt =path.join(sdk_dir, 'platform-tools',
                'aapt.exe' if sys.platform=='win32' else 'aapt'),
            aidl = path.join(sdk_dir, 'platform-tools',
                'aidl.exe' if sys.platform=='win32' else 'aidl'),
            llvmrs = path.join(sdk_dir, 'platform-tools',
                'llvm-rs-cc.exe' if sys.platform=='win32' else 'llvm-rs-cc'),
            dx = path.join(sdk_dir, 'platform-tools',
                'dx.bat' if sys.platform=='win32' else 'dx'),
            apkbuilder = path.join(sdk_dir, 'tools',
                'apkbuilder.bat' if sys.platform=='win32' else 'apkbuilder'),
            zipalign = path.join(sdk_dir, 'tools',
                'zipalign.exe' if sys.platform=='win32' else 'zipalign'),
            jarsigner = 'jarsigner',
            javac = 'javac',
        )

        if ndk_dir is not None:
            paths['ndk_build'] = path.join(ndk_dir, 'ndk-build.bat' if sys.platform=="win32" else 'ndk-build')

        paths.update(custom_paths)

        self.dx = Dx(paths['dx'])
        self.aapt = Aapt(paths['aapt'])
        self.aidl = Aidl(paths['aidl'])
        self.llvmRs = LlvmRs(paths['llvmrs'])
        self.zipalign = ZipAlign(paths['zipalign'])
        self.apkbuilder = ApkBuilder(paths['apkbuilder'])
        self.javac = JavaC(paths['javac'])
        if ndk_dir is not None:
            self.ndk_build = NdkBuild(paths['ndk_build'])
            self.ndk_clean = NdkClean(paths['ndk_build'])
        else:
            self.ndk_build = None
            self.ndk_clean = None
        self.jarsigner = JarSigner(paths['jarsigner'])

        self.framework_library = path.join(platform_dir, 'android.jar')
        self.framework_aidl = path.join(platform_dir, 'framework.aidl')
        self.rs_includes = [
            path.join(sdk_dir, 'platform-tools/renderscript/include'),
            path.join(sdk_dir, 'platform-tools/renderscript/clang-include')]

    def __repr__(self):
        return 'Platform %s <%s>' % (self.version, self.platform_dir)

    def generate_r(self, manifest, resource_dir, output_dir):
        """Generate the R.java file in ``output_dir``, based
        on ``resource_dir``.

        Final call will look something like this::

            $ aapt package -m -J gen/ -M AndroidManifest.xml -S res/
                -I android.jar
        """
        mkdir(output_dir)
        log.info(self.aapt(
            command='package',
            make_dirs=True,
            manifest=manifest,
            resource_dir=resource_dir,
            r_output=output_dir,
            include=[self.framework_library]))

    def compile_renderscript(self, resource_dir, source_gen_dir, source_dirs):
        """
        compile renderscript files before aapt packaging
        build all rs files in source_dirs
        put cc files in res/raw and java files in gen
        """
        files_list = list()
        for filename in recursive_glob(source_dirs, '*.rs'):
            files_list.append(filename)
        #don't try to build renderscript if there is no rs files
        if len(files_list) <= 0:
            return
        log.info(self.llvmRs(
                    path.join(resource_dir, 'raw'),
                    source_gen_dir,
                    files_list,
                    self.rs_includes
                ))

    def compile_aidl(self, source_dirs, output_dir):
        """Compile .aidl definitions found in ``source_dirs`` into
        Java files, and put them into ``output_dir``.

        Final calls will look something like this::

            $ aidl -pframework.aidl -Isrc/ -ogen/ Foo.aidl
        """
        for filename in recursive_glob(source_dirs, '*.aidl'):
            log.info(self.aidl(
                filename,
                preprocessed=self.framework_aidl,
                search_path=source_dirs,
                output_folder=output_dir,
            ))

    def _collect_jars(self, paths):
        jar_files = []
        for item in paths:
            if path.isdir(item):
                jar_files += recursive_glob(item, '*.jar')
            else:
                jar_files.append(item)
        return jar_files

    def compile_java(self, source_dirs, output_dir, extra_jars=[],
                     debug=False, target='1.5'):
        """Compile all *.java files in ``source_dirs`` (a list of
        directories) and store the class files in ``output_dir``.

        ``extra_jars`` will be added to the classpath. The list may
        include both .jar files as well as directories, which will
        recursively be searched for .jar files.
        """
        # Collect all files to be compiled
        source_files = recursive_glob(source_dirs, '*.java')
        jar_files = self._collect_jars(extra_jars)
        # TODO: check if files are up-to-date?
        mkdir(output_dir, True)
        log.info(self.javac(
            source_files,
            target=target,
            debug=debug,
            destdir=output_dir,
            classpath=jar_files,
            bootclasspath=self.framework_library))

    def compile_native(self, project_dir):
        """Shortcut for building native code
        """
        log.info(self.ndk_build(
            project_dir,
        ))
        self.ndk_build(project_dir)

    def clean_native(self, project_dir):
        """Shortcut for cleaning native code
        """
        log.info(self.ndk_clean(
            project_dir,
        ))
        self.ndk_clean(project_dir)

    def dex(self, source_dir, output=None, extra_jars=[]):
        """Dexing is the process of converting Java bytecode to Dalvik
        bytecode.

        Will process all class files in ``source_dir`` and store the
        result in a single file ``output``.

        Final call will look somethin like this::

            $ dx --dex --output=bin/classes.dex bin/classes libs/*.jar
        """
        if not output:
            _, output = tempfile.mkstemp(suffix='.dex')
        output = path.abspath(output)
        jar_files = self._collect_jars(extra_jars)
        log.info(self.dx([source_dir] + jar_files, output=output))
        return CodeObj(output)

    def compile(self, manifest, project_dir, source_dirs, resource_dir,
                source_gen_dir=None, class_gen_dir=None,
                dex_output=None, extra_jars=[], **kwargs):
        """Shortcut for the whole process until dexing into a code
        object that we can pack into an APK.

        For directories that you do not specifiy a tenmporary directory
        will be used and deleted after the build.
        """
        to_delete = []
        if not source_gen_dir:
            source_gen_dir = tempfile.mkdtemp()
            to_delete.append(source_gen_dir)
        if not class_gen_dir:
            class_gen_dir = tempfile.mkdtemp()
            to_delete.append(class_gen_dir)
        try:
            source_dirs = as_list(source_dirs)
            self.compile_renderscript(resource_dir, source_gen_dir, source_dirs)
            self.generate_r(manifest, resource_dir, source_gen_dir)
            # TODO: check args for RS
            self.compile_aidl(source_dirs, source_gen_dir)
            if self.ndk_build is not None:
                self.compile_native(project_dir)
            self.compile_java(source_dirs+ [source_gen_dir],
                              class_gen_dir, extra_jars=extra_jars,
                              **kwargs)
            return self.dex(class_gen_dir, output=dex_output,
                            extra_jars=extra_jars)
        finally:
            for d in to_delete:
                log.info('Deleting tree: %s' % d)
                shutil.rmtree(d)

    def pack_resources(self, manifest, resource_dir, asset_dir=None,
                       configurations=None, package_name=None,
                       version_code=None, version_name=None, output=None):
        """Package all the resource files.

        ``configurations`` may be a list of configuration values to be
        included. For example: "de" to make a German-only build, or
        "port,land,en_US". By default, all configurations are built.

            $ aapt package -f -M AndroidManifest.xml -S res/
                -A assets/ -I android.jar -F out/BASE-CONFIG.ap_
        """
        if not output:
            _, output = tempfile.mkstemp(suffix='.ap_')
        output = path.abspath(output)
        kwargs = dict(
            command='package',
            manifest=manifest,
            resource_dir=resource_dir,
            include=[self.framework_library],
            apk_output=output,
            configurations=configurations,
            rename_manifest_package=package_name,
            overwrite_version_code=version_code,
            overwrite_version_name=version_name,
            # There is no error code without overwrite, so
            # let's not even give the user the choice, it
            # would only cause confusion.
            overwrite=True)
        if asset_dir:
            kwargs['asset_dir'] = asset_dir
        log.info(self.aapt(**kwargs))
        return ResourceObj(output)

    def build_apk(self, output, code=None, resources=None,
                  jar_paths=[], native_dirs=[], source_dirs=[]):
        """Build an APK file, using the given code and resource files.
        """
        output = path.abspath(output)
        kwargs = dict(outputfile=output, jar_paths=jar_paths,
                      native_dirs=native_dirs, source_dirs=source_dirs)
        if code:
            kwargs['dex'] = code.filename \
                  if isinstance(code, CodeObj) else code
        if resources:
            kwargs['zips'] = [resources.filename \
                  if isinstance(resources, ResourceObj) else resources]
        log.info(self.apkbuilder(**kwargs))
        return Apk(self, output)

    def sign(self, apk, keystore, alias, password):
        """Sign an APK file.
        """
        log.info(self.jarsigner(
            apk.filename if isinstance(apk, Apk) else apk,
            keystore=keystore, alias=alias, password=password))

    def align(self, apk, output=None):
        """Align an APK file.

        If ``outfile`` is not given, the APK is align in place.
        """
        infile = apk.filename if isinstance(apk, Apk) else apk
        if not output:
            # Or should tempfile be used? Might be on another
            # filesystem though.
            outfile = "%s.align.%s" % (infile, time.time())
        log.info(self.zipalign(infile, outfile, align=4, force=True))

        if not output:
            # In-place align was requested, return the original file
            log.info('Renaming %s to %s' % (outfile, infile))
            os.rename(outfile, infile)
            return apk
        else:
            # Return a new APK.
            return Apk(self, outfile)


def get_platform(sdk_path, ndk_dir, target=None):
    """Return path and filename information for the given SDK target.

    If no target is given, the most recent target is chosen.
    """
    #check ig sdk folder contains platforms folder
    if path.exists(path.join(sdk_path, 'platforms')) == False:
        raise ValueError("sdk path is wrong")

    platforms = filter(lambda p: path.isdir(p),
                       map(lambda e: path.join(sdk_path, 'platforms', e),
                           os.listdir(path.join(sdk_path, 'platforms'))))
    # Gives us a dict like {'10': '/sdk/platforms/android-10'}
    platforms = dict([(p.rsplit('-', 1)[1], p) for p in platforms])

    if not target:
        # Use the latest target - Python string sorting is smart
        # enough here to do the right thing.
        target = sorted(platforms.keys())[-1]

    try:
        target_root = platforms[target]
    except KeyError:
        raise ValueError('target "%s" not found in "%s"' % (
            target, sdk_path))

    return PlatformTarget(target, sdk_path, ndk_dir, target_root)


def recursive_glob(treeroot, pattern):
    """From: http://stackoverflow.com/questions/2186525/2186639#2186639

    ``treeroot`` can be a list of multiple directory should be searched.
    """
    results = []
    for root in as_list(treeroot):
        for base, dirs, files in os.walk(root):
            goodfiles = fnmatch.filter(files, pattern)
            results.extend(os.path.join(base, f) for f in goodfiles)
    return results


def mkdir(directory, recursive=False):
    if not path.exists(directory):
        if recursive:
            os.makedirs(directory)
        else:
            os.mkdir(directory)


def only_existing(paths):
    """Return only those paths that actually exists."""
    return filter(lambda p: path.exists(p), paths)


def as_list(o):
    """Returns `o` as the only element in a list if it isn't already a list
    or tuple.
    """
    if not isinstance(o, (list, tuple)):
        return [o]
    return o


class AndroidProject(object):
    """Represents an Android project to be built.

    This provides a more high-level approach than working with
    ``PlatformTarget`` directly, by making some default assumptions
    as to directory layout and file locations.

    Specifically, given the location of the project base directory
    it will:

        - assume sources under ./src
        - assume resources under ./res
        - assume raw assets under ./assets
        - use ./gen for generated code, like R.java
        - use ./out for final files
        - include .jar files under ./lib

    If you don't specify a project directory explicitly, the location
    of your ``AndroidManifest.xml`` file is used. The ability to
    specify a project directory manually becomes helpful when you
    want to rewrite your manifest file before the build, in particular
    because Android's ``aapt`` currently (SDK 4.0) does not support
    manifest files that are not named ``AndroidManifest.xml``.

    Additionally, this class considers the following instance
    attributes:

        ``extra_source_dirs``
             Specify additional source code directories as a list.

        ``extra_jars``
             Specify additional jar files, that you do not want to
             place within ./lib. You'll use this to reference things
             like the Android Compatibility Support Libraries.

    When constructing a ``AndroidProject`` instance, you either need to
    pass a platform that you have aquired yourself using ``get_platform``,
    or you need to give the path to the Android SDK in ``sdk_dir``.
    Additionally, you may specify an Android API level to build against
    via ``target``. If not given, the ``android:targetSdkVersion`` attribute
    from your manifest will be automatically used. If no such attribute
    exists, the most recent API level in your SDK will be used.
    """

    def __init__(self, manifest, name=None, platform=None, sdk_dir=None,
                 ndk_dir=None, target=None, project_dir=None):
        if not platform:
            if not sdk_dir:
                raise ValueError('You need to provide the SDK path, '
                                 'or a PlatformTarget instance.')
            platform = get_platform(sdk_dir, ndk_dir, target)
            
        self.platform = platform

        self.ndk_dir = ndk_dir

        # Project-specific paths
        self.manifest = path.abspath(manifest)
        self.project_dir = path.dirname(self.manifest)
        self.resource_dir = path.join(self.project_dir, 'res')
        self.gen_dir = path.join(self.project_dir, 'gen')
        self.source_dir = path.join(self.project_dir, 'src')
        self.out_dir = path.join(self.project_dir, 'bin')
        self.asset_dir = path.join(self.project_dir, 'assets')
        self.lib_dir = path.join(self.project_dir, 'libs')
        self.obj_dir = path.join(self.project_dir, 'obj/local')

        # Retrieve platform
        if not platform:
            if not sdk_dir:
                raise ValueError('You need to provide the SDK path, '
                                 'or a PlatformTarget instance.')
            if target is None:
                target = self.manifest_parsed.find('uses-sdk')\
                    .attrib['{http://schemas.android.com/apk/res/android}targetSdkVersion']
            platform = get_platform(sdk_dir, target)

        self.platform = platform

        # Optional values
        self.extra_source_dirs = []
        self.extra_jars = []

        # if no name is given, inspect the manifest
        self.name = name or self.manifest_parsed.attrib['package']

    @property
    def manifest_parsed(self):
        if not hasattr(self, '_parsed_manifest'):
            from xml.etree import ElementTree
            self._parsed_manifest = ElementTree.parse(self.manifest)
        return self._parsed_manifest.getroot()

    def compile(self):
        """Force a recompile of the project.
        """
        kwargs = dict(
            dex_output=path.join(self.out_dir, 'classes.dex'),
            manifest=self.manifest,
            project_dir = self.project_dir,
            source_dirs=[self.source_dir] + self.extra_source_dirs,
            resource_dir=self.resource_dir,
            source_gen_dir=self.gen_dir,
            class_gen_dir=path.join(self.out_dir, 'classes'),
            extra_jars=only_existing([self.lib_dir])+self.extra_jars
        )
        self.code = self.platform.compile(**kwargs)

    def build(self, output=None, config=None, package_name=None,
              version_code=None, version_name=None):
        """Shortcut to build everything into a final APK in one step.

        ``package_name`` and ``version`` can be used to change these
        properties without needing to modify the AndroidManifest.xml
        file.
        """
        # Make sure the code is compiled
        if not hasattr(self, 'code'):
            self.compile()

        # Package the resources
        if not config:
            resource_filename = path.join(
                self.out_dir, '%s.ap_' % (self.name))
        else:
            resource_filename = path.join(
                self.out_dir, '%s.%s.ap_' % (self.name, config))
        kwargs = dict(
            manifest=self.manifest,
            resource_dir=self.resource_dir,
            configurations=config,
            output=resource_filename,
            package_name=package_name,
            version_code=version_code,
            version_name=version_name,
        )
        if path.exists(self.asset_dir):
            kwargs.update({'asset_dir': self.asset_dir})
        resources = self.platform.pack_resources(**kwargs)

        # Put everything into an APK.
        if not output:
            output = path.join(self.out_dir, '%s.apk' % self.name)
        apk = self.platform.build_apk(
            output,
            code=self.code, resources=resources,
            jar_paths=only_existing([self.lib_dir])+self.extra_jars,
            native_dirs=only_existing([self.lib_dir]),
            source_dirs=only_existing([self.source_dir]))
        return apk

    def clean(self):
        """Deletes both ``self.out_dir`` and ``self.gen_dir``.
        Deletes also libs and obj contents (ndk)
        """
        if path.exists(self.out_dir):
            shutil.rmtree(self.out_dir)
        if path.exists(self.gen_dir):
            shutil.rmtree(self.gen_dir)
        if self.platform.ndk_clean:
            self.platform.clean_native(self.project_dir)
