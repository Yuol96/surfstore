import os
import unittest
import xmlrpc.client
import subprocess
import time
import hashlib
import shutil
import pdb

import client
import server

SLEEPTIME = 1

class TestAll(unittest.TestCase):
    def setUp(self):
        # setup cloud server on subprocess
        bashCommand = "python server.py"
        self.server = subprocess.Popen(bashCommand.split())
        # wait to set up cloud
        time.sleep(SLEEPTIME)
        # setup bot
        try:
            self.bot  = xmlrpc.client.ServerProxy('http://localhost:8080')
        except Exception as e:
            print("bot: " + str(e))
        # prepare for client1
        self.basedir1 = './client1/' 
        if os.path.exists(self.basedir1):
            shutil.rmtree(self.basedir1)
        os.mkdir(self.basedir1)
        # prepare for client2
        self.basedir2 = './client2/' 
        if os.path.exists(self.basedir2):
            shutil.rmtree(self.basedir2)
        os.mkdir(self.basedir2)

    def tearDown(self):
        self.server.terminate()
        # have to wait, otherwise subprocess cannot close properly
        self.server.wait()
        # remove basedir
        shutil.rmtree(self.basedir1)
        shutil.rmtree(self.basedir2)

    def test_rubric1(self):
        '''
        Sanity checking: calling sync with an empty base 
        directory and empty server doesn’t result in an 
        error, etc.
        '''
        blocksize = 1024
        # launch a client
        bashCommand = "python client.py localhost:8080 "+self.basedir1+' '+str(blocksize)
        process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
        # wait to launch
        time.sleep(SLEEPTIME)
        output, error = process.communicate()
        # close client
        process.terminate()
        process.wait()

        # check no error
        self.assertNotIn(b'Errno', output)

    def test_rubric2(self):
        '''
        New local files sync to the cloud.
        '''
        # create a file in local
        blocksize = 1024
        fname = 'file1.txt'
        # Verify that your program works with binary files 
        # (images, video, etc).
        content = b'this is file1'*256
        h_list = []
        for i in range(0, len(content), blocksize):
            h_list.append(hashlib.sha256(content[i:i+blocksize]).hexdigest())
        with open(self.basedir1+fname, 'wb') as f:
            f.write(content)

        # launch a client
        bashCommand = "python client.py localhost:8080 "+self.basedir1+' '+str(blocksize)
        process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
        # wait to launch
        time.sleep(SLEEPTIME)
        output, error = process.communicate()
        # close client
        process.terminate()
        process.wait()

        # check file in the cloud
        infomap = self.bot.surfstore.getfileinfomap()
        self.assertTrue(len(infomap) == 1)
        self.assertIn(fname, infomap)
        self.assertEqual(infomap[fname], [1, h_list])
    
    def test_rubric3(self):
        '''
        Files on the server that aren’t on the client sync 
        to the client.
        '''
        # create a file in cloud
        # Make sure your program uses the block size specified 
        # in the command line argument. Don’t hard-code a 4096 
        # byte block size.
        blocksize = 2048
        fname = 'file1.txt'
        content = b'this is file1'*512
        h_list = []
        for i in range(0, len(content), blocksize):
            block = content[i:i+blocksize]
            h_list.append(hashlib.sha256(block).hexdigest())
            self.bot.surfstore.putblock(block)
        self.bot.surfstore.updatefile(fname, 1, h_list)

        # launch a client
        bashCommand = "python client.py localhost:8080 "+self.basedir1+' '+str(blocksize)
        process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
        # wait to launch
        time.sleep(SLEEPTIME)
        output, error = process.communicate()
        # close client
        process.terminate()
        process.wait()

        # check file in the local
        self.assertTrue(os.path.exists(self.basedir1+fname))
        with open(self.basedir1+fname, 'rb') as f:
            content_local = f.read()
        self.assertEqual(content_local, content)
        book = client.parseIndexFile(self.basedir1)
        self.assertIn(fname, book)
        self.assertEqual(book[fname], [1, h_list])

    def test_rubric4(self):
        '''
        Mixtures of new and missing files sync properly–the 
        new files get uploaded to the cloud, and the missing 
        files get downloaded properly.
        '''
        # create a file in the cloud
        blocksize = 1024
        fname1 = 'file1.txt'
        content1 = b'this is file1'*256
        h_list1 = []
        for i in range(0, len(content1), blocksize):
            block = content1[i:i+blocksize]
            h_list1.append(hashlib.sha256(block).hexdigest())
            self.bot.surfstore.putblock(block)
        self.bot.surfstore.updatefile(fname1, 1, h_list1)

        # create a file in local
        fname2 = 'file2.txt'
        content2 = b'this is file2'*256
        h_list2 = []
        for i in range(0, len(content2), blocksize):
            block = content2[i:i+blocksize]
            h_list2.append(hashlib.sha256(block).hexdigest())
        with open(self.basedir1+fname2, 'wb') as f:
            f.write(content2)

        # launch a client
        bashCommand = "python client.py localhost:8080 "+self.basedir1+' '+str(blocksize)
        process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
        # wait to launch
        time.sleep(SLEEPTIME)
        output, error = process.communicate()
        # close client
        process.terminate()
        process.wait()

        # check file in the cloud
        infomap = self.bot.surfstore.getfileinfomap()
        self.assertTrue(len(infomap) == 2)
        self.assertIn(fname1, infomap)
        self.assertEqual(infomap[fname1], [1, h_list1])
        self.assertIn(fname2, infomap)
        self.assertEqual(infomap[fname2], [1, h_list2])

        # check file in the local
        self.assertTrue(os.path.exists(self.basedir1+fname1))
        with open(self.basedir1+fname1, 'rb') as f:
            content_local = f.read()
        self.assertEqual(content_local, content1)
        # Make sure that your program generates/reads/uses a 
        # local index.txt file.
        self.assertTrue(os.path.exists(self.basedir1+'index.txt'))
        book = client.parseIndexFile(self.basedir1)
        self.assertIn(fname1, book)
        self.assertEqual(book[fname1], [1, h_list1])
        self.assertIn(fname2, book)
        self.assertEqual(book[fname2], [1, h_list2])

    def test_rubric5(self):
        '''
        if the cloud has changes to a local file, those 
        changes get downloaded properly. If the local client 
        has changes that aren’t on the cloud, those changes 
        get uploaded properly.
        '''
        # create a file in the cloud
        blocksize = 1024
        fname1 = 'file1.txt'
        content1 = b'this is file1'*256
        h_list1 = []
        for i in range(0, len(content1), blocksize):
            block = content1[i:i+blocksize]
            h_list1.append(hashlib.sha256(block).hexdigest())
            self.bot.surfstore.putblock(block)
        self.bot.surfstore.updatefile(fname1, 1, h_list1)

        # create a file in local
        fname2 = 'file2.txt'
        content2 = b'this is file2'*256
        h_list2 = []
        for i in range(0, len(content2), blocksize):
            block = content2[i:i+blocksize]
            h_list2.append(hashlib.sha256(block).hexdigest())
        with open(self.basedir1+fname2, 'wb') as f:
            f.write(content2)

        # launch a client
        bashCommand = "python client.py localhost:8080 "+self.basedir1+' '+str(blocksize)
        process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
        # wait to launch
        time.sleep(SLEEPTIME)
        output, error = process.communicate()
        # close client
        process.terminate()
        process.wait()

        # change in the cloud
        fname1 = 'file1.txt'
        content1 = b'this is file1 with changes'*256
        h_list1 = []
        for i in range(0, len(content1), blocksize):
            block = content1[i:i+blocksize]
            h_list1.append(hashlib.sha256(block).hexdigest())
            self.bot.surfstore.putblock(block)
        self.bot.surfstore.updatefile(fname1, 2, h_list1)

        # change in local
        fname2 = 'file2.txt'
        content2 = b'this is file2 with changes'*256
        h_list2 = []
        for i in range(0, len(content2), blocksize):
            block = content2[i:i+blocksize]
            h_list2.append(hashlib.sha256(block).hexdigest())
        with open(self.basedir1+fname2, 'wb') as f:
            f.write(content2)
        
        # launch a client to sync changes
        bashCommand = "python client.py localhost:8080 "+self.basedir1+' '+str(blocksize)
        process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
        # wait to launch
        time.sleep(SLEEPTIME)
        output, error = process.communicate()
        # close client
        process.terminate()
        process.wait()

        # check file in the cloud
        infomap = self.bot.surfstore.getfileinfomap()
        self.assertIn(fname1, infomap)
        self.assertEqual(infomap[fname1], [2, h_list1])
        self.assertIn(fname2, infomap)
        self.assertEqual(infomap[fname2], [2, h_list2])

        # check file in the local
        self.assertTrue(os.path.exists(self.basedir1+fname1))
        with open(self.basedir1+fname1, 'rb') as f:
            content_local = f.read()
        self.assertEqual(content_local, content1)
        book = client.parseIndexFile(self.basedir1)
        self.assertIn(fname1, book)
        self.assertEqual(book[fname1], [2, h_list1])
        self.assertIn(fname2, book)
        self.assertEqual(book[fname2], [2, h_list2])
    
    def test_rubric6(self):
        '''
        Your client and server handle the case where multiple 
        clients have modified a file concurrently, and the 
        above described rules are followed.
        '''
        # create a file in the cloud
        blocksize = 1024
        fname = 'file1.txt'
        content = b'this is file1'*256
        h_list = []
        for i in range(0, len(content), blocksize):
            block = content[i:i+blocksize]
            h_list.append(hashlib.sha256(block).hexdigest())
            self.bot.surfstore.putblock(block)
        self.bot.surfstore.updatefile(fname, 1, h_list)

        # launch a client1
        bashCommand = "python client.py localhost:8080 "+self.basedir1+' '+str(blocksize)
        process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
        # wait to launch
        time.sleep(SLEEPTIME)
        output, error = process.communicate()
        # close client1
        process.terminate()
        process.wait()

        # launch a client2
        bashCommand = "python client.py localhost:8080 "+self.basedir2+' '+str(blocksize)
        process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
        # wait to launch
        time.sleep(SLEEPTIME)
        output, error = process.communicate()
        # close client1
        process.terminate()
        process.wait()

        # client1 make local change1
        content1 = b'this is file1 with changes from client1'*256
        h_list1 = []
        for i in range(0, len(content1), blocksize):
            block = content1[i:i+blocksize]
            h_list1.append(hashlib.sha256(block).hexdigest())
        with open(self.basedir1+fname, 'wb') as f:
            f.write(content1)

        # client2 make local change2
        content2 = b'this is file1 with changes from client2'*256
        h_list2 = []
        for i in range(0, len(content2), blocksize):
            block = content2[i:i+blocksize]
            h_list2.append(hashlib.sha256(block).hexdigest())
        with open(self.basedir2+fname, 'wb') as f:
            f.write(content2)

        # launch a client1
        bashCommand = "python client.py localhost:8080 "+self.basedir1+' '+str(blocksize)
        process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
        # wait to launch
        time.sleep(SLEEPTIME)
        output, error = process.communicate()
        # close client1
        process.terminate()
        process.wait()

        # launch a client2
        bashCommand = "python client.py localhost:8080 "+self.basedir2+' '+str(blocksize)
        process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
        # wait to launch
        time.sleep(SLEEPTIME)
        output, error = process.communicate()
        # close client1
        process.terminate()
        process.wait()

        # check file in the cloud
        infomap = self.bot.surfstore.getfileinfomap()
        self.assertIn(fname, infomap)
        self.assertEqual(infomap[fname], [2, h_list1])

        # check file in the client1
        self.assertTrue(os.path.exists(self.basedir1+fname))
        with open(self.basedir1+fname, 'rb') as f:
            content_local = f.read()
        self.assertEqual(content_local, content1)
        book = client.parseIndexFile(self.basedir1)
        self.assertIn(fname, book)
        self.assertEqual(book[fname], [2, h_list1])

        # check file in the client1
        self.assertTrue(os.path.exists(self.basedir2+fname))
        with open(self.basedir2+fname, 'rb') as f:
            content_local = f.read()
        self.assertEqual(content_local, content1)
        book = client.parseIndexFile(self.basedir2)
        self.assertIn(fname, book)
        self.assertEqual(book[fname], [2, h_list1])


if __name__ == '__main__':
    unittest.main()