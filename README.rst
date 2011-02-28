Python routines to build Android projects
-----------------------------------------

This is a simple Python module to help you build Android projects. It
exists because I can't stand Ant.

This is not a standalone build tool, but a collection of routines with
which you can build your Android project in Python, or a Python-based
tool like fabric.

Tested with Android SDK 2.3 (older versions might not work).

Android's build process, that is, what this module implements, is outlined
here in detail:

    http://developer.android.com/guide/developing/building/index.html#detailed-build


Usage
~~~~~

The simplest case will look something like this:

    from android.build import AndroidProject

    project = AndroidProject('AndroidManifest.xml', sdk_dir='/opt/android')
    apk = project.build()
    apk.sign('keystore', 'alias', 'name')
    apk.align()


The ``AndroidProject`` class assumes a default Android directory layout,
that is it espects to find things like a ``./res`` and a ``./src``
directory next to the ``AndroidManifest.xml``.


Or::

    from android.build import AndroidProject

    project = AndroidProject('AndroidManifest.xml', sdk_dir='/opt/android')
    try:
        for version in ('free', 'pay'):
            # You may want to hard-exclude certain code so it can't just be
            # re-enabled, or whatever you need to do.
            make_adjustments_for_version(version)

            # Recompile the code.
            project.compile()

            # For each version, build different configurations.
            # In the end, you'll have 12 apk files.
            for lang in ('de', 'en', 'fr'):
                for density in ('mdpi', 'hdpi',):
                    project.build('%s-%s-%s.apk' % (version, lang, density),
                                  config='%s,%s' % (lang, density))
    finally:
        project.clean()


Rather than relying on the default project layout that ``AndroidProject``
assumes, you can also use a more low-level API::

    platform = get_platform('/opt/android/sdk', target='10')
    code = platform.compile('AndroidManifest.xml', 'src', 'res')
    res = platform.pack_resources('AndroidManifest.xml', 'res')
    apk = p.build_apk('unsigned-unaligned.apk', code, res)
    code.delete()
    res.delete()


Should it become necessary, you are also free to do things even more
low-level than that. What follows is a quick overview of all the
APIs used during a build::

    platform = get_platform('/opt/android/sdk', target='10')
    platform.generate_r(...)
    platform.compile_aidl(...)
    platform.compile_java(...)
    platform.dex(...)
    platform.package_resources(...)
    platform.build_apk(...)
    platform.sign(...)
    platform.align(...)


Stand-alone script
-----------------

If you've downloaded the source to an Android application which lacks
an Ant build script, and you don't want to go through the whole process
of installing it into Eclipse, you can do:

    $ py-androidbuild SDK_DIR

This will build the project in the current directory.


Known Issues
~~~~~~~~~~~~

Some things still need to be done - mostly because I never used the
functionality in question. If you do need them, consider submitting
a patch: The Android build process isn't that complicated, and so those
things should be easy to implement.

- Renderscript in Honeycomb requires additional build steps that are
  not yet implemented.

- Including native libraries is probably yet supported, but at the very
  least untested.
