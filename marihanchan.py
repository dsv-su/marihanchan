#! /usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Simon Jarbrant'
__copyright__ = 'Copyright 2014, Department of Computer and System Sciences, Stockholm University'

__maintainer__ = 'Simon Jarbrant'
__email__      = 'simon@dsv.su.se'
__version__    = '0.0.5'

import sys
import os       # to check if files exists
import argparse # parse cli args
import json     # parse build files
import git      # the main GitPython used to control git
import shutil   # used to copy files

# import path from os, everything from git
from os import path
from git import *

#
# Global variables used throughout the script
# --------------------------------------------
#
defaultBuildFileName = 'build.json'
buildFileName        = ''
defaults             = ''
projects             = ''
installPath          = ''

# Checks for circular dependencies within a build-file
def checkCircularDependencies( projectname, parentname, dependencies ):
    # add the current projectname to the dependencies dict
    if projectname not in dependencies:
        dependencies[ projectname ] = parentname
    else:
        if parentname == projectname:
            print 'You\'re so mean! >:('
            print 'you have declared ' + projectname + ' to require itself!'
        elif dependencies.get( projectname ) == 'project':
            print 'I hate you! >:('
            print 'you\'ve said that ' + parentname + ' requires ' + projectname + ', but ' \
                + projectname + ' is the project you\'re currently building!'
        else:
            print 'I hate you! >:('
            print 'you\'ve said that ' + parentname + ' requires ' + projectname \
                + ', but that is already required by ' + dependencies.get( projectname )
        sys.exit( -1 )

    # load the full project from the build-file so that we have its dependencies
    project = projects.get( projectname )

    # recursively loop through this project's dependencies and check them
    if 'requires' in project:
        for dependency in project.get( 'requires' ):
            # loop through this dependency's dependencies (WE NEED TO GO DEEPER BAAAAAAAAAAAAMMMMMM)
            checkCircularDependencies( dependency, projectname, dependencies )

    return


def getDefaultPropertyForComponent( component, propertyName ):
    global defaults

    propertyValue = None

    # get default value for property in component
    if 'defaults' in component:
        defaultName = component.get( 'defaults' )
        componentDefaultProperties = defaults.get( defaultName )
        if propertyName in componentDefaultProperties:
            propertyValue += componentDefaultProperties.get( propertyName )

    return propertyValue

# This does the actual hard work, and fetches git repos
def fetchComponent( name, component ):
    global installPath

    if 'repo' not in component:
        print 'error: component doesn\'t have the \'repo\' key set'
        sys.exit( -1 )

    # get the relative destination for the component
    clonePath = ''
    if installPath != '':
        clonePath += installPath

    # load default path first (if any)
    defaultPath = getDefaultPropertyForComponent( component, 'path' )
    if defaultPath is not None:
        clonePath += defaultPath

    # if the component has path specified, use it
    if 'path' in component:
        clonePath += component.get( 'path' )
    else:
        # check if we should ignore empty path
        ignoreEmptyPath = getDefaultPropertyForComponent( component, 'ignoreEmptyPath' )
        if not ignoreEmptyPath:
            print 'warning: component ' + name + ' doesn\'t have a path specified'

    # if there's a branch specified, use that - otherwise default to master
    branch = 'master'
    if 'branch' in component:
        branch = component.get( 'branch' )

    print 'fetching component ' + name
    repo = Repo.clone_from( component.get('repo'), clonePath, branch=branch )

    # if there's a tag specified, try to checkout that
    if 'tag' in component:
        repo.git.checkout( 'tags/' + component.get('tag') )

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
    if 'components' not in project:
        print 'warning: project has no components, skipping'
    else:
        for name, component in project.get( 'components' ).iteritems():
            fetchComponent( name, component )

    return

# Removes a component from a built project
def removeComponent( name, component ):
    global installPath

    # generate the path to the component that is to be removed
    removePath = installPath
    if 'path' in component:
        removePath += component.get( 'path' )

    print 'removing component ' + name + ' from ' + removePath

    shutil.rmtree( removePath )
    return


def updateComponent( newComponent, oldComponent ):
    global installPath

    # get repo object
    repoPath = installPath
    if 'path' in newComponent:
        repoPath += '/' + newComponent.get( 'path' )

    repo = Repo( repoPath, odbt=GitCmdObjectDB )

    # update branch
    if 'branch' in newComponent:
        newBranch = newComponent.get( 'branch' )
        if 'branch' in oldComponent:
            print 'currently active branch is ' + str( repo.active_branch() )

            oldBranch = oldComponent.get( 'branch' )
            if newBranch != oldBranch:
                # git checkout new branch
                print 'checking out new branch (' + newBranch + ')'
                repo.git.checkout( newBranch )
        else:
            # git checkout new branch
            print 'checking out new branch (' + newBranch + ')'
            repo.git.checkout( newBranch )

    # update tag
    if 'tag' in newComponent:
        newTag = newComponent.get( 'tag' )
        if 'tag' in oldComponent:
            oldTag = oldComponent.get( 'tag' )
            if newTag != oldTag:
                # git checkout new tag
                print 'checking out new tag (' + newTag + ')'
                repo.git.checkout( 'tags/' + newTag )
        else:
            # git checkout new tag
            print 'checking out new tag (' + newTag + ')'
            repo.git.checkout( 'tags/' + newTag )

    # git pull!
    repo.git.pull()

# Does the actual dirty work for updateProject()
def findChangesInProject( project, projectName, buildDict, oldBuildDict ):
    print 'finding changes in project ' + projectName

    # get component info from this project
    newComponents = project.get( 'components' )
    oldComponents = oldBuildDict.get( projectName ).get( 'components' )

    # get the added and removed components
    addedComponents = newComponents.viewkeys() - oldComponents.viewkeys()
    removedComponents = oldComponents.viewkeys() - newComponents.viewkeys()

    # add new components
    for componentName in addedComponents:
        fetchComponent( componentName, newComponents.get( componentName ) )

    # remove removed components
    for componentName in removedcomponents:
        removecomponent( componentName, oldComponents.get( componentName ) )

    # we don't want to check details for newly added components
    for key in addedComponents:
        del newComponents[key]

    # perform individual component updates
    for componentName in newComponents:
        newComponent = newComponents.get( componentName )
        oldComponent = oldComponents.get( componentName )
        print 'updating component: ' + componentName
        updatecomponent( newComponent, oldComponent )

    # if there is a 'requires' section in the current project, investigate that as well
    if 'requires' in project:
        for requiredProjectName in project.get( 'requires' ):
            requiredProject = buildDict.get( requiredProjectName )
            findChangesInProject( requiredProject, requiredProjectName, buildDict, oldBuildDict )

    return

# Initiates the update process on a project
def updateProject( project, projectName ):
    global buildFileName, projects, installPath

    # first, get the build file from the existing project
    if os.path.isfile( installPath + buildFileName ):
        oldBuildFile = open( installPath + buildFileName, 'r' )
        installedProjectDict = json.load( oldBuildFile )
    else:
        print 'error, no build file found at ' + installPath + buildFileName
        sys.exit( -1 )

    # then, sort out any updates / changes
    findChangesInProject( project, projectName, projects, installedProjectDict )
    return


def main():
    global defaultBuildFileName, buildFileName, defaults, projects, installPath

    # parse cli arguments
    parser = argparse.ArgumentParser()
    parser.add_argument( '-b', '--buildfile', help='Buildfile to read projects from', required=True)
    parser.add_argument( '-p', '--project', help='Target build to make', required=True )
    parser.add_argument( '-u', '--update', help='Target build to update', action='store_true' )
    parser.add_argument( '-d', '--directory', help='Directory of project to install or update\
        (will override any \'root\' directive set in the buildfile!)' )
    args = parser.parse_args()

    if args.buildfile:
        buildFileName = args.buildfile
    else:
        buildFileName = defaultBuildFileName

    # extracts the target project name and update flag
    targetName  = args.project
    update      = args.update

    # if directory argument is supplied, use that. otherwise install in current dir
    if args.directory:
        installPath = args.directory
    else:
        installPath = ''

    # add trailing slash to installPath if needed
    if installPath != '':
        installPath += '/'

    # open buildfile and parse contents
    if os.path.isfile( buildFileName ):
        buildFile = open( buildFileName, 'r' )
        projects  = json.load( buildFile )
    else:
        print 'You\'re so mean! you haven\'t supplied me with a buildfile.. >:('
        sys.exit( -1 )

    # only continue if we have a valid target
    if targetName not in projects:
        print 'error: unknown build target \'' + targetName + '\''
        sys.exit( -1 )

    # extract the buildtarget from the list of available projects
    targetProject = projects.get( targetName )

    # check dependencies
    print '*giggles* ok, checking dependencies...' 
    checkCircularDependencies( targetName, 'project', {} )

    print '*giggles* dependencies looks ok! :)'

    # load defaults if there are any
    if 'defaults' in projects:
        print 'loading defaults...'
        defaults = projects.get( 'defaults' )

    # set root folder path
    if 'root' in targetProject and installPath == '':
        installPath += targetProject.get( 'root' ) + '/'
    else:
        print 'but... project ' + targetName + ' has no root folder specified :/'

    # build or update target accordingly
    if update:
        print 'ok, I\'m updating project ' + targetName + ' now :)'
        updateProject( targetProject, targetName )
    else:
        print 'ok, I\'m building project ' + targetName + ' now :)'
        buildProject( targetProject )

    # save buildFile to install path
    shutil.copyfile( buildFileName, installPath + buildFileName )

    print '*giggles* ok I\'m done! project ' + targetName + ' built :)'
    return

# after all the function declarations, call main so that the program starts
main()