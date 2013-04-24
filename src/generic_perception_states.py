#!/usr/bin/python
import roslib
roslib.load_manifest('raw_generic_states')
import rospy
import smach
import smach_ros
import hbrs_srvs.srv
import std_srvs.srv
import tf
import geometry_msgs.msg
import hbrs_msgs.msg

from hbrs_srvs.srv import GetObjects, ReturnBool


class find_drawer(smach.State):

    def __init__(self):
        smach.State.__init__(
            self,
            outcomes=['found_drawer', 'no_drawer_found', 'srv_call_failed'], output_keys=["drawer_pose_list"])
        
        self.drawer_finder_srv_name = '/hbrs_perception/detect_marker'
        self.drawer_finder_srv = rospy.ServiceProxy(self.drawer_finder_srv_name, hbrs_srvs.srv.GetObjects)
        
    def execute(self, userdata): 
        
        try:
            rospy.wait_for_service(self.drawer_finder_srv_name, 15)
            resp = self.drawer_finder_srv()
        except Exception, e:
            rospy.logerr("could not execute service <<%s>>: %e", self.drawer_finder_srv_name, e)
            return 'srv_call_failed'
            
        if (len(resp.objects) <= 0):
            rospy.logerr('found no drawer')
            return 'no_drawer_found'
        
        rospy.loginfo('found {0} drawers'.format(len(resp.objects)))
        
        userdata.drawer_pose_list = resp.objects
        
        return 'found_drawer'


class detect_object(smach.State):

    def __init__(self):
        smach.State.__init__(
            self,
            outcomes=['succeeded', 'failed'],
            output_keys=['object_list'])
        
        self.object_finder_srv = rospy.ServiceProxy('/hbrs_object_finder/get_segmented_objects', hbrs_srvs.srv.GetObjects)

    def execute(self, userdata):     
        #get object pose list
        rospy.wait_for_service('/hbrs_object_finder/get_segmented_objects', 30)

        for i in range(10): 
            print "find object try: ", i
            resp = self.object_finder_srv()
              
            if (len(resp.objects) <= 0):
                rospy.loginfo('found no objects')
                rospy.sleep(0.1);
            else:    
                rospy.loginfo('found {0} objects'.format(len(resp.objects)))
                break
            
        if (len(resp.objects) <= 0):
            rospy.logerr("no graspable objects found");
            userdata.object_list = []            
            return 'failed'
        
        else:
            userdata.object_list = resp.objects
            return 'succeeded'


class find_objects(smach.State):

    DETECT_SERVER = '/detect_objects'

    def __init__(self, retries=5, frame_id=None):
        smach.State.__init__(self,
                             outcomes=['objects_found',
                                       'no_objects_found',
                                       'srv_call_failed'],
                             input_keys=['found_objects'],
                             output_keys=['found_objects'])
        self.detect_objects = rospy.ServiceProxy(self.DETECT_SERVER, GetObjects)
        self.tf_listener = tf.TransformListener()
        self.retries = retries
        self.frame_id = frame_id

    def execute(self, userdata):
        userdata.found_objects = None
        for i in range(self.retries):
            rospy.loginfo('Looking for objects (attempt %i/%i)' % (i + 1, self.retries))
            try:
                rospy.wait_for_service(self.DETECT_SERVER, 15)
                resp = self.detect_objects()
            except Exception as e:
                rospy.logerr("Service call to <<%s>> failed", self.DETECT_SERVER)
                return 'srv_call_failed'
            if not resp.objects:
                rospy.loginfo('Found no objects')
            else:
                n = str([obj.name for obj in resp.objects])
                rospy.loginfo('Found %i objects: %s' % (len(resp.objects), n))
                break

        if not resp.objects:
            rospy.loginfo('No objects in the field of view')
            return 'no_objects_found'

        if self.frame_id:
            for obj in resp.objects:
                try:
                    obj.pose = self.tf_listener.transformPose(self.frame_id, obj.pose)
                except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
                    rospy.logerr('Unable to transform %s -> %s' % (obj.pose.header.frame_id, self.frame_id))

        userdata.found_objects = resp.objects
        return 'objects_found'


class do_visual_servoing(smach.State):

    SERVER = '/raw_visual_servoing/do_visual_servoing'

    def __init__(self):
        smach.State.__init__(self,
                             outcomes=['succeeded', 'failed', 'timeout'],
                             input_keys=['simulation'])
        self.do_vs = rospy.ServiceProxy(self.SERVER, ReturnBool)

    def execute(self, userdata):
        if userdata.simulation:
            return 'succeeded'
        try:
            rospy.logdebug("Calling service <<%s>>" % self.SERVER)
            response = self.do_vs()
        except rospy.ServiceException as e:
            rospy.logerr("Exception when calling service <<%s>>: %s" % (self.SERVER, str(e)))
            return 'aborted'
        if response.value:
            return 'succeeded'
        else:
            return 'timeout'
