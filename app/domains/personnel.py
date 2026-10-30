"""Local personnel case previews. No external system is changed."""
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import difflib
import json
import string

TOOL_IDS = {f'P{i:02}' for i in range(1, 19)} - {'P13'}

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), default=str).encode()).hexdigest()

def result(status, summary, data=None, checks=None, artifacts=None, warnings=None):
    return {'status': status, 'summary': summary, 'data': data or {}, 'checks': checks or [], 'artifacts': artifacts or [], 'warnings': warnings or []}

def check(label, passed, detail):
    return {'label': label, 'passed': bool(passed), 'detail': str(detail)}

def require(p, fields):
    missing = [f for f in fields if f not in p or p[f] is None or p[f] == '' or p[f] == []]
    if missing: raise ValueError('Fehlende Angaben: ' + ', '.join(missing))

def dec(v):
    if isinstance(v, (float, bool)): raise ValueError('Dezimalwerte als Zeichenkette oder ganze Zahl angeben')
    x = Decimal(str(v))
    if not x.is_finite(): raise ValueError('Ungültiger Dezimalwert')
    return x

def day(v): return date.fromisoformat(v)

def period(start, end):
    a, b = day(start), day(end)
    if b < a: raise ValueError('Zeitraum endet vor Beginn')
    return a, b

def overlaps(periods):
    spans = sorted((period(x['start'], x['end']) for x in periods))
    return any(a[1] >= b[0] for a,b in zip(spans,spans[1:]))

def approval(p, scope):
    h = digest(scope)
    a = p.get('approval', {})
    ok = isinstance(a, dict) and bool(a.get('by')) and a.get('scope_hash') == h
    return h, ok

def render(p):
    require(p, ['template', 'template_version', 'template_approved', 'fields'])
    if p['template_approved'] is not True: return result('NEEDS_DECISION', 'Vorlage ist nicht freigegeben.')
    keys = [name for _, name, _, _ in string.Formatter().parse(p['template']) if name is not None]
    if any(not name.isidentifier() for name in keys): raise ValueError('Nur einfache Platzhalter zulässig')
    missing = [k for k in keys if k not in p['fields'] or p['fields'][k] is None]
    if missing: raise ValueError('Fehlende Platzhalter: ' + ', '.join(missing))
    text = p['template'].format_map(p['fields'])
    return result('READY', 'Freigegebene Vorlage als Entwurf befüllt.', {'template_version': p['template_version'], 'document_hash': hashlib.sha256(text.encode()).hexdigest()}, artifacts=[{'name':'entwurf.txt','content':text,'media_type':'text/plain'}], warnings=['Dokument ist ein Entwurf; Versand und Unterzeichnung erfolgen manuell.'])

def run(tool_id, payload):
    if tool_id not in TOOL_IDS: return result('EXCEPTION', 'Unbekanntes Werkzeug.')
    try:
        if not isinstance(payload, dict): raise ValueError('Eingabe muss ein Objekt sein')
        p = payload
        if tool_id in ('P01','P02'):
            fields = ['person_id','old','new','unit','valid_from'] + (['basis'] if tool_id == 'P01' else ['model'])
            require(p, fields); day(p['valid_from'])
            old,new = dec(p['old']),dec(p['new'])
            if old < 0 or new < 0: raise ValueError('Negative Werte sind nicht zulässig')
            scope={k:p[k] for k in fields}
            if tool_id == 'P02':
                if p['model'] not in ('befristet', 'unbefristet'): raise ValueError('Modell muss befristet oder unbefristet sein')
                if p['unit'] != 'Stunden/Woche': raise ValueError('Einheit muss Stunden/Woche sein')
                if not (0 < old <= 168 and 0 < new <= 168): raise ValueError('Wochenstunden müssen größer als 0 und höchstens 168 sein')
                if p['model'] == 'befristet' and not p.get('valid_to'): raise ValueError('Befristete Änderung benötigt valid_to')
                if p['model'] == 'unbefristet' and p.get('valid_to'): raise ValueError('Unbefristete Änderung darf kein Enddatum haben')
            if tool_id == 'P02' and p.get('valid_to'):
                period(p['valid_from'],p['valid_to']); scope['valid_to']=p['valid_to']
            h,ok=approval(p,scope)
            data={'scope_hash':h,'old':str(old),'new':str(new),'difference':str(new-old),'unit':p['unit']}
            if scope.get('valid_to'):
                data['expiry_review_date']=scope['valid_to']
                data['expiry_task']={'due_date':scope['valid_to'],'action':'Ende und anschließendes Stundenmodell manuell prüfen','person_id':p['person_id']}
            return result('READY' if ok else 'NEEDS_DECISION','Änderungsvorschau erstellt.' if ok else 'Passende Freigabe für Änderung erforderlich.',data,[check('Freigabe zum Inhalt',ok,h)],warnings=['Keine externe Änderung durchgeführt.'])
        if tool_id == 'P03':
            require(p,['round_id','revision','people','valid_from','currency','basis','rule_version','mode']); day(p['valid_from'])
            if not isinstance(p['people'],list): raise ValueError('people muss eine Liste sein')
            if p['mode'] not in ('manual','percentage'): raise ValueError('mode muss manual oder percentage sein')
            if p['mode']=='percentage':
                require(p,['percentage']); percentage=dec(p['percentage'])
                if percentage < -100: raise ValueError('Prozentsatz ergibt negativen Betrag')
            counts = {x.get('person_id'): sum(1 for y in p['people'] if y.get('person_id') == x.get('person_id')) for x in p['people']}
            rows=[]
            for person in p['people']:
                require(person,['person_id','old','current'] + (['new'] if p['mode']=='manual' else []))
                old,current=dec(person['old']),dec(person['current'])
                new=dec(person['new']) if p['mode']=='manual' else old*(Decimal(1)+percentage/Decimal(100))
                if min(old,current,new) < 0: raise ValueError('Negative Beträge sind nicht zulässig')
                rounded=new.quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
                conflict=counts[person['person_id']] > 1 or current != old
                scope={'round_id':p['round_id'],'revision':p['revision'],'person_id':person['person_id'],'old':str(old),'new':str(rounded),'valid_from':p['valid_from'],'currency':p['currency'],'basis':p['basis'],'rule_version':p['rule_version'],'mode':p['mode'],'rounding':'HALF_UP'}
                if p['mode']=='percentage': scope['percentage']=str(percentage)
                h,ok=approval(person,scope)
                rows.append({'person_id':person['person_id'],'old':str(old),'current':str(current),'new':str(rounded),'scope':scope,'scope_hash':h,'status':'NEEDS_DECISION' if conflict or not ok else 'READY','conflict':conflict})
            return result('READY' if all(r['status']=='READY' for r in rows) else 'NEEDS_DECISION','Gehaltsrunde einzeln geprüft.',{'people':rows},warnings=['Keine externe Änderung durchgeführt.'])
        if tool_id == 'P04':
            require(p,['person_id','fact_id','old','new','valid_from','reason','history']); day(p['valid_from'])
            if p.get('valid_to'): period(p['valid_from'],p['valid_to'])
            scope={k:p[k] for k in ('person_id','fact_id','old','new','valid_from','reason')}
            if p.get('valid_to'): scope['valid_to']=p['valid_to']
            h,ok=approval(p,scope)
            return result('READY' if ok else 'NEEDS_DECISION','Korrektur als neue Version vorbereitet.',{'history':p['history'],'proposed_version':scope,'scope_hash':h},[check('Freigabe',ok,h)])
        if tool_id in ('P05','P12'): return render(p)
        if tool_id == 'P06':
            require(p,['document_hash','version','person_id','return_evidence'])
            e=p['return_evidence']; require(e,['document_hash','version','person_id','method'])
            matches=all(p[k]==e[k] for k in ('document_hash','version','person_id'))
            signed=matches and e['method']=='verified_signature' and bool(e.get('evidence_id'))
            return result('READY' if signed else 'NEEDS_DECISION','Rücklauf geprüft.' if signed else 'Signatur oder Dokumentzuordnung muss manuell geklärt werden.',{'matched':matches,'signature_verified':signed},[check('Dokument und Version',matches,'Hash, Version und Person'),check('Signaturnachweis',signed,'OCR oder Bild genügt nicht')],warnings=['Kein Versand oder Signaturdienst konfiguriert.'])
        if tool_id == 'P07':
            require(p,['person_id','measure','draft','rule_version','representative','consultation_evidence'])
            e=p['consultation_evidence']; ok=isinstance(e,dict) and e.get('representative')==p['representative'] and e.get('measure_hash')==digest(p['draft']) and e.get('status')=='completed'
            return result('READY' if ok else 'NEEDS_DECISION','Beteiligungsnachweis geprüft.',{'draft_hash':digest(p['draft'])},[check('Beteiligung',ok,'Nachweis muss Vertretung und Entwurf zuordnen')],warnings=['Keine rechtliche Wirkung aus Fristablauf abgeleitet.'])
        if tool_id in ('P08','P09'):
            require(p,['person_id','periods','evidence']);
            if tool_id=='P09': require(p,['previous_version','decision'])
            if not isinstance(p['periods'],list): raise ValueError('periods muss eine Liste sein')
            conflict=overlaps(p['periods'])
            return result('NEEDS_DECISION' if conflict else 'READY','Zeiträume geprüft.',{'periods':p['periods'],'previous_version':p.get('previous_version')},[check('Überschneidung',not conflict,'Inklusive Start- und Enddatum')],warnings=['Keine gesetzliche Anspruchsentscheidung.'])
        if tool_id == 'P10':
            require(p,['person_id','return_date','hours','role','leave_periods','approval']); d=day(p['return_date']); dec(p['hours'])
            conflict=any(a <= d <= b for a,b in (period(x['start'],x['end']) for x in p['leave_periods']))
            scope={k:p[k] for k in ('person_id','return_date','hours','role')}; h,ok=approval(p,scope)
            return result('READY' if ok and not conflict else 'NEEDS_DECISION','Rückkehrdaten geprüft.',{'scope_hash':h},[check('Rückkehr außerhalb Abwesenheit',not conflict,p['return_date']),check('Freigabe',ok,h)])
        if tool_id == 'P11':
            require(p,['person_id','field','old','new','evidence','effective_date']); day(p['effective_date'])
            allowed={'address','phone','email','emergency_contact','bank_account','name'}; ok=p['field'] in allowed
            return result('READY' if ok else 'NEEDS_DECISION','Stammdatenänderung geprüft.',{'field':p['field'],'old':p['old'],'new':p['new']},[check('Zulässiges Feld',ok,p['field'])],warnings=['Keine externe Änderung durchgeführt.'])
        if tool_id == 'P14':
            require(p,['person_id','qualification','evidence','valid_until','confirmed_by','rule_version','as_of']); end=day(p['valid_until']); today=day(p['as_of']); ok=end>=today
            return result('READY' if ok else 'NEEDS_DECISION','Qualifikationsnachweis geprüft.',{'valid_until':p['valid_until'],'days_remaining':(end-today).days},[check('Gültigkeit',ok,p['valid_until'])])
        if tool_id == 'P15':
            require(p,['person_id','end_date','departure_type','decision_evidence','tasks']); day(p['end_date'])
            if not isinstance(p['tasks'],list): raise ValueError('tasks muss eine Liste sein')
            scope={k:p[k] for k in ('person_id','end_date','departure_type')}; h=digest(scope)
            evidence=p['decision_evidence']
            decision_ok=isinstance(evidence,dict) and bool(evidence.get('by')) and bool(evidence.get('evidence_id')) and evidence.get('scope_hash')==h
            pending=[]
            for t in p['tasks']:
                require(t,['name'])
                if t.get('confirmed') is not True or not t.get('confirmed_by') or not t.get('evidence_id'): pending.append(t)
            return result('READY' if decision_ok and not pending else 'NEEDS_DECISION','Austrittsentscheidung und Aufgaben anhand lokaler Angaben geprüft.',{'decision_scope_hash':h,'pending_tasks':pending,'tasks':p['tasks']},[check('Entscheidungsnachweis',decision_ok,h),check('Aufgabennachweise',not pending,len(pending))],warnings=['Angaben sind lokale Bestätigungen und wurden nicht extern verifiziert.','Keine arbeitsrechtliche Entscheidung getroffen.'])
        if tool_id == 'P16':
            require(p,['person_id','absence_type','start','end','approval','handover']); period(p['start'],p['end'])
            scope={k:p[k] for k in ('person_id','absence_type','start','end')}; h,ok=approval(p,scope)
            return result('READY' if ok else 'NEEDS_DECISION','Abwesenheit und Übergabe vorbereitet.',{'scope_hash':h,'handover':p['handover']},[check('Freigabe',ok,h)])
        if tool_id == 'P17':
            require(p,['person_id','documents'])
            docs=p['documents'];
            if len(docs)<2: raise ValueError('Mindestens zwei Dokumentversionen erforderlich')
            versions=[]
            for d in docs:
                require(d,['version','content']); h=hashlib.sha256(d['content'].encode()).hexdigest(); versions.append({'version':d['version'],'hash':h,'signature_verified':bool(d.get('signature_evidence') and d['signature_evidence'].get('document_hash')==h and d['signature_evidence'].get('version')==d['version'] and d['signature_evidence'].get('method')=='verified_signature' and d['signature_evidence'].get('evidence_id'))})
            return result('READY','Vertragsversionen verglichen.',{'versions':versions,'changed':len({v['hash'] for v in versions})>1,'diff': '\n'.join(difflib.unified_diff(docs[0]['content'].splitlines(), docs[-1]['content'].splitlines(), fromfile=str(docs[0]['version']), tofile=str(docs[-1]['version']), lineterm=''))})
        if tool_id == 'P18':
            require(p,['case_type','decision_fields','revision','role','delegation','valid_from','valid_to']); period(p['valid_from'],p['valid_to'])
            scope={k:p[k] for k in ('case_type','decision_fields','revision','role','delegation','valid_from','valid_to')}; h,ok=approval(p,scope)
            return result('READY' if ok else 'NEEDS_DECISION','Freigabeumfang geprüft.',{'scope_hash':h},[check('Freigabe zum Umfang',ok,h)])
    except (ValueError, TypeError, KeyError, InvalidOperation, AttributeError) as exc:
        return result('NEEDS_DATA',str(exc))

# Examples are deliberately synthetic and editable.
SAMPLES = {
'P01':{'person_id':'P1','old':'4000.00','new':'4200.00','unit':'EUR','basis':'Monat','valid_from':'2026-01-01'},
'P02':{'person_id':'P1','old':'40','new':'30','unit':'Stunden/Woche','model':'befristet','valid_from':'2026-01-01','valid_to':'2026-06-30'},
'P03':{'round_id':'R1','revision':1,'valid_from':'2026-01-01','currency':'EUR','basis':'Monat','rule_version':'1','mode':'percentage','percentage':'2.5','people':[{'person_id':'P1','old':'2987.35','current':'2987.35'}]},
'P04':{'person_id':'P1','fact_id':'F1','old':'30','new':'32','valid_from':'2025-01-01','reason':'Korrektur','history':[{'value':'30'}]},
'P05':{'template':'Vertrag für {name}, Beginn {start}', 'template_version':'1','template_approved':True,'fields':{'name':'Muster','start':'2026-01-01'}},
'P06':{'document_hash':'abc','version':'1','person_id':'P1','return_evidence':{'document_hash':'abc','version':'1','person_id':'P1','method':'ocr'}},
'P07':{'person_id':'P1','measure':'Änderung','draft':'Entwurf','rule_version':'1','representative':'BR','consultation_evidence':{'representative':'BR','measure_hash':digest('Entwurf'),'status':'completed'}},
'P08':{'person_id':'P1','periods':[{'start':'2026-01-01','end':'2026-06-30'}],'evidence':'Antrag'},
'P09':{'person_id':'P1','periods':[{'start':'2026-01-01','end':'2026-07-31'}],'evidence':'Antrag','previous_version':'1','decision':'bestätigt'},
'P10':{'person_id':'P1','return_date':'2026-07-01','hours':'30','role':'Sachbearbeitung','leave_periods':[{'start':'2026-01-01','end':'2026-06-30'}],'approval':{}},
'P11':{'person_id':'P1','field':'address','old':'Alt','new':'Neu','evidence':'E1','effective_date':'2026-01-01'},
'P12':{'template':'Bescheinigung für {name}', 'template_version':'1','template_approved':True,'fields':{'name':'Muster'}},
'P14':{'person_id':'P1','qualification':'Unterweisung','evidence':'E1','valid_until':'2026-12-31','confirmed_by':'HR','rule_version':'1','as_of':'2026-10-01'},
'P15':{'person_id':'P1','end_date':'2026-12-31','departure_type':'bestätigt','decision_evidence':{'by':'HR','evidence_id':'E1','scope_hash':'pending'},'tasks':[{'name':'Schlüssel','confirmed':False}]},
'P16':{'person_id':'P1','absence_type':'Urlaub','start':'2026-01-01','end':'2026-01-10','approval':{},'handover':'Vertretung'},
'P17':{'person_id':'P1','documents':[{'version':'1','content':'40 Stunden'},{'version':'2','content':'30 Stunden'}]},
'P18':{'case_type':'Vertrag','decision_fields':{'hours':'30'},'revision':1,'role':'HR','delegation':'D1','valid_from':'2026-01-01','valid_to':'2026-12-31'} }
