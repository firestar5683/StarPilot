"""Offline reserve sensitivity model; no audio, routes, GPU or device operations.
This models buffer arithmetic/guards, not callback timing or actual hold viability.
"""
import json


def simulate(initial, jobs=20, reject_first=False):
    buffer=float(initial);minimum=buffer;holds=0;underflows=0;accepted=0;estimate=30.;elapsed=0.
    for job in range(jobs):
        if buffer>90:
            elapsed+=buffer-90;buffer=90.
        required=estimate+10
        if buffer<required:
            buffer+=24;holds+=1
        deadline_buffer=buffer
        durations=[23.,26.] if reject_first and job==0 else [25.55 if job%2 else 24.5]
        spent=0.
        for index,duration in enumerate(durations):
            if deadline_buffer-spent<estimate+10:
                if buffer<max(40,estimate+12):buffer+=24;holds+=1
                break
            # Runtime holds during in-flight work once the accepted reserve reaches 20s.
            if buffer-duration<20:
                before=max(0.,buffer-20);elapsed+=before;spent+=before;duration-=before;buffer-=before
                minimum=min(minimum,buffer);buffer+=24;holds+=1
            buffer-=duration;spent+=duration;elapsed+=duration;minimum=min(minimum,buffer)
            underflows+=int(buffer<0)
            estimate=max(30.,durations[index]*1.2)
            if index==len(durations)-1:buffer+=28;accepted+=1
    return dict(initial_seconds=initial,accepted_jobs=accepted,holds=holds,
                underflows_model_only=underflows,minimum_buffer_seconds=round(minimum,2),elapsed_seconds=round(elapsed,2))


if __name__=='__main__':
    print(json.dumps({scenario:[simulate(initial,reject_first=retry) for initial in (82,54,40,30)]
                      for scenario,retry in [('all_accepted',False),('first_job_rejected_retry_49s',True)]},indent=2))
