/* Exact trailing-whitespace operation, scanning backward. The game's own
 * locale classifier and copy-on-write resize remain authoritative. */
typedef int(__cdecl*TrimSpace)(unsigned);
static unsigned trim_end(const wchar_t*s,TrimSpace space){unsigned n=0;while(s[n])n++;while(n&&space((unsigned)s[n-1]))n--;return n;}
static unsigned trim_forward(const wchar_t*s,TrimSpace space){unsigned n=0,last=0;while(s[n]){if(!space((unsigned)s[n]))last=n+1;n++;}return last;}
static unsigned trimEnabled,trimValidate,trimCompared,trimMismatch;
static void trim_init(void){char v[4];trimEnabled=GetEnvironmentVariableA("PAWS_STARTUP_TRIM",v,4)==1&&v[0]=='1';trimValidate=GetEnvironmentVariableA("PAWS_STARTUP_TRIM_VALIDATE",v,4)==1&&v[0]=='1';}
static unsigned FC trim_line(void*s,void*d){
 wchar_t*text=*(wchar_t**)s;unsigned n;TrimSpace space=(TrimSpace)(base+0x3f3ea2);
 typedef unsigned(FC*TrimOriginal)(void*,void*);
 typedef unsigned(FC*TrimResize)(void*,void*,unsigned);
 if(!trimEnabled)return((TrimOriginal)(base+0x497cd))(s,d);
 n=trim_end(text,space);
 if(trimValidate){trimCompared++;if(n!=trim_forward(text,space)){trimMismatch++;return((TrimOriginal)(base+0x497cd))(s,d);}}
 if(text[n])((TrimResize)(base+0x4981b))(s,d,n);
 return(unsigned)s;
}
