"""
Copyright (c) 2013 Shotgun Software, Inc
----------------------------------------------------

"""
import os
import maya.cmds as cmds

import tank
from tank import Hook

class PrePublishHook(Hook):
    """
    Single hook that implements pre-publish functionality
    """
    def execute(self, tasks, work_template, progress_cb, **kwargs):
        """
        Main hook entry point
        :tasks:         List of tasks to be pre-published.  Each task is be a
                        dictionary containing the following keys:
                        {
                            item:   Dictionary
                                    This is the item returned by the scan hook
                                    {
                                        name:           String
                                        description:    String
                                        type:           String
                                        other_params:   Dictionary
                                    }

                            output: Dictionary
                                    This is the output as defined in the configuration - the
                                    primary output will always be named 'primary'
                                    {
                                        name:             String
                                        publish_template: template
                                        tank_type:        String
                                    }
                        }

        :work_template: template
                        This is the template defined in the config that
                        represents the current work file

        :progress_cb:   Function
                        A progress callback to log progress during pre-publish.  Call:

                            progress_cb(percentage, msg)

                        to report progress to the UI

        :returns:       A list of any tasks that were found which have problems that
                        need to be reported in the UI.  Each item in the list should
                        be a dictionary containing the following keys:
                        {
                            task:   Dictionary
                                    This is the task that was passed into the hook and
                                    should not be modified
                                    {
                                        item:...
                                        output:...
                                    }

                            errors: List
                                    A list of error messages (strings) to report
                        }
        """

        print "<pre-publish> tasks =>", tasks
        print "<pre-publish> work_template =>", work_template

        results = []

        # will need the current scene file:
        scene_file = cmds.file(query=True, sn=True)
        if scene_file:
            scene_file = os.path.abspath(scene_file)
            print "<pre-publish> scene_file =>", scene_file

        # validate tasks:
        for task in tasks:
            item = task["item"]
            output = task["output"]
            errors = []

            # report progress:
            print "<pre-publish> Validiating %s" % task['item']
            progress_cb(0, "Validating", task)

            print output["name"]

            # depending on output type, do some specific validation:
            if output["name"] == "camera_export":
                errors.extend(self._validate_camera(scene_file, work_template, item, output, progress_cb))

            elif output["name"] == "cone_geo_export":
                errors.extend(self._validate_cones(scene_file, work_template, item, output, progress_cb))

            elif output["name"] == "model_geo_export":
                errors.extend(self._validate_geometry(scene_file, work_template, item, output, progress_cb))

            elif output["name"] == "shotgun_note_create":
                pass  # we don't get given the comments...

            elif output["name"] == "lens_distort_export":
                pass  # pfft. should check if the node has been published before probably.

            else:
                # don't know how to publish other output types!
                print "<pre-publish> Don't know how to publish this item! %s as %s" % (item['name'], output['name'])
                errors.append("Don't know how to publish this item! %s as %s" % (item['name'], output['name']))

            # if there is anything to report then add to result
            if len(errors) > 0:
                # add result:
                results.append({"task":task, "errors":errors})

            progress_cb(100)

        import pprint
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(results)

        print "<pre-publish> complete"

        return results

    def _validate_camera(self, path, work_template, item, output, progress_cb):
        """
        Validation rules:
            Camera must be named correctly. |Scene|cameras|(LEFT/RIGHT/SHOT)
            Run euler filter on camera connections cmds.filterCurve( 'LEFT_rotateX', 'LEFT_rotateY', 'LEFT_rotateZ' )
        Return:
            Name error
            Number of Curves filtered
        """
        errors = []

        try:
            cmds.loadPlugin('fbxmaya')
        except RuntimeError:
            print '<pre-publish> Unable to load FBX plugin. We will be unable to export cameras for publish!'
            errors.append('Unable to load FBX plugin. We will be unable to export cameras for publish!')

        return errors

    def _validate_cones(self, path, work_template, item, output, progress_cb):
        errors = []
        try:
            cmds.loadPlugin('objExport')
        except RuntimeError:
            print '<pre-publish> Unable to load objExport plugin. We will be unable to export cones for publish!'
            errors.append('Unable to load objExport plugin. We will be unable to export cones for publish!')

        return errors

    def _validate_geometry(self, path, work_template, item, output, progress_cb):
        errors = []
        try:
            cmds.loadPlugin('objExport')
        except RuntimeError:
            print '<pre-publish> Unable to load objExport plugin. We will be unable to export geo for publish!'
            errors.append('Unable to load objExport plugin. We will be unable to export geo for publish!')

        # clear the current selection and, if the geo is not hidden add it to the new selection.
        # list the current selection. if the object was hidden the selection count will be 0
        cmds.select(item['name'], replace=True, visible=True)
        if not cmds.ls(selection=True):
            print '<pre-publish> Geometry is hidden. Unhide or deselect to continue.'
            errors.append('Geometry is hidden. Unhide or deselect to continue.')

        return errors
