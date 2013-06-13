"""
Copyright (c) 2013 Shotgun Software, Inc
----------------------------------------------------

"""

import os
import maya.cmds as cmds

import tank
from tank import Hook

class AttributeNotConnected(Exception):
    pass

class ScanSceneHook(Hook):
    """
    Hook to scan scene for items to publish
    """

    def execute(self, **kwargs):
        """
        Main hook entry point
        """

        items = []
        current_selection = cmds.ls(selection=True)

        # get the main scene:
        scene_path = os.path.abspath(cmds.file(query=True, sn=True))
        name = os.path.basename(scene_path)
        if not name:
            name = "matchmove"

        items.append({
            "type": "work_file",
            "name": name,
            "description": ""})

        # get a list of any cameras in the scene, then filter by those with
        # connections to animCurves. These are the cameras which have been baked
        all_persp_cameras = cmds.listCameras(perspective=True)
        for camera in all_persp_cameras:
            try:
                for attr_name in ['tx','ty','tz','rx','ry','rz','sx','sy','sz']:
                    plug = "%s.%s" % (camera, attr_name)
                    if not cmds.connectionInfo(plug, isDestination=True):
                        raise AttributeNotConnected
            except AttributeNotConnected:
                break
            else:
                print '<scan-scene> found camera %s' % camera
                items.append({
                    "type": "camera",
                    "name": camera,
                    "description": "scene renderable camera",
                    "selected": True,
                })

        # find all of the cones in the scene. Cones are any object with part of
        # their name containing 'cone' or 'Cone'.
        cone_parents = set()
        cones_groups = cmds.ls('|Scene|cones*', transforms=True, long=True)

        #for cone in all_cones:
            #try:
                #cone_parents.add(cmds.listRelatives(cone, parent=True, fullPath=True)[0])
            #except:
                #pass # the object is parented to the global root

        for parent in cones_groups:
            print '<scan-scene> found cones group %s' % parent
            items.append({
                "type": "cones_geo",
                "name": parent,
                "description": "cones",
                "selected": True,
            })

        # find geo in the scene and add each peice to the items list, assumes the
        # scene has been created per MM specs.
        all_geo = cmds.ls('|Scene|geo|*', transforms=True, long=True)
        for geo_obj in all_geo:
            print '<scan-scene> found geo %s' % geo_obj
            items.append({
                "type": "model_geo",
                "name": geo_obj,
                "description": "model",
                "selected": True,
            })

        # locate lens distortion nodes exported from 3DE
        lens_work_path_template = self.parent.get_template_by_name('3de_shot_lens_work')
        lens_fields = self.parent.context.as_template_fields(lens_work_path_template)
        found_lenses = self.parent.tank.paths_from_template(lens_work_path_template, lens_fields, skip_keys=['version'])
        for lens_name in found_lenses:
            print '<scan-scene> found lens %s' % lens_name
            items.append({
                "type": "lens_node",
                "name": lens_name,
                "description": "Lens distortion nuke node exported from 3DEqualizer",
                "selected": True,
            })

        items.append({
            "type": "shotgun_note",
            "name": "comments",
            "description": "upload comments as a new Shot Note",
            "selected": True,
        })

        import pprint
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(items)

        print "<scan-scene> complete"

        return items
