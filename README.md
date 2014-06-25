marihanchan
===========

_a git cloning utility for the DSVIT CMS deployment system_

_"make me a ~~sandwich~~ project!"_


what is this?
-------------
_todo: write_

most basic usage:
```shell
    ./marihanchan.py --project <project>
```


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

marihan needs a build-file in order to function. this works sort of like a 'repository',
in which the different projects that can be created are defined. a build-file is written
in JSON, needs to reside in the same directory as the main 'marihan.py' script, and needs
to be named 'build.json' (later versions of marihan might be able to do this part in a
smarter way).

a basic build-file example:
```json
{
  "drupal_base": {
    "root": "drupal",
    "components": {
      "drupal": {
        "repo": "https://github.com/drupal/drupal.git",
        "branch": "7.x"
      }
    }
  },

  "dsv_base": {
    "root": "dsv_base",
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
    "root": "forms",
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

 - 'root' = a simple string telling marihan if the project should be put in a specific
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

the "root" of the project is the location of where marihan will put it. this could be
either just nothing (would clone into the execution dir) or any absolute or relative
url within the system. please note that marihan always uses the "root" of the top-most
project only, so if you have a project with no root in it - none of the dependencies will
change this fact.

the "rqeuires" property tells marihan what other projects this current one depends on. in
the example above, the "dsv_forms" project depends on the "dsv_base", which in turn depends
on "drupal_base". marihan will always build in a recursive manner, beginning with the
dependency furthest down. it also checks for circular references, and will not execute
jobs that contain them.

finally, the "components" property declares what components a project has. please take a look at
the section about component definitions below.

components
-------

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
