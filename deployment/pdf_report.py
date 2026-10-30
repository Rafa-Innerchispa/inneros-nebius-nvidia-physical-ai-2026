"""Branded exports of persisted, allowlisted Guardian evidence. No new inference."""
from pathlib import Path
import io,sys
from html import escape
from datetime import datetime,timezone,timedelta

VENDOR=Path.home()/'.local/share/inneros-nebius-demo/pdf-deps'
if VENDOR.is_dir():sys.path.insert(0,str(VENDOR))
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,KeepTogether,PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT='Helvetica';BOLD='Helvetica-Bold'
for regular,bold in [('/usr/share/fonts/truetype/freefont/FreeSans.ttf','/usr/share/fonts/truetype/freefont/FreeSansBold.ttf'),('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')]:
    if Path(regular).is_file() and Path(bold).is_file():
        pdfmetrics.registerFont(TTFont('GuardianSans',regular));pdfmetrics.registerFont(TTFont('GuardianSansBold',bold));FONT='GuardianSans';BOLD='GuardianSansBold';break

NAVY=colors.HexColor('#0b1b2c');CYAN=colors.HexColor('#00b8d9')
INK=colors.HexColor('#152a40');MUTED=colors.HexColor('#52677e')
LIGHT=colors.HexColor('#eef5fa');GOLD=colors.HexColor('#ffb547')
WIDTH=A4[0]-84
STYLES={
    'title':ParagraphStyle('title',fontName=BOLD,fontSize=23,leading=28,textColor=INK,spaceAfter=10),
    'sub':ParagraphStyle('sub',fontName=FONT,fontSize=10,leading=15,textColor=MUTED,spaceAfter=12),
    'h2':ParagraphStyle('h2',fontName=BOLD,fontSize=12,leading=16,textColor=INK,spaceBefore=14,spaceAfter=8,keepWithNext=True),
    'body':ParagraphStyle('body',fontName=FONT,fontSize=9,leading=13,textColor=INK,spaceAfter=6),
    'small':ParagraphStyle('small',fontName=FONT,fontSize=7.5,leading=11,textColor=MUTED,spaceAfter=4),
    'cell':ParagraphStyle('cell',fontName=FONT,fontSize=8,leading=11,textColor=INK),
    'head':ParagraphStyle('head',fontName=BOLD,fontSize=8,leading=11,textColor=colors.white),
    'metric':ParagraphStyle('metric',fontName=BOLD,fontSize=21,leading=26,textColor=INK),
}
def p(text,style='body'):
    return Paragraph(escape(str(text if text is not None else 'Not supplied')).replace('\n','<br/>'),STYLES[style])
def local_time(value):
    if not value:return 'Not supplied by source'
    try:
        dt=datetime.fromtimestamp(value,timezone.utc) if isinstance(value,(int,float)) else datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return dt.astimezone(timezone(timedelta(hours=-5))).strftime('%d %b %Y, %H:%M:%S')+' Ecuador (UTC-5)'
    except (ValueError,TypeError,OverflowError):return 'Not supplied by source'
def label(value):return str(value).replace('_',' ').capitalize()
def table(rows,widths=None,header=True):
    data=[[p(v,'head' if i==0 and header else 'cell') for v in row] for i,row in enumerate(rows)]
    t=Table(data,colWidths=widths or [WIDTH/len(rows[0])]*len(rows[0]),repeatRows=1 if header else 0,hAlign='LEFT')
    rules=[('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),('LINEBELOW',(0,0),(-1,0),.7,CYAN)]
    if header:rules+=[('BACKGROUND',(0,0),(-1,0),NAVY),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,LIGHT])]
    else:rules+=[('ROWBACKGROUNDS',(0,0),(-1,-1),[LIGHT,colors.white])]
    t.setStyle(TableStyle(rules));return t
def chrome(canvas,doc):
    w,h=A4;canvas.saveState()
    canvas.setFillColor(NAVY);canvas.rect(0,h-88,w,88,fill=1,stroke=0)
    # Original vector spark mark; no external image service or licensed asset.
    canvas.setStrokeColor(CYAN);canvas.setLineWidth(1.4);canvas.circle(60,h-43,20,fill=0,stroke=1)
    path=canvas.beginPath();path.moveTo(63,h-24);path.lineTo(49,h-45);path.lineTo(59,h-45);path.lineTo(55,h-61);path.lineTo(72,h-38);path.lineTo(62,h-38);path.close()
    canvas.setFillColor(GOLD);canvas.drawPath(path,fill=1,stroke=0)
    canvas.setFillColor(colors.white);canvas.setFont(BOLD,14);canvas.drawString(93,h-37,'InnerOS')
    canvas.setFillColor(colors.HexColor('#bcecf6'));canvas.setFont(FONT,10);canvas.drawString(93,h-54,'Infrastructure Guardian')
    canvas.setFont(BOLD,7.5);canvas.setFillColor(CYAN);canvas.drawRightString(w-42,h-35,'EVIDENCE REPORT')
    canvas.setFont(FONT,7);canvas.setFillColor(colors.white);canvas.drawRightString(w-42,h-51,'Real observations / Human authority')
    canvas.setStrokeColor(colors.HexColor('#d5e2ee'));canvas.line(42,41,w-42,41)
    canvas.setFillColor(MUTED);canvas.setFont(FONT,7);canvas.drawString(42,28,'guardian.creatorcore.ai | Read-only evidence | No device action authorized')
    canvas.drawRightString(w-42,28,f'{doc.page}')
    canvas.restoreState()
def document(title,subtitle,body):
    out=io.BytesIO();doc=SimpleDocTemplate(out,pagesize=A4,leftMargin=42,rightMargin=42,topMargin=112,bottomMargin=58,title=title,author='InnerOS Infrastructure Guardian',pageCompression=1)
    story=[p(title,'title'),p(subtitle,'sub'),*body]
    doc.build(story,onFirstPage=chrome,onLaterPages=chrome)
    return out.getvalue()
def keyvalues(values):return table([(a,b) for a,b in values],[130,WIDTH-130],header=False)
def snapshot_pdf(data):
    summary=data['summary'];signals=data['signals']
    cards=Table([[p(str(summary['signal_count']),'metric'),p(str(summary.get('signals_needing_review',summary['unavailable_or_unreachable_signals'])),'metric'),p('REAL','metric')],[p('PUBLISHED SIGNALS','small'),p('REQUIRE REVIEW','small'),p('EXISTING SOURCE','small')]],colWidths=[WIDTH/3]*3)
    cards.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),LIGHT),('LEFTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,0),10),('BOTTOMPADDING',(0,1),(-1,1),9)]))
    body=[cards,Spacer(1,12),keyvalues([('Source',data['source']),('Retrieved',local_time(data['collected_at'])),('Source observation',local_time(data.get('source_observed_at'))),('Freshness',label(data['freshness']))])]
    binding=[p('Evidence binding','h2'),keyvalues([('Snapshot',data['snapshot_id']),('SHA-256',data['snapshot_digest']),('Exported',local_time(datetime.now(timezone.utc).isoformat()))])]
    if len(signals)>8:
        review=[x for x in signals if x['state'] in ('not_reachable','offline','unavailable','unknown','disconnected','checks_need_attention')]
        body+=[p('Findings requiring review','h2')]
        body+=[table([['Observed asset','State'],*[[x['label'],label(x['state'])] for x in review]],[WIDTH*.55,WIDTH*.45])] if review else [p('No unavailable or unreachable values were supplied in this snapshot. This is not a complete health guarantee.')]
        body+=binding+[p('Interpretation','h2'),p('Monitor reachability is an observation, not a confirmed root cause. No physical device change or new model inference was performed to create this report.'),PageBreak()]
    body+=[p('Full observed infrastructure','h2')]
    rows=[['Signal / asset','Observed state','Unit','Source updated']]
    for x in signals:
        value=x['state'];value=label(value) if isinstance(value,str) and 'T' not in value else str(value)
        rows.append([x['label'],value,x.get('unit',''),local_time(x.get('source_updated_at'))])
    body+=[table(rows,[163,105,42,WIDTH-310]),p('How to interpret this report','h2'),p('These are actual allowlisted observations from existing collectors, not a synthetic incident. A monitor failing to reach a device does not establish hardware failure. Failed aggregate server service checks do not prove a powered-off host. Camera signals are not a complete physical camera inventory.'),p('Retrieval time is not a new physical probe. Source state can be older or its age unknown. No new Nemotron inference was run to export this PDF.')]
    if len(signals)<=8:body+=binding
    return document(data['site_label']+' / '+label(data['category']),'Infrastructure observation report | REAL_READ_ONLY',body)
def analysis_pdf(data):
    result=data['result'];d=result.get('diagnosis') or {};receipt=result.get('provider_receipt') or {};usage=receipt.get('usage') or {}
    body=[keyvalues([('Inference mode',result.get('inference_mode')),('Provider',result.get('provider')),('Model',result.get('model')),('Requested',local_time(data.get('requested_at'))),('Measured duration',str(data.get('elapsed_seconds'))+' seconds')]),p('Model assessment','h2'),p(d.get('root_cause')),p('Impact','h2'),p(d.get('impact')),p('Recommendation / unverified','h2'),p(d.get('recommended_action')),p(d.get('rationale')),p('A model recommendation is not a confirmed physical diagnosis or permission to act. No device restart or recovery is proved by this report.'),p('Actual provider receipt','h2'),keyvalues([('Response ID',receipt.get('response_id')),('Input / output tokens',str(usage.get('prompt_tokens'))+' / '+str(usage.get('completion_tokens'))),('Output maximum',data.get('max_output_tokens')),('Paid requests attempted',data.get('paid_requests_attempted')),('Receipt SHA-256',receipt.get('receipt_sha256'))]),p('Bound infrastructure snapshots','h2')]
    for obs in data.get('observations') or []:
        body += [KeepTogether([keyvalues([('Site',obs['site_label']),('Signals',obs['summary']['signal_count']),('Retrieved',local_time(obs.get('collected_at'))),('Source observation',local_time(obs.get('source_observed_at'))),('Snapshot',obs['snapshot_id']),('SHA-256',obs['snapshot_digest'])]),Spacer(1,10)])]
    body+=[p('Point-in-time analysis','h2'),p('This PDF exports the recorded provider result and exact snapshots. It does not run a new inference, analyze later readings or spend additional cloud credits. Source timestamps remain authoritative. Physical device action authorization: NONE.')]
    return document('NVIDIA Nemotron / analysis','Recorded analysis of real infrastructure | Provider-backed evidence',body)
def call_pdf(data):
    body=[keyvalues([('Request',data['request_id']),('Status',data['status']),('Owner authorized',local_time(data.get('authorized_at'))),('Finished',local_time(data.get('finished_at'))),('Approval expires',local_time(data.get('expires_at_epoch'))),('Dispatch executed',str(data.get('executed'))),('Dispatch verified',str(data.get('verified')))]),p('Human-in-the-loop boundary','h2'),p('Only the authenticated owner can approve this single call in Home Assistant. The public page cannot approve it. No response means expiry without dialing. No arbitrary destination, automatic redial or device action is authorized.'),p('Evidence binding','h2'),keyvalues([('Snapshot',data['snapshot_id']),('Snapshot SHA-256',data['snapshot_digest'])]),p('Verification scope','h2'),p('A verified dispatch receipt does not prove that every spoken word was heard or that the conversational model was available. Human audibility must be confirmed separately. No physical recovery is asserted.')]
    return document('Owner callback / approval audit','Existing Home Assistant approval and VoiceOps execution evidence',body)
def overview_pdf():
    return document('Guardian / evaluation guide','Real infrastructure, recorded model evidence and governed owner callbacks',[p('1. Inspect a real source','h2'),p('Choose Casa Rafael network, cameras, servers or energy; or Bellini network. Read real infrastructure to view existing source observations and timestamps.'),p('2. Inspect NVIDIA evidence','h2'),p('Read the recorded NVIDIA Nemotron analysis and provider receipt. It is an actual point-in-time inference, not a new paid request for each click.'),p('3. Request an owner callback','h2'),p('The judge may request a call. The owner receives a Home Assistant notification and must authenticate to approve or cancel. The request expires without calling if the owner does not respond. A public visitor cannot authorize a call or a device restart.'),p('Scope','h2'),p('Source observations, model recommendations, owner consent, dispatch and actual audibility are separate facts. The public console does not execute physical device mutations.')])
