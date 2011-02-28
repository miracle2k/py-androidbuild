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


**NOTE: This is currently a work in progress. The API isn't finalized.
The examples below may not work as is.**


Example::

    from android.build import AndroidProject

    project = AndroidProject('AndroidManifest.xml', sdk_dir='/opt/android')
    apk = project.build()
    apk.sign('keystore', 'alias', 'name')
    apk.align()


Or::

    from android.build import AndroidProject

    project = AndroidProject('AndroidManifest.xml', sdk_dir='/opt/android')
    for lang in ('de', 'en', 'fr'):
        for density in ('mdpi', 'hdpi',):
            project.build('%s-%s.apk' % (lang, density),
                          config='%s,%s' % (lang, density))

Rather than using on the default project layout that ``AndroidProject``
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
