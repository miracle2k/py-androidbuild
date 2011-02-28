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

Or::

    from android.build import AndroidProject
    project = AndroidProject(paths={'sdk': '/opt/android'})
    project.generate_r()
    project.compile_aidl()
    project.compile_java()
    project.dex()
    apk = project.build_apk(project.pack_resources())
    apk.sign()
    apk.align()
    project.clean()