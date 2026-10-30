"""Local, deterministic communication workflows. No mailbox access or sending."""
import hashlib
import json
from datetime import date, timedelta

TOOL_IDS = {f'M{i:02d}' for i in range(1, 16)}

def _hash(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()

def _result(data, summary='Lokale Auswertung erstellt.', status='READY', warnings=None, artifact=None):
    return {'status': status, 'summary': summary, 'data': data, 'checks': [{'label': 'Eingaben geprüft', 'passed': status == 'READY', 'detail': summary}], 'artifacts': ([{'name': 'entwurf.txt', 'content': artifact, 'media_type': 'text/plain'}] if artifact else []), 'warnings': warnings or []}

def _need(p, *keys):
    missing = [k for k in keys if k not in p or p[k] is None or p[k] == '' or p[k] == []]
    if missing: raise ValueError('Fehlende Angaben: ' + ', '.join(missing))

def _error(m):
    text = ' '.join(str(m.get(k, '')) for k in ('kind','subject','body','result')).lower()
    return any(x in text for x in ('ndr','delivery failure','delivery status notification','zustellfehler','unzustellbar','verarbeitungsfehler','processing error'))

def run(tool_id, p):
    if tool_id not in TOOL_IDS: return _result({}, 'Unbekanntes Werkzeug.', 'NEEDS_DATA')
    try:
        if not isinstance(p, dict): raise ValueError('Eingabe muss ein Objekt sein.')
        if tool_id == 'M01':
            _need(p, 'message', 'rules'); m=p['message']; _need(m,'id','sender','subject','body')
            if _error(m): return _result({'classification':'EXCEPTION','message_id':m['id'],'reference':m.get('reference'), 'reason':'Zustell- oder Verarbeitungsfehler'}, 'Fehler bleibt als aktive Ausnahme sichtbar.', 'EXCEPTION')
            rules=[r for r in p['rules'] if r.get('approved') is True and r.get('version') and r.get('sender','').lower()==m['sender'].lower()]
            sensitive=m.get('personal_data') or m.get('action_required') or m.get('attachments') or any(x in (m['subject']+' '+m['body']).lower() for x in ('personal','mitarbeiter','gehalt','anliegen','bitte'))
            cls='INFORMATION' if len(rules)==1 and not sensitive else 'REVIEW'
            return _result({'classification':cls,'message_id':m['id'],'body_hash':_hash(m['body']),'rule':rules[0] if cls=='INFORMATION' else None}, 'Nachricht lokal eingeordnet.', 'READY' if cls=='INFORMATION' else 'NEEDS_DECISION')
        if tool_id == 'M02':
            _need(p,'message','receipt','retention'); m=p['message']; r=p['receipt']; t=p['retention']
            if _error(m) or str(r.get('result','')).lower() in ('error','failed','failure','partial','ndr'): return _result({'archive_eligible':False,'reference':m.get('reference')},'Fehler bleibt eine aktive Ausnahme.','EXCEPTION')
            ok=r.get('result')=='success' and r.get('verified') is True and all(r.get(k) for k in ('target','timestamp')) and m.get('id') and m.get('hash') and t.get('approved') is True and t.get('version')
            return _result({'archive_eligible':bool(ok),'original':m.get('id'),'receipt':r,'retention_version':t.get('version'),'hr_case_closed':False},'Archivbeleg lokal vorbereitet.' if ok else 'Erfolg oder Aufbewahrungsregel nicht belegt.', 'READY' if ok else 'NEEDS_DATA')
        if tool_id == 'M03':
            _need(p,'messages'); out=[]
            for m in p['messages']:
                _need(m,'id','mailbox','body'); key=[m['mailbox'],m['id']]; body=_hash(m['body']); attachments=sorted(m.get('attachment_hashes',[])); questions=m.get('questions',[])
                prior=next((x for x in out if x['key']==key),None)
                same_content=lambda x: x['body_hash']==body and x['attachments']==attachments and x['questions']==questions
                identical=next((x for x in out if (x['key']==key or (m.get('internet_id') and x['internet_id']==m['internet_id'])) and same_content(x)),None)
                conflict=bool(prior and not same_content(prior))
                out.append({'key':key,'internet_id':m.get('internet_id'),'body_hash':body,'attachments':attachments,'duplicate_of':identical['key'] if identical and not conflict else None,'identity_conflict':conflict,'questions':questions,'recipients':m.get('recipients',[])})
            return _result({'messages':out},'Gleiche Quell-ID mit abweichendem Inhalt prüfen.' if any(x['identity_conflict'] for x in out) else 'Eingänge mit Herkunft und Änderungen verglichen.', 'NEEDS_DECISION' if any(x['identity_conflict'] for x in out) else 'READY')
        if tool_id == 'M04':
            _need(p,'message','role_mapping'); m=p['message']; mapping=p['role_mapping']; _need(m,'text');
            if not mapping.get('valid') or not mapping.get('role'): return _result({},'Gültige Rollenzuordnung fehlt.','NEEDS_DECISION')
            t=m['text'].lower(); action=any(x in t for x in ('bitte','frist','erledigen','prüfen'))
            return _result({'type':'TASK' if action else ('FYI' if any(x in t for x in ('zur kenntnis','fyi')) else 'REVIEW'),'owner':mapping['role'] if action else None,'reply_all':False},'Empfängerkontext ausgewertet.', 'READY' if action or 'fyi' in t or 'zur kenntnis' in t else 'NEEDS_DECISION')
        if tool_id == 'M05':
            _need(p,'questions','answers','case_id'); out=[]
            for q in p['questions']:
                _need(q,'id','text'); matches=[a for a in p['answers'] if a.get('question_id')==q['id'] and a.get('case_id')==p['case_id'] and a.get('source') and (a.get('direction','inbound') != 'inbound' or a.get('identity_confirmed') is True)]
                states={a.get('state') for a in matches}; values={str(a.get('value')) for a in matches if a.get('state')=='answered'}
                knowledge='contradictory' if 'contradictory' in states or len(values)>1 else ('answered' if 'answered' in states else 'partial' if 'partial' in states else 'open')
                outgoing=[a for a in matches if a.get('direction')=='outbound' and a.get('state')=='answered' and a.get('recipient') and a.get('recipient')==q.get('recipient') and isinstance(a.get('delivery_evidence'),dict) and a['delivery_evidence'].get('source') and a['delivery_evidence'].get('delivered') is True]
                outbound='delivered' if outgoing else 'not_delivered'
                state=('answered' if outbound=='delivered' and knowledge=='answered' else knowledge if knowledge in ('contradictory','partial') else 'open') if q.get('audience')=='external' else knowledge
                out.append({'id':q['id'],'text':q['text'],'state':state,'knowledge_state':knowledge,'outbound_state':outbound,'evidence':matches})
            return _result({'questions':out},'Fragen einzeln abgeglichen.','NEEDS_DECISION' if any(x['state']=='contradictory' for x in out) else 'NEEDS_DATA' if any(x['state'] in ('open','partial') for x in out) else 'READY')
        if tool_id == 'M06':
            _need(p,'source','speaker','message_date','days','fulfillment','today'); d=date.fromisoformat(p['message_date'])+timedelta(days=int(p['days'])); today=date.fromisoformat(p['today']); evidence=p.get('evidence'); fulfilled=isinstance(evidence,dict) and evidence.get('verified') is True and bool(evidence.get('source')) and evidence.get('fulfillment')==p['fulfillment']
            return _result({'due_date':d.isoformat(),'source':p['source'],'speaker':p['speaker'],'condition':p.get('condition'),'fulfillment':p['fulfillment'],'fulfilled':fulfilled,'reminder_due':today>=d and not fulfilled},'Zusage mit Datum und Erfüllungsbedingung erfasst.')
        if tool_id == 'M07':
            _need(p,'template','facts'); t=p['template']; _need(t,'text','version');
            if t.get('approved') is not True: return _result({},'Vorlage ist nicht freigegeben.','NEEDS_DECISION')
            facts=p['facts']; missing=[k for k,v in facts.items() if not isinstance(v,dict) or not v.get('source') or v.get('current') is not True or 'value' not in v]
            if missing: return _result({'invalid_facts':missing},'Fakten benötigen aktuelle Quellen.','NEEDS_DATA')
            import string
            fields=[f for _,f,_,_ in string.Formatter().parse(t['text']) if f is not None]
            if any(not f.isidentifier() or f not in facts for f in fields): return _result({'fields':fields},'Vorlagenfelder fehlen oder sind ungültig.','NEEDS_DATA')
            text=t['text'].format(**{k:v['value'] for k,v in facts.items()}); snap={'template':t,'facts':facts,'recipients':p.get('recipients',[])}
            return _result({'draft':text,'snapshot_hash':_hash(snap),'snapshot':snap,'sources':{k:v['source'] for k,v in facts.items()}},'Quellengebundener Entwurf erstellt.',warnings=['Versand und Empfängerprüfung sind manuell.'],artifact=text)
        if tool_id == 'M08':
            _need(p,'snapshot_hash','current_snapshot'); current=_hash(p['current_snapshot']); fresh=current==p['snapshot_hash'] and p['current_snapshot'].get('template',{}).get('approved') is True and all(f.get('current') is True and f.get('source') for f in p['current_snapshot'].get('facts',{}).values())
            return _result({'current_hash':current,'fresh':fresh},'Entwurf ist aktuell.' if fresh else 'Entwurf oder Freigaben haben sich geändert.', 'READY' if fresh else 'NEEDS_DECISION')
        if tool_id == 'M09':
            _need(p,'task_id','requester','revision'); claim=p.get('claim'); conflict=bool(claim and claim.get('active') and claim.get('owner')!=p['requester'])
            return _result({'task_id':p['task_id'],'owner':claim.get('owner') if conflict else p['requester'],'revision':p['revision'],'saved_notes':p.get('notes',[])},'Aufgabe bereits beansprucht.' if conflict else 'Lokaler Übernahmevorschlag erstellt.', 'NEEDS_DECISION' if conflict else 'READY',warnings=['Keine dauerhafte Sperre; gemeinsame Speicherung erforderlich.'])
        if tool_id == 'M10':
            _need(p,'records','search_type','query','authorized_scopes','purpose'); field={'message_id':'message_id','case_id':'case_id','personnel_number':'personnel_number','name':'name'}.get(p['search_type'])
            if not field: raise ValueError('Unbekannte Suchart.')
            found=[r for r in p['records'] if r.get('scope') in p['authorized_scopes'] and str(r.get(field,''))==str(p['query'])]
            return _result({'matches':found,'search_type':p['search_type'],'purpose':p['purpose']},'Exakte Suche im angegebenen Berechtigungsbereich abgeschlossen.')
        if tool_id == 'M11':
            _need(p,'old','new','identity_confirmed','case_id','document_type');
            if p['identity_confirmed'] is not True: return _result({},'Identität nicht bestätigt.','NEEDS_DECISION')
            changes=[{'field':k,'old':p['old'].get(k),'new':p['new'].get(k),'kind':'added' if k not in p['old'] else 'removed' if k not in p['new'] else 'changed'} for k in sorted(set(p['old'])|set(p['new'])) if p['old'].get(k)!=p['new'].get(k)]
            impacted=[x for x in p.get('dependencies',[]) if set(x.get('fields',[])) & {c['field'] for c in changes}]
            return _result({'changes':changes,'impacted':impacted},'Feldänderungen und betroffene Schritte dargestellt.')
        if tool_id == 'M12':
            _need(p,'cases','authorized_scopes'); groups={}
            for c in p['cases']:
                if c.get('scope') not in p['authorized_scopes']: continue
                _need(c,'person_id','case_id','scope'); groups.setdefault(c['person_id'],[]).append(c)
            return _result({'groups':groups},'Berechtigte Fälle nach bestätigter Person gruppiert.')
        if tool_id == 'M13':
            _need(p,'tasks','today','rule_version'); today=date.fromisoformat(p['today']); out=[]
            for t in p['tasks']:
                _need(t,'id','status'); due=date.fromisoformat(t['due']) if t.get('due') else None; reasons=[]
                if due and due<today and t.get('deadline_approved'): reasons.append('genehmigte Frist überfällig')
                if t.get('blocked_steps',0)>0: reasons.append('abhängige Schritte blockiert')
                if t['status']=='EXCEPTION': reasons.append('aktive Ausnahme')
                out.append({**t,'priority_reasons':reasons,'priority':len(reasons)})
            out.sort(key=lambda x:(-x['priority'],x.get('due','9999'),str(x['id'])))
            return _result({'tasks':out,'as_of':p['today'],'rule_version':p['rule_version']},'Arbeitsübersicht mit erklärten Prioritäten erstellt.')
        if tool_id == 'M14':
            _need(p,'absence','tasks'); a=p['absence']; _need(a,'start','end','deputy'); start=date.fromisoformat(a['start']); end=date.fromisoformat(a['end']);
            if end<start: raise ValueError('Abwesenheitsende liegt vor Beginn.')
            if a.get('confirmed') is not True: return _result({},'Abwesenheit ist nicht bestätigt.','NEEDS_DECISION')
            items=[{'id':t.get('id'),'due':t.get('due'),'next_action':t.get('next_action'),'source':t.get('source'),'requires_authority':bool(t.get('sensitive')),'state':t.get('state')} for t in p['tasks']]
            return _result({'deputy':a['deputy'],'items':items},'Übergabeübersicht erstellt.',warnings=['Keine Zugriffsrechte oder Entscheidungsbefugnisse übertragen.'])
        if tool_id == 'M15':
            _need(p,'content','source','owner','version','scope','valid_from'); date.fromisoformat(p['valid_from']); approved=p.get('approved') is True
            return _result({'content':p['content'],'source':p['source'],'owner':p['owner'],'version':p['version'],'scope':p['scope'],'valid_from':p['valid_from'],'state':'APPROVED' if approved else 'CANDIDATE','dependent_drafts':p.get('dependent_drafts',[])},'Wissensversion lokal erfasst.' if approved else 'Wissenskandidat benötigt Freigabe.', 'READY' if approved else 'NEEDS_DECISION')
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError) as e:
        return _result({}, 'Ungültige oder fehlende Eingaben: '+str(e), 'NEEDS_DATA')

SAMPLES = {
'M01':{'message':{'id':'m1','sender':'news@example.org','subject':'Info','body':'Rundbrief'},'rules':[{'sender':'news@example.org','version':'1','approved':True}]},
'M02':{'message':{'id':'m1','hash':'abc'},'receipt':{'result':'success','verified':True,'target':'job1','timestamp':'2026-01-01'},'retention':{'approved':True,'version':'1'}},
'M03':{'messages':[{'id':'m1','mailbox':'hr','body':'Hallo'}]},
'M04':{'message':{'text':'Bitte prüfen'},'role_mapping':{'valid':True,'role':'HR'}},
'M05':{'case_id':'c1','questions':[{'id':'q1','text':'Wann?'}],'answers':[{'question_id':'q1','case_id':'c1','source':'m1','state':'answered','value':'morgen','identity_confirmed':True}]},
'M06':{'source':'m1','speaker':'NL','message_date':'2026-10-01','days':7,'fulfillment':'Unterlagen','today':'2026-10-10'},
'M07':{'template':{'text':'Guten Tag {name}', 'version':'1','approved':True},'facts':{'name':{'value':'Alex','source':'c1','current':True}}},
'M08':{'snapshot_hash':_hash({'template':{'approved':True},'facts':{}}),'current_snapshot':{'template':{'approved':True},'facts':{}}},
'M09':{'task_id':'t1','requester':'HR','revision':'1'},
'M10':{'records':[{'case_id':'c1','scope':'Nord'}],'search_type':'case_id','query':'c1','authorized_scopes':['Nord'],'purpose':'Fallarbeit'},
'M11':{'old':{'date':'2026-01-01'},'new':{'date':'2026-01-02'},'identity_confirmed':True,'case_id':'c1','document_type':'Antrag'},
'M12':{'cases':[{'person_id':'p1','case_id':'c1','scope':'Nord'}],'authorized_scopes':['Nord']},
'M13':{'tasks':[{'id':'t1','status':'EXCEPTION','due':'2026-10-01','deadline_approved':True}],'today':'2026-10-30','rule_version':'1'},
'M14':{'absence':{'start':'2026-11-01','end':'2026-11-10','deputy':'HR2','confirmed':True},'tasks':[{'id':'t1','next_action':'Prüfen'}]},
'M15':{'content':'Vorgang prüfen','source':'Handbuch 1','owner':'HR','version':'1','scope':'Nord','valid_from':'2026-01-01','approved':True},
}
