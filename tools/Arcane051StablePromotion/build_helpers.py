from common import *
def main():
    folder=OUT/'helpers';folder.mkdir(exist_ok=True);inputs=folder/'inputs';inputs.mkdir(exist_ok=True);reports={};mapped={}
    rows=read(BASE/'build-report.json')
    for name in ['paws_player_colors.ini','paws_patch_versions.ini']:
        data=(BASE/name).read_bytes()
        if name=='paws_patch_versions.ini':
            assert data.count(BETA.encode())==1;data=data.replace(BETA.encode(),VERSION.encode())
        (folder/name).write_bytes(data)
    for name,row in rows.items():
        changed=[]
        for source,digest in row['sources'].items():
            path=Path(source);assert sha(path)==digest.upper(),source
            data=path.read_bytes();before=data
            if path.suffix.lower()=='.cs' and BETA.encode() in data:
                assert path.name.endswith('LargeMapsIdentity.cs') and data.count(BETA.encode())==1
                data=data.replace(BETA.encode(),VERSION.encode());changed.append(source)
            dest=inputs/digest/path.name;dest.parent.mkdir(exist_ok=True)
            if dest.exists():assert dest.read_bytes()==data
            else:dest.write_bytes(data)
            mapped[source]=dest
        assert len(changed)==1
        args=[]
        for arg in row['args']:
            if arg.startswith('/out:'):arg='/out:'+str(folder/name)
            elif arg in mapped:arg=str(mapped[arg])
            elif arg.startswith('/resource:'):
                path,label=arg[len('/resource:'):].rsplit(',',1);arg='/resource:'+str(mapped[path])+','+label
            args.append(arg)
        run(args);features=json.loads(run([folder/name,'--features']));assert features==dict(row['features'],patchVersion=VERSION),name
        tests={flag:run([folder/name,flag]).strip() for flag in ['--quiet-startup-self-test','--common-ui-self-test','--lobby-payload-test','--assistant-self-test','--fast-transfer-self-test']}
        reports[name]=dict(sha256=sha(folder/name),baselineSha256=row['sha256'],features=features,args=args,sources={str(mapped[p]):sha(mapped[p]) for p in row['sources']},changedSource=changed,selfTests=tests)
        print('STABLE_HELPER_PASS',name,flush=True)
    write(folder/'build-report.json',reports);print('PASS: eight helpers, 40 self-tests; only patch identity changed',flush=True)
if __name__=='__main__':main()
