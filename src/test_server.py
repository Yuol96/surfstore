import unittest
import hashlib
import xmlrpc.client
import subprocess
import time

import server

SLEEPTIME = 1

class TestServer(unittest.TestCase):
    def setUp(self):
        # setup server on subprocess
        bashCommand = "python server.py"
        self.server = subprocess.Popen(bashCommand.split())
        # wait to set up remote server
        time.sleep(SLEEPTIME)
        # setup client
        try:
            self.client  = xmlrpc.client.ServerProxy('http://localhost:8080')
        except Exception as e:
            print("Client: " + str(e))

        self.data1 = b'this is a data block\n'
        self.h1 = hashlib.sha256(self.data1).hexdigest()
        self.data2 = b'this is another data block\n'
        self.h2 = hashlib.sha256(self.data2).hexdigest()

    def tearDown(self):
        self.server.terminate()
        # have to wait, otherwise subprocess is still running
        self.server.wait()

    def test_0_ping(self):
        self.assertTrue(self.client.surfstore.ping())

    def test_1_putblock(self):
        status = self.client.surfstore.putblock(self.data1)
        self.assertTrue(status)

    def test_2_getblock(self):
        status = self.client.surfstore.putblock(self.data1)
        data = self.client.surfstore.getblock(self.h1)
        self.assertEqual(data, self.data1)

    def test_3_hasblocks(self):
        status = self.client.surfstore.putblock(self.data1)
        in_list = [self.h1, self.h2]
        out_list = self.client.surfstore.hasblocks(in_list)
        self.assertEqual(out_list, [self.h1])        

    def test_4_updatefile(self):
        status = self.client.surfstore.updatefile("test.txt", 1, [self.h1, self.h2])
        self.assertTrue(status)
        status = self.client.surfstore.updatefile("test.txt", 1, [self.h2, self.h1])
        self.assertFalse(status)
        status = self.client.surfstore.updatefile("test.txt", 5, [self.h2, self.h1])
        self.assertFalse(status)

    def test_5_getfileinfomap(self):
        status = self.client.surfstore.updatefile("test.txt", 1, [self.h1, self.h2])
        infomap = self.client.surfstore.getfileinfomap()
        self.assertEqual(infomap, {"test.txt":[1, [self.h1, self.h2]]})


if __name__ == '__main__':
    unittest.main()