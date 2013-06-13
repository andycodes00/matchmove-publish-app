"""
Copyright (c) 2012 Shotgun Software, Inc
----------------------------------------------------

Hook that loads items into the current scene.

This hook supports a number of different platforms and the behaviour on each platform is
different. See code comments for details.


"""
import tank
import os

class AddFileToScene(tank.Hook):

    def execute(self, engine_name, file_path, shotgun_data, **kwargs):
        """
        Hook entry point and app-specific code dispatcher
        """

        publish_record = self.parent.engine.shotgun.find_one('TankPublishedFile', [['id', 'is', shotgun_data['id']]] ,['entity','name','version_number','tank_type'])

        if engine_name == "tk-maya":
            self.add_file_to_maya(file_path, shotgun_data, publish_record)

        elif engine_name == "tk-nuke":
            self.add_file_to_nuke(file_path, shotgun_data)

        elif engine_name == "tk-motionbuilder":
            self.add_file_to_motionbuilder(file_path, shotgun_data)

        elif engine_name == "tk-3dsmax":
            self.add_file_to_3dsmax(file_path, shotgun_data)

        elif engine_name == "tk-photoshop":
            self.add_file_to_photoshop(file_path, shotgun_data)

        else:
            raise Exception("Don't know how to load file into unknown engine %s" % engine_name)

    ###############################################################################################
    # app specific implementations

    def add_file_to_maya(self, file_path, shotgun_data, publish_data):
        """
        Load file into Maya.

        This implementation creates a standard maya reference file for any item.
        """

        import pymel.core as pm
        import maya.cmds as cmds

        # get the slashes right
        file_path = file_path.replace(os.path.sep, "/")

        (path, ext) = os.path.splitext(file_path)

        type_map = {'Matchmove Camera': 'cam',
                    'Matchmove Model': 'geo',
                    'Matchmove Cones': 'cones'}
        import_name = '%s_%s_%s_v%03d' % (publish_data['entity']['name'], publish_data['name'], type_map[publish_data['tank_type']['name']], publish_data['version_number'])

        texture_extensions = [".png", ".jpg", ".jpeg", ".exr", ".cin", ".dpx",
                              ".psd", ".tiff", ".tga"]

        if ext in [".ma", ".mb"]:
            # maya file - load it as a reference
            pm.system.createReference(file_path)

        elif ext in texture_extensions:
            # create a file texture read node
            x = cmds.shadingNode('file', asTexture=True)
            cmds.setAttr( "%s.fileTextureName" % x, file_path, type="string" )

        elif ext == ".fbx":
            # camera publishes
            try:
                cmds.loadPlugin('fbxmaya')
                pm.mel.eval('FBXImportCameras -v 1')
                pm.mel.eval('FBXImportMode -v merge')
                pm.mel.eval('FBXImport -f "%s"' % file_path)
            except RuntimeError:
                self.parent.log_error('Unable to load FBX plugin. We will be unable to load published cameras')

        elif ext == ".obj":
            # geo or cones

            #file -import -type "OBJ" -gr -ra true -rdn -rpr "end_shot_001_pPlane1_geo_v033" -options "mo=0"
            # -loadReferenceDepth "all"
            # "/mnt/shows/fragrance/sequences/end_shot/end_shot_001/publish/mm/end_shot_001_matchmove_v033/geoPublish/end_shot_001_pPlane1_geo_v033.obj";

            # x = cmds.file(file_path,
            #               i=True,
            #               typ="OBJ",
            #               dns=True,
            #               rdn=True,
            #               ra=True,
            #               rpr=import_name,
            #               options='mo=0',
            #               lrd="all")
            x = pm.mel.eval('file -import -type "OBJ" -gr -gn "{0}"-ra true -rdn -rpr "{0}" -options "mo=0" -loadReferenceDepth "all" "{1}"'.format(import_name, file_path))
            cmds.select(x, replace=True)

        else:
            self.parent.log_error("Unsupported file extension for %s! Nothing will be loaded." % file_path)

    def add_file_to_nuke(self, file_path, shotgun_data):
        """
        Load item into Nuke.

        This implementation will create a read node and associate the given path with
        the read node's file input.
        """

        import nuke

        # get the slashes right
        file_path = file_path.replace(os.path.sep, "/")

        (path, ext) = os.path.splitext(file_path)

        valid_extensions = [".png", ".jpg", ".jpeg", ".exr", ".cin", ".dpx", ".tiff", ".mov"]

        if ext in valid_extensions:
            # create the read node
            nuke.nodes.Read(file=file_path)
        else:
            self.parent.log_error("Unsupported file extension for %s - no read node will be created." % file_path)

    def add_file_to_motionbuilder(self, file_path, shotgun_data):
        """
        Load item into motionbuilder.

        This will attempt to merge the loaded file with the scene.
        """
        from pyfbsdk import FBApplication

        if not os.path.exists(file_path):
            self.parent.log_error("The file %s does not exist." % file_path)
            return

        # get the slashes right
        file_path = file_path.replace(os.path.sep, "/")

        (path, ext) = os.path.splitext(file_path)

        if ext != ".fbx":
            self.parent.log_error("Unsupported file extension for %s. Only FBX files are supported." % file_path)
        else:
            app = FBApplication()
            app.FileMerge(file_path)

    def add_file_to_3dsmax(self, file_path, shotgun_data):
        """
        Load item into 3dsmax.

        This will attempt to merge the loaded file with the scene.
        """
        from Py3dsMax import mxs
        if not os.path.exists(file_path):
            self.parent.log_error("The file %s does not exist." % file_path)
        else:
            mxs.importFile(file_path)

    def add_file_to_photoshop(self, file_path, shotgun_data):
        """
        Load item into Photoshop.
        """
        import photoshop
        f = photoshop.RemoteObject('flash.filesystem::File', file_path)
        photoshop.app.load(f)

