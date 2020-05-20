#! /usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Simon Jarbrant, Dane Cavanagh, Pavel Sokolov'
__copyright__ = 'Copyright 2014, Department of Computer and System Sciences, Stockholm University'

__maintainer__ = 'Pavel Sokolov'
__email__      = 'psokolov@dsv.su.se'
__version__    = '0.0.8'

import sys
import os       # to check if files exists
import argparse # parse cli args
import json     # parse build files
import git      # the main GitPython used to control git
import shutil   # used to copy files
import string

# import path from os, everything from git
from os import path
from git import *

#
# Global variables used throughout the script
# --------------------------------------------
#
defaultBuildFileName = 'build.json'
buildFileName        = ''
buildFilePath        = ''
defaults             = ''
projects             = ''
installPath          = ''


# Builds the specified project
def buildProject( projectName ):
    global projects, installPath

    project = projects.get( projectName )

    # build project dependencies first
    if 'requires' in project:
        for dependency in project.get( 'requires' ):
            if dependency not in projects:
                print 'error: cannot find build declaration for project ' + dependency
                sys.exit( -1 )

            # build dependency
            buildProject( dependency )

    # now proceed with building this project
    if 'components' not in project:
        print 'warning: project has no components, skipping'
    else:
        for name, component in project.get( 'components' ).iteritems():
            fetchComponent( name, component )

    # if there are any git patches specified in this project, apply them
    if 'patches' in project:
        for patch in project.get( 'patches' ):
            applyGitPatch( patch, installPath )

    return

# Checks for circular dependencies within a build-file
def checkCircularDependencies( projectName, parentname, dependencies ):
    global projects, buildFileName

    # load the full project from the build-file so that we have its dependencies
    if projectName in projects:
        project = projects.get( projectName )
    else:
        print 'error: project ' + projectName + ' isn\'t declared in ' + buildFileName
        sys.exit( -1 )

    # add the current projectname to the dependencies dict
    if projectName not in dependencies:
        dependencies[ projectName ] = parentname
    else:
        if parentname == projectName:
            print 'You\'re so mean! >:('
            print 'you have declared ' + projectName + ' to require itself!'
        elif dependencies.get( projectName ) == 'project':
            print 'I hate you! >:('
            print 'you\'ve said that ' + parentname + ' requires ' + projectName + ', but ' \
                + projectName + ' is the project you\'re currently building!'
        else:
            print 'I hate you! >:('
            print 'you\'ve said that ' + parentname + ' requires ' + projectName \
                + ', but that is already required by ' + dependencies.get( projectName )
        sys.exit( -1 )

    # recursively loop through this project's dependencies and check them
    if 'requires' in project:
        for dependency in project.get( 'requires' ):
            # loop through this dependency's dependencies (WE NEED TO GO DEEPER BAAAAAAAAAAAAMMMMMM)
            checkCircularDependencies( dependency, projectName, dependencies )

    return

# Checks for the existence of files required to build the specified project
def checkRequiredFiles( projectName ):
    # check for any git patch files
    checkRequiredPatchFiles( projectName )

    return

# Looks for any patchfiles that have been specified in the buildfile
def checkRequiredPatchFiles( projectName ):
    global projects

    # fetch project dict
    project = projects.get( projectName )

    if 'patches' in project:
        for patchFile in project.get( 'patches' ):
            if not os.path.exists( patchFile ):
                print 'error: couldn\'t find patchfile "' + patchFile + '" in the current' \
                    + ' working dir'
                sys.exit( -1 )

    # now check dependencies (if any)
    if 'requires' in project:
        for dependency in project.get( 'requires' ):
            checkRequiredPatchFiles( dependency )

    return

# Enables support for the "Defaults" system. Checks (and returns) a default value for the given
# property, if one exists
def getDefaultPropertyForComponent( component, propertyName ):
    global defaults

    # if there are no defaults, just return
    if defaults == '':
        return None

    propertyValue = ''

    # get default value for property in component
    if 'defaults' in component:
        defaultName = component.get( 'defaults' )
        componentDefaultProperties = defaults.get( defaultName )
        if propertyName in componentDefaultProperties:
            propertyValue += componentDefaultProperties.get( propertyName )

    if propertyValue is '':
        return None
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

    # if the component has path specified, append it
    if 'path' in component:
        clonePath += component.get( 'path' )
    else:
        # check if we should ignore empty path
        ignoreEmptyPath = False
        if 'ignoreEmptyPath' in component:
            ignoreEmptyPath = component.get( 'ignoreEmptyPath' )
        else:
            ignoreEmptyPath = getDefaultPropertyForComponent( component, 'ignoreEmptyPath' )

        if not ignoreEmptyPath:
            # print warning if we shouldn't ignore that path is empty
            print 'warning: component ' + name + ' doesn\'t have a path specified'

    # if there's a branch specified, use that - otherwise default to master
    branch = 'master'
    if 'branch' in component:
        branch = component.get( 'branch' )

    print 'fetching component: ' + name
    try:
        repo = Repo.clone_from( component.get('repo'), clonePath, branch=branch )
    except GitCommandError:
        print 'ooops, cannot clone, most likely the component exists because you manually cloned it ;O('
        updateComponent( component, component )
        return


    # if there's a tag specified, try to checkout that
    if 'tag' in component:
        repo.git.checkout( 'tags/' + component.get('tag'), b = 'tag_' + component.get('tag') )

    # apply a patch to the component
    if 'patch' in component:
        patch = component.get( 'patch' )
        applyGitPatch( patch, clonePath )

    if 'patches' in component:
        for patch in component.get( 'patches' ):
            applyGitPatch( patch, clonePath )

    return

# Applies the specified patch to the specified project. If it fails, it will revert
def applyGitPatch( patchFileName, repoPath ):
    print 'applying patch \"' + patchFileName + '\" to ' + repoPath + '...'

    # first, get a git object from the repoPath
    git = Git( repoPath )

    # then simply try to apply the patch! (assume that it's located at the current working dir)
    try:
        patchLocation = str( os.getcwd() ) + '/' + patchFileName
        git.am( patchLocation, "-3" )
    except GitCommandError:
        print 'oh no! the patch doesn\'t apply cleanly :\'('
        git.am( '--abort' )
        resetGitRepo( repoPath )

    return

# Initiates the update process on a project
def updateProject( projectName ):
    global buildFileName, projects, installPath

    project = projects.get( projectName )

    # reset the built project so we don't get any git issues
    resetGitRepo( installPath )

    # if it's an old file located in a project dir - move it one level up
    if os.path.isfile( installPath + buildFileName):
        shutil.copyfile( installPath + buildFileName , installPath + '../' + projectName + '_' + buildFileName )
        os.remove( installPath + buildFileName )

    # first, get the build file from the existing project
    if os.path.isfile( installPath + '../' + projectName + '_' + buildFileName ):
        oldBuildFile = open( installPath + '../' + projectName + '_' + buildFileName, 'r' )
        installedProjectDict = json.load( oldBuildFile )
    else:
        print 'error, no build file found at ' + installPath + '../' + projectName + '_' + buildFileName
        sys.exit( -1 )

    # then, sort out any updates / changes and apply them
    findChangesInProject( projectName, installedProjectDict )

    return

# Forcefully reset a git repo to it's remote counterpart's HEAD
def resetGitRepo( repoPath ):
    repo = Repo( repoPath, odbt=GitCmdObjectDB )
    branchName = str( repo.active_branch )

    print 'resetting ' + repoPath + ' to remote HEAD...'

    git = repo.git
    # If we checked out from a tag, branchName is a tag name in that case
    if branchName[:4] == 'tag_':
        git.reset( '--hard', branchName[4:] )
    else:
        git.reset( '--hard', 'origin/' + branchName)

    return

# Does the actual dirty work for updateProject()
def findChangesInProject( projectName, oldBuildDict ):
    global projects

    print 'finding changes in project ' + projectName

    project = projects.get( projectName )

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
    for componentName in removedComponents:
        removeComponent( componentName, oldComponents.get( componentName ) )

    # we don't want to check details for newly added components
    for key in addedComponents:
        del newComponents[key]

    # perform individual component updates
    for componentName in newComponents:
        newComponent = newComponents.get( componentName )
        oldComponent = oldComponents.get( componentName )
        print 'updating component: ' + componentName
        repoPath = installPath
        if 'path' in newComponent:
            # load default path first (if any)
            defaultPath = getDefaultPropertyForComponent( newComponent, 'path' )
            if defaultPath is not None:
                repoPath += defaultPath
            repoPath += newComponent.get( 'path' )
        if not os.path.exists( repoPath ):
            print 'component not found, trying to fetch it'
            fetchComponent ( componentName, newComponent )
        else:
            updateComponent( newComponent, oldComponent )

    # if there is a 'requires' section in the current project, investigate that as well
    if 'requires' in project:
        for requiredProjectName in project.get( 'requires' ):
            requiredProject = projects.get( requiredProjectName )
            findChangesInProject( requiredProjectName, oldBuildDict )

    # apply any patches in the project
    if 'patches' in project:
        for patch in project.get( 'patches' ):
            applyGitPatch( patch, installPath )

    return

# Updates the given component (needs both new and old config specification)
def updateComponent( newComponent, oldComponent ):
    global installPath

    # get repo object
    repoPath = installPath

    if 'path' in newComponent:
        # load default path first (if any)
        defaultPath = getDefaultPropertyForComponent( newComponent, 'path' )
        if defaultPath is not None:
            repoPath += defaultPath
        repoPath += newComponent.get( 'path' )
    repo = Repo( repoPath, odbt=GitCmdObjectDB )

    url = repo.remotes.origin.url
    url = string.replace(url, 'git://', 'https://')
    url = string.replace(url, 'http://', 'https://')
    repo.remotes.origin.config_writer.set("url", url)

    # update branch
    if 'branch' in newComponent:
        newBranch = newComponent.get( 'branch' )
        if 'branch' in oldComponent:
            oldBranch = oldComponent.get( 'branch' )
            if newBranch != oldBranch:
                # git checkout new branch
                print 'checking out new branch (' + newBranch + ')'
                repo.git.fetch()
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
                repo.git.fetch()
                try:
                    # git checkout new tag
                    print 'checking out tag (' + newTag + ')'
                    repo.git.checkout( 'tags/' + newTag, b = 'tag_' + newTag )
                except GitCommandError:
                    # if a tagged branch is already there, just reset it to remote
                    print 'tagged branch ' + newTag + ' already exists, checking it out and resetting it to remote'
                    repo.git.checkout( 'tag_' + newTag)
                    repo.git.reset( '--hard', newTag )
        else:
            repo.git.fetch()
            try:
                # git checkout new tag
                print 'checking out tag (' + newTag + ')'
                repo.git.checkout( 'tags/' + newTag, b = 'tag_' + newTag )
            except GitCommandError:
                # if a tagged branch is already there, just reset it to remote
                print 'tagged branch ' + newTag + ' already exists, checking it out and resetting it to remote'
                repo.git.checkout( 'tag_' + newTag)
                repo.git.reset( '--hard', newTag )
    else:
        # try to get active branch, in case of detached state checkout remote HEAD
        branch = str( repo.active_branch )
        print 'active branch: ' + branch
        try:
            # git pull in case it is a real branch, not tagged one
            repo.git.pull()
        except GitCommandError:
            print 'Oh no! I couldn\'t pull. Probably we\'re at tagged branch and there is no tracking info. Will reset to remote then!'
            tag = branch[4:]
            print 'Resetting to remote tag ' + tag
            try:
                repo.git.reset( '--hard', tag )
            except GitCommandError, e:
                print 'No, we were not on a tagged branch. Please discard manual local changes you\'ve probably done to this project.'
                raise e

    # apply a patch to the component
    if 'patch' in newComponent:
        patch = newComponent.get( 'patch' )
        applyGitPatch( patch, repoPath )

    # apply any patches in the project
    if 'patches' in newComponent:
        for patch in newComponent.get( 'patches' ):
            applyGitPatch( patch, repoPath )


# Removes a component from a built project
def removeComponent( name, component ):
    global installPath

    # generate the path to the component that is to be removed
    removePath = installPath
    if 'path' in component:
		# load default path first (if any)
		defaultPath = getDefaultPropertyForComponent( component, 'path' )
		if defaultPath is not None:
			removePath += defaultPath
		removePath += component.get( 'path' )

    print 'removing component ' + name + ' from ' + removePath

    shutil.rmtree( removePath )
    return

# Main, will execute first when the script is run
def main():
    global defaultBuildFileName, buildFileName, buildFilePath, defaults, projects, installPath

    # parse cli arguments
    parser = argparse.ArgumentParser()
    parser.add_argument( '-b', '--buildfile', help='Buildfile to read projects from', required=True)
    parser.add_argument( '-p', '--project', help='Target build to make', required=True )
    parser.add_argument( '-u', '--update', help='Target build to update', action='store_true' )
    parser.add_argument( '-d', '--directory', help='Directory of project to install or update\
        (will override any \'rootDir\' directive set in the buildfile!)' )
    args = parser.parse_args()

    if args.buildfile:
        buildFilePath = os.path.dirname(args.buildfile) + '/'
        buildFileName = os.path.basename(args.buildfile)
    else:
        buildFileName = defaultBuildFileName

    # extracts the target project name and update flag
    targetName  = args.project
    update      = args.update

    # if directory argument is supplied, use that
    if args.directory:
        installPath = args.directory + '/'

    # open buildfile and parse contents
    if os.path.isfile( buildFilePath + buildFileName ):
        buildFile = open( buildFilePath + buildFileName , 'r' )
        projects  = json.load( buildFile )
    else:
        print 'You\'re so mean! you haven\'t supplied me with a buildfile.. >:('
        sys.exit( -1 )

    # only continue if we have a valid target
    if targetName not in projects:
        print 'error: unknown build target \'' + targetName + '\''
        print 'have you really defined it in ' + buildFileName + '?'
        sys.exit( -1 )

    # extract the buildtarget from the list of available projects
    targetProject = projects.get( targetName )

    # check dependencies
    checkCircularDependencies( targetName, 'project', {} )
    print '*giggles* dependencies looks ok! :)'

    # check required files
    checkRequiredFiles( targetName )
    print '*giggles* and all the files required are here too! :D'

    # load defaults if there are any
    if 'defaults' in projects:
        print 'loading defaults...'
        defaults = projects.get( 'defaults' )

    # set installPath if needed
    if installPath == '':
        if 'rootDir' in targetProject:
            installPath = targetProject.get( 'rootDir' ) + '/'
            print 'but I\'ll install into ' + installPath + ' (read from project\'s rootDir)'
        else:
            print 'but... project ' + targetName + ' has no rootDir specified either :/'
            print 'since I now have nothing to go on, I\'ll clone in the current dir'
    else:
        print 'installing into ' + installPath

    # build or update target accordingly
    if update:
        print 'ok, I\'m updating project ' + targetName + ' now :)'
        updateProject( targetName )
    else:
        # check that installPath doesn't already exist
        if os.path.exists( installPath ) and os.listdir( installPath ):
            print 'error: ' + installPath + ' already exists!'
            print 'if you want to upgrade an existing project, add the --update cli argument'
            sys.exit( -1 )
        else:
            print 'ok, I\'m building project ' + targetName + ' now :)'
            buildProject( targetName )

    # save buildFile to install path
    if os.path.isfile( installPath + '../' + targetName + '_' + buildFileName ):
        os.remove( installPath + '../' + targetName + '_' + buildFileName )
    shutil.copyfile( buildFilePath + buildFileName , installPath + '../' + targetName + '_' + buildFileName )

    print '*giggles* ok I\'m done! project ' + targetName + ' built :)'
    return

# after all the function declarations, call main so that the program starts
main()
