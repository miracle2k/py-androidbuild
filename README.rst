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
    project = AndroidProject(paths={'sdk': '/opt/android'})
    project.make()


Or::

    from android.build import AndroidProject
    project = AndroidProject(paths={'sdk': '/opt/android'})
    try:
        project.compile()
        for configuration in configurations:
            res = project.pack_resources(configuration)
            apk = project.build_apk(res)
            apk.sign()
            apk.align()
    finally:
        project.clean()


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