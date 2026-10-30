"""Pure previews for administrative orchestration; no external action is performed."""
from datetime import date, timedelta
from collections import defaultdict

TOOL_IDS = {f'O{i:02}' for i in range(1, 15)}
SAMPLES = {
'O01': {'event': {'type':'end', 'person_id':'P1','date':'2027-06-30','source':'export'}, 'rule': {'id':'R1','version':'1','status':'APPROVED','trigger':'end','steps':[{'id':'clarify','owner':'HR','lead_days':30}]}},
'O02': {'target_date':'2027-04-01','tasks':[{'id':'contract','duration_days':3,'depends_on':[]},{'id':'signature','duration_days':2,'depends_on':['contract']}]},
'O03': {'needs':[{'field':'location','purpose':'contract'}], 'sources':[{'field':'location','name':'export','allowed':True,'proven':True}]},
'O04': {'fields':[{'name':'remote'},{'name':'address','when':{'field':'remote','equals':True}}], 'facts':{'remote':True}},
'O05': {'changed':['address'],'dependencies':{'address':['contract'],'contract':['signature']}},
'O06': {'decisions':[{'id':'D1','owner':'HR','topic':'contract','impact':'start date'}]},
'O07': {'scenarios':[{'name':'A','cost':100,'days':5},{'name':'B','cost':150,'days':3}]},
'O08': {'date':'2027-06-01','scope':'contracts','delegations':[{'delegate':'HR2','scope':'contracts','from':'2027-05-01','to':'2027-06-30','approved':True}]},
'O09': {'tasks':[{'id':'A','status':'blocked','blocker':'missing date','owner':'HR','next_step':'request date'}]},
'O10': {'questions':[{'field':'date','recipient':'HR'},{'field':'location','recipient':'HR'}], 'answers':{'date':'2027-01-01'}},
'O11': {'corrections':[{'field':'location','from':'A','to':'B','confirmed':True},{'field':'location','from':'A','to':'B','confirmed':True}]},
'O12': {'rule':{'field':'type','op':'eq','value':'end'},'cases':[{'id':'C1','type':'end'}]},
'O13': {'commitments':[{'id':'C1','owner':'HR','due':'2027-01-01','conditions_met':True,'proof':'signed record'}]},
'O14': {'cases':[{'status':'closed','duration_days':4,'rework':True,'cause':'missing data'},{'status':'open','duration_days':2,'rework':False}]},
}

def _out(status, summary, data=None, checks=None, warnings=None):
    return {'status':status,'summary':summary,'data':data or {},'checks':checks or [],'artifacts':[],'warnings':warnings or []}

def _pred(rule, facts):
    field, op = rule.get('field'), rule.get('op','eq')
    if op not in ('eq','ne','in','exists'): raise ValueError('Unbekanntes Prädikat')
    if not field: raise ValueError('Feld fehlt')
    if op == 'exists': return field in facts and facts[field] is not None
    if field not in facts: return None
    if op == 'eq': return facts[field] == rule.get('value')
    if op == 'ne': return facts[field] != rule.get('value')
    if not isinstance(rule.get('value'),list): raise ValueError('in erwartet eine Liste')
    return facts[field] in rule['value']

def _graph(tasks):
    ids = {t['id'] for t in tasks}
    if len(ids) != len(tasks): raise ValueError('Doppelte Task-ID')
    deps = {t['id']:t.get('depends_on',[]) for t in tasks}
    if any(d not in ids for ds in deps.values() for d in ds): raise ValueError('Unbekannte Abhängigkeit')
    state, order = {}, []
    def visit(n):
        if state.get(n)==1: raise ValueError('Zyklus im Abhängigkeitsgraph')
        if state.get(n)==2: return
        state[n]=1
        for d in deps[n]: visit(d)
        state[n]=2; order.append(n)
    for n in deps: visit(n)
    return order, deps

def run(tool_id, payload):
    if tool_id not in TOOL_IDS: return _out('EXCEPTION','Unbekanntes Werkzeug')
    try: return _run(tool_id,payload)
    except (KeyError, ValueError, TypeError, OverflowError) as e: return _out('EXCEPTION','Eingabe oder Regel ungültig',{'error':str(e)})

def _run(t,p):
    if t=='O01':
        e=p.get('event',{}); r=p.get('rule',{})
        if not all(e.get(k) for k in ('type','person_id','date','source')) or e.get('ambiguous'): return _out('NEEDS_DATA','Ereignis oder Person nicht eindeutig')
        if r.get('status')!='APPROVED' or r.get('trigger')!=e['type'] or not r.get('id') or not r.get('version'): return _out('NEEDS_DECISION','Passende freigegebene Regel fehlt')
        dt=date.fromisoformat(e['date']); steps=r.get('steps',[])
        if not steps: return _out('NEEDS_DATA','Regelschritte fehlen')
        _graph(steps)
        existing=set(p.get('existing_keys',[])); tasks=[]
        for s in steps:
            if not s.get('owner'): return _out('NEEDS_DATA','Aufgabenrolle fehlt')
            key=':'.join([e['person_id'],r['id'],r['version'],s['id'],str(e.get('revision','1'))]); days=int(s.get('lead_days',0))
            if days<0: raise ValueError('Negativer Vorlauf')
            tasks.append({'id':s['id'],'key':key,'existing':key in existing,'due':str(dt-timedelta(days=days)),'owner':s['owner'],'depends_on':s.get('depends_on',[]),'reason':r['id']})
        return _out('READY','Aufgabenvorschau berechnet',{'tasks':tasks},warnings=['Keine Aufgabe wurde angelegt.'])
    if t=='O02':
        tasks=p.get('tasks',[])
        if not p.get('target_date') or not tasks: return _out('NEEDS_DATA','Zieltermin und Aufgaben erforderlich')
        order,deps=_graph(tasks)
        if any('duration_days' not in x or x['duration_days'] is None for x in tasks): return _out('NEEDS_DATA','Dauerannahmen fehlen')
        if any(type(x['duration_days']) is not int for x in tasks): raise ValueError('Dauer muss eine ganze Zahl sein')
        by={x['id']:x for x in tasks}; target=date.fromisoformat(p['target_date']); ends={n:target for n in order}; starts={}
        for n in reversed(order):
            duration=int(by[n].get('duration_days',0))
            if duration<0: raise ValueError('Negative Dauer')
            starts[n]=ends[n]-timedelta(days=duration)
            for d in deps[n]: ends[d]=min(ends[d],starts[n])
        critical=[]; n=min(order,key=lambda x:starts[x]); critical.append(n)
        while True:
            successors=[x for x in order if n in deps[x] and starts[x]==ends[n]]
            if not successors: break
            n=sorted(successors)[0]; critical.append(n)
        return _out('NEEDS_DECISION' if any(not x.get('confirmed',False) for x in tasks) else 'READY','Rückwärtsplan als Vorschlag berechnet',{'schedule':[{'id':n,'start':str(starts[n]),'end':str(ends[n]),'assumption':not by[n].get('confirmed',False)} for n in order],'earliest_start':str(min(starts.values())),'critical_path':critical},warnings=['Kalendertage; keine Kalender- oder Aufgabenänderung.'])
    if t=='O03':
        needs=p.get('needs',[]); sources=p.get('sources',[]); facts=p.get('facts',{}); plan=[]
        if not needs: return _out('NEEDS_DATA','Datenbedarf fehlt')
        if any(not n.get('purpose') for n in needs): return _out('NEEDS_DECISION','Zweck für Datenbedarf fehlt')
        for n in needs:
            f=n['field']; options=[s['name'] for s in sources if s.get('field')==f and s.get('allowed') and s.get('proven')]
            plan.append({'field':f,'resolved':f in facts and facts[f] is not None,'eligible_sources':options,'next_step':'vorliegenden Fakt prüfen' if f in facts else ('Quelle kontrolliert prüfen' if options else 'manuell beschaffen')})
        return _out('READY' if all(x['resolved'] for x in plan) else 'NEEDS_DATA','Beschaffungsplan erstellt',{'needs':plan},warnings=['Es wurden keine Quellen abgefragt.'])
    if t=='O04':
        facts=p.get('facts',{}); fields=[]; unknown=[]
        for f in p.get('fields',[]):
            cond=f.get('when'); active=True if not cond else _pred({'field':cond['field'],'op':'eq','value':cond.get('equals')},facts)
            if active is None: unknown.append(f['name'])
            elif active: fields.append({'name':f['name'],'value':facts.get(f['name']),'missing':f['name'] not in facts or facts[f['name']] is None})
        if not p.get('fields'): return _out('NEEDS_DATA','Formularschema fehlt')
        return _out('NEEDS_DATA' if unknown or any(x['missing'] for x in fields) else 'READY','Formularentwurf erstellt',{'fields':fields,'unknown_conditions':unknown})
    if t=='O05':
        deps=p.get('dependencies',{}); seen=set(p.get('changed',[])); queue=list(seen)
        if not queue: return _out('NEEDS_DATA','Änderung fehlt')
        while queue:
            for n in deps.get(queue.pop(0),[]):
                if n not in seen: seen.add(n); queue.append(n)
        return _out('READY','Transitive Folgen berechnet',{'changed':p['changed'],'affected':sorted(seen-set(p['changed']))})
    if t=='O06':
        groups=defaultdict(list)
        for d in p.get('decisions',[]): groups[(d.get('owner',''),d.get('topic',''))].append(d)
        if not groups: return _out('NEEDS_DATA','Entscheidungen fehlen')
        return _out('NEEDS_DECISION','Entscheidungspakete zur Prüfung erstellt',{'bundles':[{'owner':k[0],'topic':k[1],'decisions':v} for k,v in sorted(groups.items())]})
    if t=='O07':
        scenarios=p.get('scenarios',[])
        if not scenarios or any('cost' not in x or 'days' not in x for x in scenarios): return _out('NEEDS_DATA','Szenarien mit Kosten und Dauer erforderlich')
        for x in scenarios:
            if float(x['cost'])<0 or float(x['days'])<0: raise ValueError('Negative Szenariowerte')
        return _out('NEEDS_DECISION','Szenarien vergleichbar; Entscheidung bleibt bei der Fachrolle',{'scenarios':scenarios})
    if t=='O08':
        if not p.get('scope') or not p.get('date'): return _out('NEEDS_DATA','Datum und Geltungsbereich fehlen')
        day=date.fromisoformat(p['date']); matches=[d for d in p.get('delegations',[]) if d.get('approved') and d.get('scope')==p['scope'] and date.fromisoformat(d['from'])<=day<=date.fromisoformat(d['to']) and d.get('delegate')]
        return _out('READY' if len(matches)==1 else 'NEEDS_DECISION','Vertretungsprüfung abgeschlossen',{'matches':matches})
    if t=='O09':
        tasks=p.get('tasks',[])
        if not tasks: return _out('NEEDS_DATA','Aufgaben fehlen')
        _graph(tasks)
        if any(not x.get('status') for x in tasks): return _out('NEEDS_DATA','Aufgabenstatus fehlt')
        blocked=[x for x in tasks if x.get('status') in ('blocked','waiting')]
        return _out('NEEDS_DATA' if blocked else 'READY','Blockadenübersicht erstellt',{'blockers':blocked})
    if t=='O10':
        groups=defaultdict(list); answers=p.get('answers',{})
        if not p.get('questions'): return _out('NEEDS_DATA','Fragen fehlen')
        for q in p.get('questions',[]):
            if q.get('field') not in answers or answers[q['field']] is None: groups[q.get('recipient','')].append(q['field'])
        return _out('NEEDS_DATA' if groups else 'READY','Offene Fragen gebündelt',{'bundles':[{'recipient':k,'fields':sorted(set(v))} for k,v in sorted(groups.items())]})
    if t=='O11':
        counts=defaultdict(int)
        for c in p.get('corrections',[]):
            if c.get('confirmed'): counts[(str(c.get('field')),str(c.get('from')),str(c.get('to')))]+=1
        proposals=[{'field':k[0],'from':k[1],'to':k[2],'count':v,'status':'DRAFT'} for k,v in sorted(counts.items()) if v>=2]
        return _out('NEEDS_DECISION' if proposals else 'NEEDS_DATA','Regelvorschläge aus bestätigten Korrekturen',{'proposals':proposals},warnings=['Keine Regel aktiviert.'])
    if t=='O12':
        if not p.get('rule') or not p.get('cases'): return _out('NEEDS_DATA','Regel und historische Fälle erforderlich')
        results=[{'case_id':c.get('id'),'match':_pred(p['rule'],c)} for c in p['cases']]
        return _out('NEEDS_DATA' if any(x['match'] is None for x in results) else 'READY','Regel nur simuliert',{'results':results},warnings=['Keine Regel aktiviert oder Fälle verändert.'])
    if t=='O13':
        cs=p.get('commitments',[])
        if not cs: return _out('NEEDS_DATA','Verpflichtungen fehlen')
        results=[{'id':c.get('id'),'complete':bool(c.get('owner') and c.get('due') and c.get('conditions_met') is True and c.get('proof')),'missing':[k for k in ('owner','due','conditions_met','proof') if not c.get(k)]} for c in cs]
        return _out('READY' if all(x['complete'] for x in results) else 'NEEDS_DATA','Verpflichtungen geprüft',{'commitments':results})
    cases=p.get('cases',[])
    if not cases: return _out('NEEDS_DATA','Messdaten fehlen; keine Basiswerte erfunden')
    durations=[x['duration_days'] for x in cases if x.get('duration_days') is not None]; causes=defaultdict(int)
    for c in cases:
        if c.get('cause'): causes[c['cause']]+=1
    return _out('READY','Kennzahlen aus gelieferten Fällen berechnet',{'count':len(cases),'closed':sum(x.get('status')=='closed' for x in cases),'rework':sum(x.get('rework') is True for x in cases),'mean_duration_days':sum(durations)/len(durations) if durations else None,'duration_sample_count':len(durations),'causes':dict(causes)})
