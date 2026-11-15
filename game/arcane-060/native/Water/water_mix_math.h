/* Ordered native alpha-over realizes the desired premultiplied mixture. */
static float water_layer_alpha(const float*w,const float*a,unsigned n,unsigned own){
 unsigned j;float sum=0,other=0,den;for(j=0;j<n;j++)sum+=w[j];if(sum<.000001f||w[own]<.000001f)return 0;
 for(j=own+1;j<n;j++)other+=w[j]/sum*a[j];den=1-other;return den>.000001f?(w[own]/sum*a[own])/den:0;
}
