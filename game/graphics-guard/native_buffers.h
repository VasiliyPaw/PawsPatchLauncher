/* Compatibility ABI only. All resources retain native D3D9 ownership.
 * Do not infer exclusive ownership from IUnknown::Release's return value:
 * state blocks/device bindings may retain implicit resource references.
 * Retired buffer-pool experiments must not be included by product builders. */
static UINT nativeBufferFrames;
__declspec(dllexport) void WINAPI PawGpuTick(UINT world,UINT phase,UINT paused,UINT warm){(void)world;(void)phase;(void)paused;(void)warm;nativeBufferFrames++;}
__declspec(dllexport) void WINAPI PawBufferPoolPurge(void){}
__declspec(dllexport) UINT WINAPI PawBufferPoolStats(UINT*out,UINT size){if(!out||size<40)return 0;memset(out,0,40);out[9]=nativeBufferFrames;return 40;}
