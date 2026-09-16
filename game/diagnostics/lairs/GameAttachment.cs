using System;
using System.Collections.Generic;

namespace PawLairDiagnostics
{
    internal static class GameAttachment
    {
        // Steam's short-lived bootstrap k2.exe is not the game to observe.
        // Re-enumerate until one current process passes all readiness checks.
        internal static T Wait<T>(Func<T[]> enumerate, Func<T,bool> ready, Action<T> release,
            Func<bool> cancelled, Func<long> milliseconds, Action<int> sleep, long timeout) where T:class
        {
            long start=milliseconds();
            while(!cancelled() && milliseconds()-start<timeout)
            {
                T[] candidates=enumerate();T selected=null;bool keep=false;
                try
                {
                    foreach(T candidate in candidates)
                    {
                        if(!ready(candidate)) continue;
                        if(selected!=null) throw new InvalidOperationException("Запущено несколько готовых копий игры. Оставь одну для диагностики.");
                        selected=candidate;
                    }
                    if(selected!=null){keep=true;return selected;}
                }
                finally{foreach(T candidate in candidates)if(!keep || !Object.ReferenceEquals(candidate,selected))release(candidate);}
                sleep(250);
            }
            return null;
        }
    }
}
