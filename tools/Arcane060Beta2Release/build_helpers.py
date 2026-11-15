from context import *
import shutil
def main():
 D=O/'helpers/source';D.mkdir(parents=True,exist_ok=True);reports=read(B1/'helpers/build-report.json');parts=read(LOSS/'packed.json')
 for f in(B1/'helpers/source').glob('*.cs'):shutil.copy2(f,D/f.name)
 f=D/'25-LargeMapsIdentity.cs';s=f.read_text();assert '0.6.0-beta.1'in s;f.write_text(s.replace('0.6.0-beta.1',VERSION))
 f=D/'PawRuntimeStartup.cs';s=f.read_text();anchor=' static void Validate(string game) {';assert anchor in s
 extra='''
 static void ValidateTextures(string game) {
  string[] names={NAMES};long[] sizes={SIZES};uint[] stamps={STAMPS};
  string startup=Path.Combine(game,"startup","autoexec.txt");string mounted=File.Exists(startup)?File.ReadAllText(startup):"";
  for(int i=0;i<names.Length;i++){
   string path=Path.Combine(game,names[i]);if(!File.Exists(path)||new FileInfo(path).Length!=sizes[i])throw new InvalidDataException("Paw's Patch terrain textures are missing or incomplete. Apply the update in the launcher.");
   using(var input=new BinaryReader(File.OpenRead(path))){if(input.ReadUInt32()!=0x4B434754||input.ReadUInt32()!=2||input.ReadUInt32()!=3)throw new InvalidDataException("Paw's Patch terrain archive header differs. Apply the update in the launcher.");input.BaseStream.Position=26;if(input.ReadUInt32()!=stamps[i])throw new InvalidDataException("Paw's Patch terrain archive version differs. Apply the update in the launcher.");}
   bool found=mounted.Split(new[]{'\\r','\\n'},StringSplitOptions.RemoveEmptyEntries).Any(line=>String.Equals(line.Trim(),"adddepot "+names[i],StringComparison.OrdinalIgnoreCase));if(!found)throw new InvalidDataException("Paw's Patch terrain textures are not connected. Apply the update in the launcher.");
  }
 }
'''.replace('{NAMES}','{'+','.join('"'+Path(p['path']).name+'"'for p in parts)+'}').replace('{SIZES}','{'+','.join(str(p['size'])+'L'for p in parts)+'}').replace('{STAMPS}','{'+','.join('0x'+p['stamp']+'u'for p in parts)+'}')
 s=s.replace(anchor,extra+anchor+'\n  ValidateTextures(game);');f.write_text(s)
 result={};resources=O/'helpers/resources';resources.mkdir(exist_ok=True)
 for name,row in reports.items():
  target=O/'helpers'/name;args=[]
  for arg in row['args']:
   if arg.startswith('/out:'):arg='/out:'+str(target)
   elif arg.lower().endswith('.cs'):arg=str(D/Path(arg).name)
   elif arg.startswith('/resource:'):
    path,label=arg[10:].rsplit(',',1);original=Path(path);dest=resources/(sha(original)+'-'+original.name)
    if not dest.exists():shutil.copy2(original,dest)
    arg='/resource:'+str(dest)+','+label
   args.append(arg)
  run(args,O/'helpers'/(name+'.build.log'));shutil.copy2(B1/'helpers/paws_player_colors.ini',target.parent/'paws_player_colors.ini')
  features=json.loads(run([target,'--features']));expected=dict(row['features']);expected['patchVersion']=VERSION;assert features==expected,(name,'feature drift')
  checks={}
  for flag in ['--quiet-startup-self-test','--common-ui-self-test','--lobby-payload-test','--assistant-self-test','--fast-transfer-self-test']:checks[flag]=run([target,flag]).strip()
  sources=[Path(a)for a in args if a.lower().endswith('.cs')]+[Path(a[10:].rsplit(',',1)[0])for a in args if a.startswith('/resource:')]
  result[name]=dict(sha256=sha(target),baselineSha256=row['sha256'],features=features,args=args,sources={str(f):sha(f)for f in sources},selfTests=checks)
  print('BETA2_HELPER_PASS',name,flush=True)
 write(O/'helpers/build-report.json',result)
if __name__=='__main__':main()
