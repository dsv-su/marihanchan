marihanchan
===========

_a git cloning utility for deployment systems_

_"make me a ~~sandwich~~ project!"_


what is this?
-------------
_todo: write_

most basic usage:
```shell
    ./marihanchan.py --project <project>
```

requirements
------------

 - Python 2.7 or later (marihanchan was built and tested on 2.7, to be as broadly compatible as
 possible)
 - GitPython - a python library used to interact with git repositories
(http://pythonhosted.org/GitPython, marihanchan was built on GitPython 0.3.2 RC1)


usage
-----

the marihan tool has a couple flags that can be set, a few of which is required. the different
flags that are recognized are:
```shell
# the build-file flag, tells marihanchan where to look up projects (this defaults to
# a file called 'build.json', located in the same folder as the running script)
./marihanchan.py -b (--buildfile) <build-file>
```

```shell
# the project flag (which is required). this tells marihanchan what project it should
# build/update
./marihanchan.py -p (--project) <project>
```

```shell
# the directory flag. note that this will override any 'root' set in
# the target project
./marihanchan.py -p (--project) <project> -d (--directory) /var/www/mysite
```

```shell
# the update flag, which will make marihanchan try to go through an existing project and update
# it. 
./marihanchan.py -p (--project) <project> -d (--directory) /var/www/mysite -u (--update)
```


the build-file
--------------

marihanchan needs a build-file in order to function. this works sort of like a central library,
in which the different projects that can be built are defined. a build-file is written
in JSON, and either needs to be explicitly supplied via cli arguments when running the script
or placed in the same directory as the main script. note that if you opt for the latter, then
the build-file needs to also be named "build.json" (this might be handled nicer-ly in later
versions of the script)

a basic build-file example:
```json
{
  "drupal_base": {
    "rootDir": "drupal",
    "components": {
      "drupal": {
        "repo": "https://github.com/drupal/drupal.git",
        "branch": "7.x"
      }
    }
  },

  "dsv_base": {
    "rootDir": "dsv_base",
    "requires": [ "drupal_base" ],
    "components": {
      "views": {
        "repo": "git://git.drupal.org/project/views.git",
        "branch": "7.x-3.x",
        "tag": "7.x-3.8",
        "path": "sites/all/components/views"
      }
    }
  },

  "dsv_theme": {
    "components": {
      "jquery_update": {
        "repo": "git://git.drupal.org/project/jquery_update.git",
        "branch": "7.x-2.x",
        "tag": "7.x-2.4",
        "path": "sites/all/components/contrib/jquery_update"
      },
      "bootstrap": {
        "repo": "http://git.drupal.org/project/bootstrap.git",
        "branch": "7.x-3.x",
        "path": "sites/all/themes/contrib/bootstrap"
      },
      "drupal_theme_next": {
        "repo": "https://github.com/dsv-su/drupal_theme_next.git",
        "path": "sites/all/themes/custom/drupal_theme_next"
      }
    }
  }

  "dsv_forms": {
    "rootDir": "forms",
    "requires": [ "dsv_base", "dsv_theme" ],
    "components": {
      "webforms": {
        "repo": "http://git.drupal.org/project/webform.git",
        "branch": "7.x-3.x",
        "tag": "7.x-3.20",
        "path": "sites/all/components/contrib/webforms"
      }
    }
  }
}
```


defining a project
------------------

in the example above, there are 3 projects: "drupal_base", "dsv_base", and "dsv_forms".
a project is defined by a key (the name of the project) and a JSON object (the properties
of the project). projects can have 3 different properties:

 - 'rootDir' = a simple string telling marihan if the project should be put in a specific
    folder in the installation path
 - 'requires' = what other project(s) this project requires
 - 'components' = the different components of this project

first of all: all of these aren't needed. actually, none of them are. it is fully
possible to define a project like this:

```json
{
  "empty_project": {}
}
```

the above project will (of course..) result in absolutely nothing being done. but that
isn't very interesting, now is it? let's instead explain what marihan does with the
information.

the "rootDir" of the project is the location where marihan will put it. this could be
either just nothing (would clone into the execution dir) or any absolute or relative
path within the system. please note that marihan always uses the rootDir of the top-most
project only, so if you have a project with no rootDir in it - none of the dependencies will
change this fact and the project will be cloned into the current working dir.

the "rqeuires" property tells marihan what other projects this current one depends on. in
the example above, the "dsv_forms" project depends on the "dsv_base", which in turn depends
on "drupal_base". marihan will always build in a recursive manner, beginning with the
dependency furthest down. it also checks for circular references, and will not execute
jobs that contain them.

finally, the "components" property declares what components a project has. please take a look at
the section about component definitions below.


components
----------

within any of your projects, you'll most probably want to define at least one component.
components define what is cloned as part of your project, and can have the following properties:

 - repo = the git repo to clone from
 - branch = the branch to check out
 - tag = what tag to be checked out
 - path = where the cloned component will end up within you project

unlike the properties of a project, I don't think that its necessary
for me to go over what most of these are - they're all pretty
self-explanatory.

the one property I will mention a bit though is the "path". this defines where inside of
the project this component will end up being cloned. take a look at the project "dsv_forms" in
the example above. in the project itself we say that the root dir is plainly "forms". this
will create a  folder within the installation path called "forms" and clone into that. now,
take a look in that project's only component, "webforms". it has its path set to
"sites/all/components/contrib/webforms", which means that it will end up in
"forms/sites/all/components/contrib/webforms".
if you do not specify a path for a component, it will simply be cloned into the project root.


defaults
--------

default declarations are great ways to save you time and minimize typo issues when making large
build files. defaults allow you to declare - as the name implies - default values for components.
an example default declaration can look like this:
```json
{
  "defaults": {
    "core": {
      "ignoreEmptyPath": true
    },
    "module_contrib": {
      "path": "sites/all/modules/contrib"
    },
    "module_custom": {
      "path": "sites/all/modules/custom"
    },
    "theme_contrib": {
      "path": "sites/all/themes/contrib"
    },
    "theme_custom": {
      "path": "sites/all/themes/custom"
    }
  },

  "drupal7": {
    "rootDir": "drupal",
    "components": {
      "core_drupal7": {
        "defaults": "core",
        "repo": "https://github.com/drupal/drupal.git",
        "branch": "7.x",
        "tag": "7.28"
      }
    }
  },

  "dsv_theme": {
    "components": {
      "jquery_update": {
        "defaults": "module_contrib",
        "repo": "git://git.drupal.org/project/jquery_update.git",
        "branch": "7.x-2.x",
        "tag": "7.x-2.4",
        "path": "jquery_update"
      },
      "bootstrap": {
        "defaults": "theme_contrib",
        "repo": "git://git.drupal.org/project/bootstrap.git",
        "branch": "7.x-3.x",
        "tag": "7.x-3.0",
        "path": "sites/all/themes/contrib/bootstrap"
      },
      "dsv_drupal_theme": {
        "defaults": "theme_custom",
        "repo": "https://github.com/dsv-su/dsv_drupal_theme.git",
        "path": "sites/all/themes/custom/dsv_drupal_theme"
      }
    }
  },

  ...
```

notice how (for example) the component "jquery_update" in "dsv_theme" has its "defaults" property
set to "module_contrib"? this makes the marihanchan script take the path property defined in that
default and append the component's path when cloning. pretty nifty, right?


flags
-----

currently the marihanchan script can understand the following component flags:

 - __ignoreEmptyPath__ - (boolean) ignores a missing path (issues no warning when building)


git patches
-----------

marihanchan has support for patching your projects, too! currently, only support for patching
entire projects is built in - but patching for components is on its way. applying patches is very
easy to accomplish - just add them to your project which needs patching up:
```json
{
  "moodle26": {
    "rootDir": "moodle",
    "patches": [ "fixes.patch" ],
    "components": {
      "moodle_26_core": {
        "repo": "https://github.com/moodle/moodle.git",
        "branch": "MOODLE_26_STABLE",
        "ignoreEmptyPath": true
      }
    }
  }
}
```

important to remember here is that currently all patches need to reside in the same folder as
the base marihanchan script. a nicer solution to this is being worked on.

__note:__ if a git patch cannot be applied cleanly, then marihanchan will roll back to the remote
HEAD of the current branch (effectively reverting the patch)
