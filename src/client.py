import argparse
import xmlrpc.client

from pathlib import Path
import hashlib
import pdb

def scandir(basedir: str, blocksize: int):
	fname2hashlist = {}
	hash2block = {}

	basedir = Path(basedir)
	for p in basedir.iterdir():
		if p.is_dir():
			print('[WARN] found dir: {}'.format(p.name))
			continue

		if p.name == 'index.txt':
			continue

		fname = p.name
		with p.open('rb') as f:
			tmp = f.read(blocksize)
			while len(tmp) > 0:
				h = hashlib.sha256(tmp).hexdigest()
				lst = fname2hashlist.get(fname, [])
				lst.append(h)
				fname2hashlist[fname] = lst
				hash2block[h] = tmp
				tmp = f.read(blocksize)

	return fname2hashlist, hash2block

def parseIndexFile(basedir: str):
	basedir = Path(basedir)
	fpath = basedir/'index.txt'

	dct = {}

	if not fpath.exists():
		# # create index.txt file
		# with fpath.open('w') as f:
		# 	pass
		return {}

	with fpath.open() as f:
		for line in f:
			lst = line.strip().split()
			if len(lst) < 2:
				print('[ERROR] wrong index.txt format')
				continue
			fname, version, *hashlist = lst
			dct[fname] = [int(version), hashlist]

	return dct

def download(client, basedir, fname, hashlist):
	"""
	Download the blocks associated with that file, and reconstitute that file in the base directory.
	Corner case: the file on the server marked as 'deleted' (i.e. len(hashlist) == 1 and hashlist[0] == 0)
	"""
	basedir = Path(basedir)

	if len(hashlist) == 1 and hashlist[0] == 0:
		# File was deleted on the remote side.
		# When a new file was created and then deleted on the remote side by another client, 
		# the file would be missing on this client. Thus, we need `missing_ok=True`
		if (basedir / fname).exists():
			(basedir / fname).unlink() 
	else:
		with (basedir / fname).open('wb') as hd:
			for h in hashlist:
				b = client.surfstore.getblock(h)
				hd.write(b.data)


def mergeCloudToLocal(client, localIndex, remoteIndex, basedir):
	for fname in remoteIndex:
		rmVersion, rmHashlist = remoteIndex[fname]
		lcVersion, lcHashlist = localIndex.get(fname, [0, []])
		if rmVersion > lcVersion:
			download(client, basedir, fname, rmHashlist)
			localIndex[fname] = [rmVersion, rmHashlist]

def isSame(hashlist1, hashlist2) -> bool:
	"""
	Compare two hashlists.
	"""
	if len(hashlist1) != len(hashlist2):
		return False
	for h1, h2 in zip(hashlist1, hashlist2):
		if h1 != h2:
			return False
	return True

def upload(client, fname, version, hashlist, hash2block, localIndex, basedir):
	"""
	Upload the blocks corresponding to this file to the server, then update the server with the new FileInfo.
	- If that update is successful, then the client should update its local index.
	- If fails with a version error, download the cloud version and update the localIndex

	* Corner Case: hashlist == [0] * 
	"""
	if not (len(hashlist) == 1 and hashlist[0] == 0):
		inHashlist = set(client.surfstore.hasblocks(hashlist))
		for h in hashlist:
			if h not in inHashlist:
				b = hash2block[h]
				client.surfstore.putblock(b)
	
	isUpdated = client.surfstore.updatefile(fname, version, hashlist)
	if isUpdated:
		localIndex[fname] = [version, hashlist]
	else:
		newRemoteIndex = client.surfstore.getfileinfomap()
		newVersion, newHashlist = newRemoteIndex[fname]
		download(client, basedir, fname, newHashlist)
		localIndex[fname] = [newVersion, newHashlist]

def mergeLocalToCloud(client, localIndex, basedir, blocksize, remoteIndex):
	fname2hashlist, hash2block = scandir(basedir, blocksize)
	# Handle files that are modified or created
	for fname in fname2hashlist:
		lcVersion, lcHashlist = localIndex.get(fname, [0, []])
		hashlist = fname2hashlist[fname]
		if not isSame(hashlist, lcHashlist):
			upload(client, fname, lcVersion+1, hashlist, hash2block, localIndex, basedir)

	# Handle files that are deleted
	deletedFnames = set(localIndex.keys()) - set(fname2hashlist.keys())
	for fname in deletedFnames:
		if remoteIndex[fname][1] != [0]:
			lcVersion, lcHashlist = localIndex[fname]
			upload(client, fname, lcVersion+1, [0], hash2block, localIndex, basedir)

def dumpLocalIndex(localIndex, basedir):
	basedir = Path(basedir)
	with (basedir/'index.txt').open('w') as hd:
		for fname in localIndex:
			lcVersion, lcHashlist = localIndex[fname]
			hd.write(' '.join(map(str, [fname, lcVersion] + lcHashlist)) + '\n')

def synchronize(client, basedir: str, blocksize: int):
	localIndex = parseIndexFile(basedir)
	remoteIndex = client.surfstore.getfileinfomap()

	mergeCloudToLocal(client, localIndex, remoteIndex, basedir)
	mergeLocalToCloud(client, localIndex, basedir, blocksize, remoteIndex)
	dumpLocalIndex(localIndex, basedir)

if __name__ == "__main__":

	parser = argparse.ArgumentParser(description="SurfStore client")
	parser.add_argument('hostport', help='host:port of the server')
	parser.add_argument('basedir', help='The base directory')
	parser.add_argument('blocksize', type=int, help='Block size')
	args = parser.parse_args()

	try:
		client  = xmlrpc.client.ServerProxy('http://{}'.format(args.hostport))
		# Test ping
		client.surfstore.ping()
		print("Ping() successful")

		print('Start Synchronization...')
		synchronize(client, args.basedir, args.blocksize)

	except Exception as e:
		print("Client: " + str(e))
