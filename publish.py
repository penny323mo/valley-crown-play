import hashlib,io,json,pathlib,urllib.request,zipfile
c=json.loads(pathlib.Path('release.json').read_text())
assert c['artifact_url'].startswith('https://github.com/penny323mo/valley-crown/releases/download/')
data=urllib.request.urlopen(c['artifact_url'],timeout=120).read()
assert hashlib.sha256(data).hexdigest()==c['zip_sha256'],'ZIP hash mismatch'
z=zipfile.ZipFile(io.BytesIO(data));root=pathlib.Path('_site');dest=root/'builds'/c['build'];dest.mkdir(parents=True)
for name,digest in c['files_sha256'].items():
 assert not pathlib.PurePosixPath(name).is_absolute() and '..' not in pathlib.PurePosixPath(name).parts
 candidates=['artifacts/clean-a/'+name,'notices/'+name]
 matches=[n for n in candidates if n in z.namelist()];assert len(matches)==1,name
 b=z.read(matches[0]);assert hashlib.sha256(b).hexdigest()==digest,name
 p=dest/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
(dest/'WEB_EXPORT_MANIFEST.json').write_text(json.dumps(c,indent=2)+'\n')
(root/'.nojekyll').touch()
(root/'release.json').write_text(json.dumps(c,indent=2)+'\n')
for sub,target in [('', 'builds/'+c['build']+'/'),('play','../builds/'+c['build']+'/')]:
 p=root/sub;p.mkdir(exist_ok=True)
 (p/'index.html').write_text('<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url='+target+'"><title>Valley Crown</title><a href="'+target+'">Play Valley Crown '+c['build']+'</a>')
size=sum(p.stat().st_size for p in root.rglob('*') if p.is_file());assert size<900_000_000
print('Verified published build',c['build'],'bytes',size)
