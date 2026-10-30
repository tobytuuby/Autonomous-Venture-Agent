#!/usr/bin/env python3
"""Online SQLite backup plus bounded artifact snapshots, immutable manifest and verification."""
import argparse,datetime,hashlib,json,os,pathlib,sqlite3,tarfile,tempfile,shutil,fcntl

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
 return h.hexdigest()

def snapshot(sources,destination,identity):
 dest=pathlib.Path(destination).resolve()
 if not dest.is_dir() or not any(dest == pathlib.Path(parts[1]) or pathlib.Path(parts[1]) in dest.parents for line in open('/proc/mounts') if (parts:=line.split()) and parts[2] in ('nfs','nfs4')):raise RuntimeError('destination must be beneath mounted NFS filesystem')
 with open(dest/'.sqlite-backup.lock','a+') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
  with tempfile.TemporaryDirectory(prefix='sqlite-backup-') as work:
   stage=pathlib.Path(work); entries=[]
   for source in sources:
    root=pathlib.Path(source)
    if not root.exists():raise RuntimeError('source missing: '+str(root))
    files=[root] if root.is_file() else sorted(p for p in root.rglob('*') if p.is_file() and not p.is_symlink() and '.cache' not in p.parts and p.suffix in ('.sqlite','.db','.json','.jsonl','.md'))
    for path in files:
     if path.name.endswith(('-wal','-shm','-journal')):continue
     if not path.resolve().is_relative_to(root.resolve() if root.is_dir() else root.parent.resolve()):raise RuntimeError('source path escapes root')
     if path.is_symlink():raise RuntimeError('symlink denied')
     rel=path.relative_to(root) if root.is_dir() else pathlib.Path(path.name)
     name=hashlib.sha256(str(root).encode()).hexdigest()[:12]+'/'+str(rel)
     out=stage/'data'/name;out.parent.mkdir(parents=True,exist_ok=True)
     if path.suffix in ('.sqlite','.db'):
      with sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True,timeout=20) as conn,sqlite3.connect(out) as target:
       conn.backup(target,pages=100,sleep=0.05)
      with sqlite3.connect(out) as check:
       if check.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise RuntimeError('sqlite integrity failed')
      kind='sqlite-online'
     else:
      shutil.copy2(path,out);kind='file'
     entries.append(dict(source=str(path),archive='data/'+name,sha256=sha(out),bytes=out.stat().st_size,kind=kind))
   manifest=dict(schema=1,identity=identity,created_utc=stamp,entries=entries)
   (stage/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
   target=dest/(identity+'-'+stamp+'.tar.gz')
   if target.exists():raise RuntimeError('collision')
   tmp=dest/('.'+target.name+'.partial')
   try:
    with tarfile.open(tmp,'w:gz') as tf:
     tf.add(stage/'manifest.json',arcname='manifest.json')
     for entry in entries:tf.add(stage/entry['archive'],arcname=entry['archive'])
    with tarfile.open(tmp,'r:gz') as tf:
     for entry in entries:
      actual=hashlib.sha256()
      with tf.extractfile(entry['archive']) as f:
       for c in iter(lambda:f.read(1048576),b''):actual.update(c)
      if actual.hexdigest()!=entry['sha256']:raise RuntimeError('archive checksum mismatch')
    os.replace(tmp,target)
   finally:
    if tmp.exists():tmp.unlink()
   print(json.dumps(dict(backup=str(target),sha256=sha(target),entries=len(entries),bytes=target.stat().st_size)))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--destination',required=True);p.add_argument('--identity',required=True);p.add_argument('--source',action='append',required=True)
 a=p.parse_args();snapshot(a.source,a.destination,a.identity)
