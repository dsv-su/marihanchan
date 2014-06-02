#! /usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Simon Jarbrant'
__copyright__ = 'Copyright 2014, Department of Computer and System Sciences, Stockholm University'

__maintainer__ = 'Simon Jarbrant'
__email__      = 'simon@dsv.su.se'
__version__    = '0.0.3beta'

import sys, argparse, json, git, shutil
from git import *

buildFileName = 'build.json'
projects      = ''
installPath   = ''

def checkCircularDependencies( projectname, parentname, dependencies ):
    # add the current projectname to the dependencies dict
    if projectname not in dependencies:
        dependencies[ projectname ] = parentname
    else:
        if parentname == projectname:
            print 'I hate you! >:('
            print 'you have declared ' + projectname + ' to require itself!'
        elif dependencies.get( projectname ) == 'project':
            print 'I hate you! >:('
            print 'you\'ve said that ' + parentname + ' requires ' + projectname + ', but ' + projectname + ' is the project you\'re currently building!'
        else:
            print 'I hate you! >:('
            print 'you\'ve said that ' + parentname + ' requires ' + projectname + ', but that is already required by ' + dependencies.get( projectname )
        sys.exit( -1 )

    # load the full project from the build-file so that we have its dependencies
    project = projects.get( projectname )

    # recursively loop through this project's dependencies and check them
    if 'requires' in project:
        for dependency in project.get( 'requires' ):
            # loop through this dependency's dependencies (WE NEED TO GO DEEPER BAAAAAAAAAAAAAAMMMMMM)
            checkCircularDependencies( dependency, projectname, dependencies )

    return


def fetchModule( name, module ):
    global installPath

    if 'repo' not in module:
        print 'error: module doesn\'t have the \'repo\' key set'
        sys.exit( -1 )

    print 'installPath: ' + installPath

    # get the relative destination for the module
    clonePath = ''
    if installPath != '':
        clonePath += installPath

    # if the module has an explicit path specified, use that
    if 'path' in module:
        clonePath += module.get( 'path' )
    else:
        print 'warning: module ' + name + ' doesn\'t have a path specified'

    print 'clonePath: ' + clonePath

    # if there's a branch specified, use that - otherwise default to master
    branch = 'master'
    if 'branch' in module:
        branch = module.get( 'branch' )

    repo = Repo.clone_from( module.get('repo'), clonePath, branch=branch )

    # if there's a tag specified, try to checkout that
    if 'tag' in module:
        repo.git.checkout( 'tags/' + module.get('tag') )

    return


def buildProject( project ):
    global projects

    # build project requirements first
    if 'requires' in project:
        for dependency in project.get( 'requires' ):
            if dependency not in projects:
                print 'error: cannot find build declaration for project ' + dependency
                sys.exit( -1 )

            # build dependency
            buildProject( projects.get(dependency) )

    # now proceed with building project
    if 'modules' not in project:
        print 'warning: project has no modules, skipping'
    else:
        for name, module in project.get( 'modules' ).iteritems():
            fetchModule( name, module )

    return


def main():
    global buildFileName, projects, installPath

    # parse cli arguments
    parser = argparse.ArgumentParser()
    parser.add_argument( '-b', '--build', help='Target build to make', required=True )
    parser.add_argument( '-d', '--directory', help='Directory to install to' )
    args = parser.parse_args()

    targetName  = args.build
    installPath = args.directory

    # add trailing slash to installPath if needed
    if installPath != '':
        installPath += '/'

    print 'installPath: ' + installPath

    # open buildfile and parse contents
    buildFile = open( buildFileName, 'r' )
    projects  = json.load( buildFile )

    # only continue if we have a valid target
    if targetName not in projects:
        print 'error: unknown build target \'' + targetName + '\''
        sys.exit( -1 )

    # extract the buildtarget from the list of available projects
    targetProject = projects.get( targetName )

    # check dependencies
    print '*giggles* ok, checking dependencies...' 
    checkCircularDependencies( targetName, 'project', {} )

    print '*giggles* dependencies ok! :)'

    # set root folder path
    if 'root' in targetProject:
        installPath += targetProject.get( 'root' ) + '/'
    else:
        print 'warning: project ' + targetName + ' has no root folder specified'

    print 'ok, I\'m building project ' + targetName + ' now :)'

    # build target
    buildProject( targetProject )

    # save buildFile to install path
    shutil.copyfile( buildFileName, installPath + buildFileName )

    print '*giggles* ok I\'m done! project ' + targetName + ' built :)'

main()