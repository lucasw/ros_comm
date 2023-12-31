#!/usr/bin/env python
# Software License Agreement (BSD License)
#
# Copyright (c) 2009, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import os
import signal
import sys 
import time
import unittest

import rospy
import rostest

import std_msgs.msg

from subprocess import Popen, PIPE

def run_for(cmd, secs):
    popen = Popen(cmd, stdout=PIPE, stderr=PIPE, close_fds=True)
    timeout_t = time.time() + secs
    while time.time() < timeout_t:
        time.sleep(0.1)
    os.kill(popen.pid, signal.SIGKILL)
    
class TestRostopicOnline(unittest.TestCase):

    def setUp(self):
        self.msgs = {}
        self.topics = ['/chatter', '/foo/chatter', '/bar/chatter']
        rospy.loginfo(self.topics)
        self.cmd = 'rostopic'

        # wait for network to initialize
        rospy.init_node('test')

    def callback(self, msg, key):
        self.msgs[key] = msg

    def test_rostopic(self):
        topics = self.topics
        cmd = self.cmd

        for i, t in enumerate(topics):
            rospy.Subscriber(t, std_msgs.msg.String, self.callback, i)

        timeout_t = time.time() + 10.0
        while time.time() < timeout_t and set(topics) != set(self.msgs.keys()):
            time.sleep(0.1)

        # network is initialized
        names = ['/chatter', 'foo/chatter']

        time.sleep(1.0)
        # list
        # - we aren't matching against the core services as those can make the test suites brittle
        output = Popen([cmd, 'list'], stdout=PIPE).communicate()[0]
        output = output.decode()
        topic_list = set(output.split())
        rospy.logwarn("{topics} - {topic_list})")
        for topic in topics:
            self.assert_(topic in topic_list, f"{topic} - {topic_list}")

        for name in names:
            # type
            output = Popen([cmd, 'type', name], stdout=PIPE).communicate()[0]
            output = output.decode()
            self.assertEqual('std_msgs/String', output.strip())
            # check type of topic field
            output = Popen([cmd, 'type', name + '/data'], stdout=PIPE).communicate()[0]
            output = output.decode()
            self.assertEqual('std_msgs/String data string', output.strip())

            # TODO(lucasw) it seems like the publishers from test_rostopic_pub
            # sometimes are seen here when running the test with reuse-master
            full_cmd = [cmd, 'find', 'std_msgs/String']
            output = Popen(full_cmd, stdout=PIPE).communicate()[0]
            output = output.decode()
            values = [n.strip() for n in output.split('\n') if n.strip()]
            self.assertEqual(set(values), set(topics), f"\n{full_cmd}\noutput: {output}\nvalues: {values}\n{topics}")

            #echo
            # test with -c option to get command to terminate
            count = 3
            full_cmd = [cmd, 'echo', name, '-n', str(count)]
            output = Popen(full_cmd, stdout=PIPE).communicate()[0]
            output = output.decode()
            values = [n.strip() for n in output.split('\n') if n.strip()]
            values = [n for n in values if n.startswith("data: ")]
            text = f"{full_cmd}\nwrong number of echos in output:\n{values}"
            self.assertEqual(count, len(values), text)
            for n in values:
                self.assert_('data: "hello world ' in n, n)

            if 0:
                #bw
                stdout, stderr = run_for([cmd, 'bw', name], 3.)
                self.assert_('average:' in stdout, "OUTPUT: %s\n%s"%(stdout,stderr))

                # hz
                stdout, stderr = run_for([cmd, 'hz', name], 2.)
                self.assert_('average rate:' in stdout)

                # delay
                stdout, stderr = run_for([cmd, 'delay', name], 2.)
                self.assert_('average rate:' in stdout)

    def test_rostopic_pub(self):
        topics = self.topics
        cmd = self.cmd
        # pub
        #  - pub wait until ctrl-C, so we have to wait then kill it
        if True:
            s = 'hello'
            topic = '/pub/chatter'
            key = topic
            sub1 = rospy.Subscriber(topic, std_msgs.msg.String, self.callback, key)
            rospy.loginfo(f"created {topic}")

            #TODO: correct popen call
            args = [cmd, 'pub', topic, 'std_msgs/String', s]
            popen = Popen(args, stdout=PIPE, stderr=PIPE, close_fds=True)
        
            # - give rostopic pub 5 seconds to send us a message
            timeout_t = time.time() + 5.0
            while time.time() < timeout_t and set(topics) != set(self.msgs.keys()):
                time.sleep(0.1)
            # - check published value
            self.assertIn(key, self.msgs, f"{self.msgs}")
            msg = self.msgs[key]
            self.assertEqual(s, msg.data, f"{args} {self.msgs}")
            
            os.kill(popen.pid, signal.SIGKILL)

            # test with dictionary
            topic = '/pub2/chatter'
            key = topic
            sub2 = rospy.Subscriber(topic, std_msgs.msg.String, self.callback, key)

            args = [cmd, 'pub', topic, 'std_msgs/String', "{data: %s}"%s]
            popen = Popen(args, stdout=PIPE, stderr=PIPE, close_fds=True)

            # - give rostopic pub 5 seconds to send us a message
            timeout_t = time.time() + 5.
            while time.time() < timeout_t and set(topics) != set(self.msgs.keys()):
                time.sleep(0.1)
                
            # - check published value
            self.assertIn(key, self.msgs)
            msg = self.msgs[key]
            self.assertEqual(s, msg.data)
            
            os.kill(popen.pid, signal.SIGKILL)
            
PKG = 'test_rostopic'
NAME = 'test_rostopic_command_line_online'
if __name__ == '__main__':
    rostest.run(PKG, NAME, TestRostopicOnline, sys.argv)
