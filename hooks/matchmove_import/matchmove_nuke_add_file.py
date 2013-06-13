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

        if engine_name != "tk-nuke":
            raise Exception("This AddFileToScene hook only works in Nuke!")

        elif publish_record['tank_type']['name'] == 'Matchmove Camera':
            self.add_camera_to_nuke(file_path, shotgun_data, publish_record)

        elif publish_record['tank_type']['name'] == 'Matchmove Cones':
            self.add_cones_to_nuke(file_path, shotgun_data, publish_record)

        elif publish_record['tank_type']['name'] == 'Matchmove Model':
            self.add_model_to_nuke(file_path, shotgun_data, publish_record)

        elif publish_record['tank_type']['name'] == 'Matchmove Lens Distortion Node':
            self.add_lens_to_nuke(file_path, shotgun_data, publish_record)

        else:
            raise Exception("Don't know how to load file into Nuke")


    def add_camera_to_nuke(self, file_path, shotgun_data, publish_record):
        """
        Load camera into Nuke.

        This implementation will create a Camera node and set the file input from the cached camera.
        """

        import nuke

        # get the slashes right
        file_path = file_path.replace(os.path.sep, "/")
        (path, ext) = os.path.splitext(file_path)
        file_name = "%s_%s_v%03d" % (publish_record['entity']['name'], publish_record['name'], publish_record['version_number'])

        if ext == ".fbx":
            # create the camera node
            cam = nuke.nodes.Camera2(name=file_name)
            cam['read_from_file'].setValue(True)
            cam['file'].setValue(file_path)

            cam.showControlPanel()

            fbx_node_names = cam['fbx_node_name'].values()
            fbx_take_names = cam['fbx_take_name'].values()

            cam['fbx_node_name'].setValue(fbx_node_names[-1])
            cam['fbx_take_name'].setValue(fbx_take_names[-1])
        else:
            self.parent.log_error("Unsupported file extension for %s - no read node will be created." % file_path)


    def add_cones_to_nuke(self, file_path, shotgun_data, publish_record):
        """
        Cheat Method, reuse the generic model load method to bring in cones.
        """
        self.add_model_to_nuke(file_path, shotgun_data, publish_record)

    def add_model_to_nuke(self, file_path, shotgun_data, publish_record):
        """
        Load obj data into Nuke.

        This implementation will create a ReadGeo Node in Nuke.
        """

        import nuke

        # get the slashes right
        file_path = file_path.replace(os.path.sep, "/")
        (path, ext) = os.path.splitext(file_path)
        file_name = "%s_%s_v%03d" % (publish_record['entity']['name'], publish_record['name'], publish_record['version_number'])

        if ext == ".obj":
            # create the Geo node
            model = nuke.nodes.ReadGeo(name=file_name, file=file_path)
            model['display'].setValue('solid+lines')

        else:
            self.parent.log_error("Unsupported file extension for %s - no ReadGeo node will be created." % file_path)

    def add_lens_to_nuke(self, file_path, shotgun_data, publish_record):
        """
        Import a lens node script to the current scene
        """

        import nuke

        # get the slashes right
        file_path = file_path.replace(os.path.sep, "/")
        (path, ext) = os.path.splitext(file_path)
        file_name = "%s_%s_v%03d" % (publish_record['entity']['name'], publish_record['name'], publish_record['version_number'])

        if ext == ".nk":
            # import the nodes
            print "Adding nodes from %s" % file_path
            nuke.nodePaste(file_path)
        else:
            self.parent.log_error("Lens is not a nuke script! I don't know how to import")