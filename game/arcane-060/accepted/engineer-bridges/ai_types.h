/* Transient intentions only. Native actors, paid metadata and orders save normally. */
#define BAI_PLAYERS 96
#define BAI_FAILED 6
typedef struct {float x,y,until;} BridgeAIFailure;
typedef struct {
 U kingdom,worker,site,slot,source,target,kind,material,goalCursor;
 float x,y,next,cooldown,started,progress,health,nextSafety;
 U built[4],builtCursor,failedCursor;
 float builtX[4],builtY[4];
 BridgeAIFailure failed[BAI_FAILED];
 float goalX,goalY;
} BridgeAIPlayer;
typedef struct {
 U world,cursor,planning,company,source,target,kind,goalType,goalKey;
 U sample,samples,bestN,bestMaterial,bestPoints[32],goalCursor;
 float nextStep,started,sx,sy,tx,ty,baseline,best,lowerBound;
 U scans,candidates,accepted,finished,aborted,duplicates,budgetRejected,dangerRejected,unknownPaths,guardedCommands,resumed;
 U probe;float probeX,probeY,probeDX,probeDY;
 U lastSAICommand,abortReason;
 U refusals[8];
 float candidateX,candidateY,approach,after;
 BridgeAIPlayer players[BAI_PLAYERS];
} BridgeAI;
