"""
Copyright (c) 2013 Shotgun Software, Inc
----------------------------------------------------

"""
import os
import shutil
import maya.cmds as cmds
import maya.mel as mel

import tank
from tank import Hook
#from tank import TankError

import pprint

class PublishHook(Hook):
    """
    Single hook that implements publish functionality for secondary tasks
    """
    def execute(self, tasks, work_template, comment, thumbnail_path, sg_task, primary_publish_path, progress_cb, **kwargs):
        """
        Main hook entry point
        :tasks:         List of secondary tasks to be published.  Each task is a
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

        :comment:       String
                        The comment provided for the publish

        :thumbnail:     Path string
                        The default thumbnail provided for the publish

        :sg_task:       Dictionary (shotgun entity description)
                        The shotgun task to use for the publish

        :primary_publish_path: Path string
                        This is the path of the primary published file as returned
                        by the primary publish hook

        :progress_cb:   Function
                        A progress callback to log progress during pre-publish.  Call:

                            progress_cb(percentage, msg)

                        to report progress to the UI

        :returns:       A list of any tasks that had problems that need to be reported
                        in the UI.  Each item in the list should be a dictionary containing
                        the following keys:
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
        results = []

        # publish all tasks:
        for task in tasks:
            item = task["item"]
            output = task["output"]
            errors = []

            print "<publish> ", item
            print "<publish> ", output

            # report progress:
            print "<publish> starting"
            progress_cb(0, "Starting...", task)

            # calculate publish path for this task
            # interim kludge...
            working_path = cmds.file(query=True, sceneName=True)

            fields = work_template.get_fields(working_path)
            publish_template = output["publish_template"]
            secondary_publish_path = publish_template.apply_fields(fields)

            if os.path.exists(secondary_publish_path):
                print ("<publish> The secondary output '%s' file named '%s' already exists!" % (item['type'], secondary_publish_path))

                errors.append("The secondary output '%s' file named '%s' already exists!" % (item['type'], secondary_publish_path))
                results.append({"task": task, "errors": errors})
                return results

            # create the parent directories for the publish if they don't already exist.
            if not os.path.exists(os.path.dirname(secondary_publish_path)):
                print "<publish> Creating folder %s" % os.path.dirname(secondary_publish_path)
                os.makedirs(os.path.dirname(secondary_publish_path))

            # depending on output type, do some specific validation:
            if output["name"] == "camera_export":
                errors.extend(self._publish_camera(item, publish_template, fields, comment, sg_task, primary_publish_path, progress_cb))

            elif output["name"] == "cone_geo_export":
                errors.extend(self._publish_cones(item, secondary_publish_path, fields, comment, sg_task, primary_publish_path, progress_cb))

            elif output["name"] == "model_geo_export":
                errors.extend(self._publish_geometry(item, publish_template, fields, comment, sg_task, primary_publish_path, progress_cb))

            elif output["name"] == "lens_distort_export":
                errors.extend(self._publish_lens_node(item, secondary_publish_path, fields, comment, sg_task, primary_publish_path, progress_cb))

            elif output["name"] == "shotgun_note_create":
                 errors.extend(self._publish_note(item, publish_template, fields, comment, sg_task, primary_publish_path, progress_cb))

            else:
                # don't know how to publish other output types!
                errors.append("Don't know how to publish this item! %s as %s" % (item['name'], output['name']))

            # if there is anything to report then add to result
            if len(errors) > 0:
                # add result:
                results.append({"task": task, "errors": errors})

            progress_cb(100)

        return results

    def _publish_camera(self, item, publish_template, fields, comment, sg_task, primary_publish_path, progress_cb):
        """
        Publishes the selected camera as an FBX archive in ASCII format
        """
        errors = []

        print "<publish> publish camera called"

        # more than one camera, so we need to make publish path unique to the item name
        fields['name'] = item['name']
        secondary_publish_path = publish_template.apply_fields(fields)
        secondary_publish_name = fields.get("name").upper()  # we want an uppercase name
        if not secondary_publish_name:
            secondary_publish_name = os.path.basename(secondary_publish_path)

        print "<publish> using name for publish: %s" % secondary_publish_name

        if os.path.exists(secondary_publish_path):
            print "<publish> The published camera named '%s' already exists!" % secondary_publish_path
            errors.append("The published camera named '%s' already exists!" % secondary_publish_path)
            results.append({"task": item, "errors": errors})
            return results

        # select the camera
        try:
            cmds.select(item['name'], visible=True, hierarchy=True, replace=True)
            print "<publish> selected %s" % item['name']
        except ValueError as e:
            errors.append('Unable to select camera [%s]' % item['name'])
            return errors

        # set export settings
        mel.eval('FBXExportInAscii -v 1')
        mel.eval('FBXExportConvertUnitString "cm"')
        mel.eval('FBXExportInputConnections -v 0')
        mel.eval('FBXExportCameras -v 1')

        #FBX 2006 -
        mel.eval('FBXExportFileVersion "FBX200611"')

        print "<publish>"
        print "\tFBXExportInAscii -v 1"
        print '\tFBXExportConvertUnitString "cm"'
        print '\tFBXExportInputConnections -v 0'
        print '\tFBXExportCameras -v 1'
        print '\tFBXExportFileVersion "FBX200611"'

        # export selection
        progress_cb(20.0)
        try:
            mel.eval('FBXExport -f "%s" -s' % secondary_publish_path)
            print '\tFBXExport -f "%s" -s' % secondary_publish_path
        except RuntimeError as e:
            print "<publish> 'Unable to publish camera [%s]" % item['name']
            errors.append('Unable to publish camera [%s]' % item['name'])

        progress_cb(80.0)
        env_disk_location = self.parent.engine.environment['disk_location']
        icons_disk_location = os.path.abspath(os.path.join(os.path.dirname(env_disk_location), '..', 'icons'))
        thumbnail_path = os.path.join(icons_disk_location, 'camera_track_thumb.png')

        self._register_publish(secondary_publish_path,
                               secondary_publish_name,
                               sg_task,
                               fields["version"],
                               'Matchmove Camera',
                               comment,
                               thumbnail_path,
                               [primary_publish_path])

        return errors

    def _publish_cones(self, item, secondary_publish_path, fields, comment, sg_task, primary_publish_path, progress_cb):
        """
        Publishes the cones group and children as a single OBJ archive.
        """
        errors = []
        print "<publish> publish cones called"

        # select the cones
        try:
            cones_ = cmds.select(item['name'], visible=True, hierarchy=True, replace=True)
            print "<publish> ", item['name'], " selected"
        except Exception as e:
            print e
            errors.append('Unable to select cones [%s]' % item['name'])
            return errors

        # export selection
        progress_cb(40.0)
        try:
            cmds.file(secondary_publish_path,
                      pr=0,
                      typ="OBJexport",
                      es=1,
                      op="groups=1; ptgroups=0; materials=0; smoothing=0; normals=0")
            print """cmds.file(secondary_publish_path,
                       pr=0,
                       typ="OBJexport",
                       es=1,
                       op="groups=1; ptgroups=0; materials=0; smoothing=0; normals=0")"""
        except Exception as e:
            print e
            errors.append('Unable to publish cones [%s]' % item['name'])

        progress_cb(80.0)
        env_disk_location = self.parent.engine.environment['disk_location']
        icons_disk_location = os.path.abspath(os.path.join(os.path.dirname(env_disk_location), '..', 'icons'))
        thumbnail_path = os.path.join(icons_disk_location, 'matchmove_cones_thumb.png')

        self._register_publish(secondary_publish_path,
                               'Cones',
                               sg_task,
                               fields["version"],
                               'Matchmove Cones',
                               comment,
                               thumbnail_path,
                               [primary_publish_path])

        return errors

    def _publish_geometry(self, item, publish_template, fields, comment, sg_task, primary_publish_path, progress_cb):
        """
        Publishes the geometry each object as OBJ archives.
        """
        errors = []
        print "<publish> publish model called"

        # there may more than one geo publish, so we need to make publish path unique to the item name
        # could go so badly. we only want to name the exact object.
        fields['name'] = item['name'].split('|')[-1]
        secondary_publish_path = publish_template.apply_fields(fields)

        secondary_publish_name = fields.get("name")
        if not secondary_publish_name:
            secondary_publish_name = os.path.basename(secondary_publish_path)

        if os.path.exists(secondary_publish_path):
            print "<publish> The geoPublish named '%s' already exists!" % secondary_publish_path

            errors.append("The geoPublish named '%s' already exists!" % secondary_publish_path)
            results.append({"task": task, "errors": errors})
            return results

        # select the cones
        try:
            cmds.select(item['name'], visible=True, hierarchy=True, replace=True)
        except Exception as e:
            print e
            errors.append('Unable to select transform [%s]' % item['name'])
            return errors

        # export selection
        progress_cb(60.0)
        try:
            cmds.file(secondary_publish_path,
                      pr=0,
                      typ="OBJexport",
                      es=1,
                      op="groups=1; ptgroups=0; materials=0; smoothing=0; normals=0")
            print """cmds.file(secondary_publish_path,
                       pr=0,
                       typ="OBJexport",
                       es=1,
                       op="groups=1; ptgroups=0; materials=0; smoothing=0; normals=0")"""
        except Exception as e:
            print e
            errors.append('Unable to publish model [%s]' % item['name'])

        progress_cb(80.0)
        env_disk_location = self.parent.engine.environment['disk_location']
        icons_disk_location = os.path.abspath(os.path.join(os.path.dirname(env_disk_location), '..', 'icons'))
        thumbnail_path = os.path.join(icons_disk_location, 'marker_geo_thumb.png')

        self._register_publish(secondary_publish_path,
                               secondary_publish_name,
                               sg_task,
                               fields["version"],
                               'Matchmove Model',
                               comment,
                               thumbnail_path,
                               [primary_publish_path])
        return errors

    def _publish_lens_node(self,  item, secondary_publish_path, fields, comment, sg_task, primary_publish_path, progress_cb):
        """
        Copy and rename the lens distortion script from work path to publish path and register publish.
        """
        errors = []
        print "<publish> publish lens called"

        try:
            # parent directory of dst is created by caller
            print "<publish> copying %s => %s" % (item['name'], secondary_publish_path)
            shutil.copyfile(item['name'], secondary_publish_path)
        except shutil.Error:
            print "<publish> Unable to copy to %s, is this path writable?" % secondary_publish_path
            errors.append("Unable to copy to %s, is this path writable?" % secondary_publish_path)

        env_disk_location = self.parent.engine.environment['disk_location']
        icons_disk_location = os.path.abspath(os.path.join(os.path.dirname(env_disk_location), '..', 'icons'))
        thumbnail_path = os.path.join(icons_disk_location, 'lens_distortion_thumb.png')

        self._register_publish(secondary_publish_path,
                               'lensDistort',
                               sg_task,
                               fields["version"],
                               'Matchmove Lens Distortion Node',
                               comment,
                               thumbnail_path,
                               [primary_publish_path])

        return errors


    def _publish_note(self, item, publish_template, fields, comment, sg_task, primary_publish_path, progress_cb):
        """
        Use the SG api to generate a note in Shotgun.
        """
        errors = []
        print "<publish> publish note called"

        sg = self.parent.engine.shotgun

        fields = ['id', 'content']
        filters = [
            ['entity', 'is', self.parent.context.entity],
        ]
        sg_tasks = sg.find('Task', filters, fields)
        print "<publish> found tasks: %s" % sg_tasks

        args = {
            "project": self.parent.context.project,
            "note_links": [self.parent.context.entity],
            "user": tank.util.get_shotgun_user(sg),
            "subject": 'Matchmove Publish on %s' % self.parent.context.entity.get('name', 'UNSET'),
            "content": comment,
            "sg_note_type": 'Matchmove',
            "tasks": sg_tasks,
        }

        print "<publish> create note args:"
        pp = pprint.PrettyPrinter()
        pp.pprint(args)

        sg_data = sg.create('Note', args, return_fields=['id'])
        if not sg_data.get('id'):
            print '<publish> Unable to create Note! %s' % sg_data
            errors.append('Unable to create Note! %s' % sg_data)

        return errors


    def _register_publish(self, path, name, sg_task, publish_version, tank_type, comment, thumbnail_path=None, dependency_paths=None):
        """
        Helper method to register publish using the
        specified publish info.
        """
        # construct args:
        args = {
            "tk": self.parent.tank,
            "context": self.parent.context,
            "comment": comment,
            "path": path,
            "name": name,
            "version_number": publish_version,
            "task": sg_task,
            "tank_type":tank_type,
            "thumbnail_path": thumbnail_path,
            "dependency_paths": dependency_paths,
            }

        pp = pprint.PrettyPrinter()
        print "<publish> calling register with args:"
        pp.pprint(args)

        # register publish;
        sg_data = tank.util.register_publish(**args)

        print "<publish> register complete, return data:"
        pp.pprint(sg_data)

        return sg_data





