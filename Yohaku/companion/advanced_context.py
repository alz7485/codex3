"""Bounded condition state: continuous observations, recovery events and meeting gaps."""
import json
import math

TEMPORAL_KINDS = {'metric_sustained','metric_transition','idle_return'}
EVENT_KINDS = {'metric_transition','idle_return'}


def condition_key(condition): return json.dumps(condition,sort_keys=True,separators=(',',':'))


def children(condition):
    yield condition
    for child in condition.get('conditions',()): yield from children(child)


def in_range(value,minimum,maximum):
    return type(value) in (int,float) and math.isfinite(value) and value>=minimum and (maximum is None or value<=maximum)


class ConditionTimeline:
    def __init__(self):
        self.states={}; self.previous=None; self.serial=0

    def update(self,clock,metrics,rules):
        conditions={condition_key(c):c for r in rules if r['trigger']=='auto' and r['enabled']
                    for c in children(r['condition']) if c['kind'] in TEMPORAL_KINDS}
        if self.previous is not None and not 0<=clock-self.previous<=15: self.states.clear()
        self.previous=clock
        self.states={k:v for k,v in self.states.items() if k in conditions}
        result={}
        for key,c in conditions.items():
            state=self.states.setdefault(key,{'since':None,'armed':False,'event':0,'until':0})
            kind=c['kind']; value=metrics.get('idle_minutes' if kind=='idle_return' else c['metric'])
            valid=type(value) in (int,float) and math.isfinite(value)
            if kind=='metric_sustained':
                active=in_range(value,c['minimum'],c['maximum'])
                state['since']=(clock if state['since'] is None else state['since']) if active else None
                result[key]={'active':active and clock-state['since']>=c['duration_minutes']*60,'event':0}
                continue
            if not valid:
                state.update(since=None,armed=False,event=0,until=0)
            else:
                if kind=='idle_return':
                    from_range=value>=c['idle_minutes']; to_range=value<1
                else:
                    from_range=in_range(value,c['minimum'],c['maximum'])
                    to_range=in_range(value,c['to_minimum'],c['to_maximum'])
                if from_range:
                    if state['since'] is None: state['since']=clock
                    if kind=='idle_return' or clock-state['since']>=c['duration_minutes']*60:state['armed']=True
                else: state['since']=None
                if to_range and state['armed']:
                    self.serial+=1
                    state.update(event=self.serial,until=clock+c['window_minutes']*60,armed=False)
            result[key]={'active':bool(state['event']) and clock<state['until'],'event':state['event']}
        return result


def meeting_metrics(events,now,gap_minutes=10):
    ordered=sorted(events,key=lambda e:e.start)
    total=0; end=None
    for event in ordered:
        if end is None or event.start>end:
            total+=(event.end-event.start).total_seconds()/60
        elif event.end>end: total+=(event.end-end).total_seconds()/60
        end=max(end,event.end) if end else event.end
    remaining=[e for e in ordered if e.end>now]
    groups=[]
    for event in ordered:
        if not groups or (event.start-groups[-1][1]).total_seconds()>gap_minutes*60:
            groups.append([1,event.end])
        else:
            groups[-1][0]+=1; groups[-1][1]=max(groups[-1][1],event.end)
    groups=[group for group in groups if group[1]>now]
    current_end=max((e.end for e in remaining if e.start<=now),default=now)
    future=[e.start for e in remaining if e.start>now]
    return {'daily_meeting_minutes':total,'consecutive_meetings':groups[0][0] if groups else 0,
            'next_meeting_gap_minutes':max(0,(min(future)-current_end).total_seconds()/60) if future else None}
