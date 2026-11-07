// Local targeted follow-up; use analyzeHeadless -readOnly -noanalysis.
//@category Kohan
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import java.nio.file.*;

public class KohanHotJoinExport extends GhidraScript {
 public void run() throws Exception {
  Path out=Paths.get(getScriptArgs()[0]);Files.createDirectories(out);
  DecompInterface d=new DecompInterface();d.openProgram(currentProgram);
  long[] rvas={0x29811c,0x297f78,0x1c557c,0x1c550a,0x1c5540,0x1c54e6};
  for(long rva:rvas){
   var at=currentProgram.getImageBase().add(rva);
   Function f=getFunctionAt(at);
   if(f==null){disassemble(at);f=createFunction(at,"Paw_HotJoinTarget_"+Long.toHexString(rva));}
   if(f==null){println("MISSING "+at);continue;}
   var result=d.decompileFunction(f,60,monitor);
   if(result.decompileCompleted())Files.writeString(out.resolve(String.format("%08x.c",rva)),result.getDecompiledFunction().getC());
   StringBuilder asm=new StringBuilder();
   var it=currentProgram.getListing().getInstructions(f.getBody(),true);
   while(it.hasNext()){var i=it.next();asm.append(i.getAddress()).append("  ").append(i).append("\n");}
   Files.writeString(out.resolve(String.format("%08x.asm",rva)),asm.toString());
   println("EXPORTED "+at+" "+f.getName());
  }
  d.dispose();
 }
}
