"""Append a standalone native UI sound button, preserving the installed UI.
Native widget creation is provided by the common UI helper. No simulation commands.
"""
from pathlib import Path
import argparse,hashlib,json

def add_button(raw,button):
 enc='utf-16' if raw[:2] in (b'\xff\xfe',b'\xfe\xff') else 'utf-8-sig'
 text=raw.decode(enc)
 assert '[PawGoldSoundButton' not in text,'Button already present'
 start=text.index('[Game Inherit=Interface]');opening=text.index('{',start)
 depth=1;end=opening+1
 while depth:
  if text[end]=='{':depth+=1
  elif text[end]=='}':depth-=1
  end+=1
 return (text[:end-1]+'\n'+button+'\n'+text[end-1:]).encode(enc)

def main():
 p=argparse.ArgumentParser();p.add_argument('--game',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 src=Path(__file__).resolve().parent
 rel='data/UI/Game/game_interface.tgi';old=(a.game/rel).read_bytes()
 result=add_button(old,(src/'button.tgi').read_text('utf-8'))
 dest=a.out/'payload'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(result)
 icon=(src/'PawGoldSound.png').read_bytes();dest=a.out/'payload/data/UI/Game/PawGoldSound.png';dest.write_bytes(icon)
 (a.out/'button-input.json').write_text(json.dumps({'sourceGame':str(a.game),'interfaceBeforeSha256':hashlib.sha256(old).hexdigest(),'interfaceAfterSha256':hashlib.sha256(result).hexdigest(),'iconSha256':hashlib.sha256(icon).hexdigest(),'sound':'resource_gold_select','bounds1024x768':[960,490,1020,570],'sourceImage':'exec-cf4cc496-a6b1-4ecc-afc0-52a8d6a1cf9f.png','tooltip':False},indent=2))
 print('UI_SOUND_BUTTON_PREPARED; original image bytes retained; no command binding')
if __name__=='__main__':main()
