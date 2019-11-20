import os
import unittest
import shutil
import hashlib
import shutil

import client

class TestClient(unittest.TestCase):
    def setUp(self):
        self.basedir = './test1/'
        if os.path.exists(self.basedir):
            shutil.rmtree(self.basedir)
        os.mkdir(self.basedir)

    def tearDown(self):
        shutil.rmtree(self.basedir)

    def test_1_scandir(self):        
        blocksize = 2048
        # chunkify and get hash value
        true_fname2hashlist = {}
        true_hash2block = {}
        # create file1
        fname1 = "file1.txt"
        content1 = b"this is file1.\n"*1024
        with open(self.basedir+fname1, 'wb') as f:
            f.write(content1)
        h_list = []
        for i in range(0, len(content1), blocksize):
            block = content1[i:i+blocksize]
            h = hashlib.sha256(block).hexdigest()
            true_hash2block[h] = block
            h_list.append(h)
        true_fname2hashlist[fname1] = h_list
        # create file2, binary file
        fname2 = "file2.mp4"
        content2 = b"this is another file.\n"*1024
        with open(self.basedir+fname2, 'wb') as f:
            f.write(content2)
        h_list = []
        for i in range(0, len(content2), blocksize):
            block = content2[i:i+blocksize]
            h = hashlib.sha256(block).hexdigest()
            true_hash2block[h] = block
            h_list.append(h)
        true_fname2hashlist[fname2] = h_list
        # check scan
        fname2hashlist, hash2block = client.scandir(self.basedir, blocksize)
        self.assertEqual(fname2hashlist, true_fname2hashlist)
        self.assertEqual(hash2block, true_hash2block)

    def test_2_parseIndexFile(self):
        blocksize = 2048
        # create file1
        fname1 = "file1.txt"
        content1 = b"this is file1.\n"*1024
        with open(self.basedir+fname1, 'wb') as f:
            f.write(content1)
        h_list = []
        for i in range(0, len(content1), blocksize):
            block = content1[i:i+blocksize]
            h = hashlib.sha256(block).hexdigest()
            h_list.append(h)
        # create index.txt
        with open(self.basedir+'index.txt', 'w') as f:
            f.write(' '.join(map(str, [fname1, 1] + h_list)) + '\n')

        # test
        rst = client.parseIndexFile(self.basedir)
        self.assertEqual(rst, {fname1:[1, h_list]})

    def test_3_download(self):
        pass

    def test_4_mergeCloudToLocal(self):
        pass

    def test_5_isSame(self):
        h1 = hashlib.sha256(b"haha").hexdigest()
        h2 = hashlib.sha256(b"xixi").hexdigest()
        # true case
        self.assertTrue(client.isSame([h1, h2], [h1, h2]))
        self.assertTrue(client.isSame([], []))
        # false case
        self.assertFalse(client.isSame([h1], [h1, h2]))
        self.assertFalse(client.isSame([h1, h2], [h2, h1]))

    def test_6_upload(self):
        pass

    def test_7_mergeLocalToCloud(self):
        pass

    def test_8_dumpLocalIndex(self):
        pass

    def test_9_synchronize(self):
        pass
    

if __name__ == '__main__':
    unittest.main()