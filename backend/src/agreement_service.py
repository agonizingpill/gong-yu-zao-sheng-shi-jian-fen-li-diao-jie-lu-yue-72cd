from sqlalchemy import select
from .models import Attribution,Agreement,Signature,Remedy
from .common import require,lock_case,lock_agreement,lock_current_cycle,get,record,dump,now

def create_agreement(db,user,caseid,data):
    case=lock_case(db,caseid);require(case.status=='mediation','须先完成人工归因，再起草调解协议')
    cyc=lock_current_cycle(db,caseid)
    attr=get(db,Attribution,data.attribution_id)
    require(attr.complaint_id==caseid and attr.source!='undetermined','归因须属于本卷且来源已核实')
    require(attr.cycle_id==cyc.id,'该归因属于历史履约周期，新周期须重新人工归因后才能起草协议')
    require(not db.scalar(select(Agreement).where(Agreement.cycle_id==cyc.id,Agreement.state.notin_(['cancelled','fulfilled']))),'当前周期已有在途协议')
    row=Agreement(complaint_id=caseid,cycle_id=cyc.id,**data.model_dump());db.add(row);db.flush();record(db,user,'agreement.draft',row.id,f'cycle={cyc.seq}');db.commit();return dump(row)
def sign(db,user,id,data):
    case,a=lock_agreement(db,id);require(a.state=='draft','只有草案可以登记签字')
    require(data.party in (a.party_a,a.party_b),'签字人必须为本协议参与方')
    require(not db.scalar(select(Signature).where(Signature.agreement_id==id,Signature.party==data.party)),'该参与方已签字')
    row=Signature(agreement_id=id,**data.model_dump());db.add(row);record(db,user,'agreement.sign',id,data.party);db.commit();return dump(row)
def activate(db,user,id):
    case,a=lock_agreement(db,id);require(a.state=='draft','协议不处于草案')
    signatures=db.scalars(select(Signature).where(Signature.agreement_id==id)).all()
    require({s.party for s in signatures}=={a.party_a,a.party_b},'双方均签字后协议才能生效')
    a.state='active';a.activated_at=now(db);case.status='remedy';record(db,user,'agreement.activate',id);db.commit();return dump(a)
def cancel(db,user,id,note):
    case,a=lock_agreement(db,id);require(a.state=='draft','仅未生效草案可撤销')
    a.state='cancelled'
    if not db.scalar(select(Agreement).where(Agreement.cycle_id==a.cycle_id,Agreement.state.notin_(['cancelled','fulfilled']))):
        case.status='mediation'
    record(db,user,'agreement.cancel',id,note);db.commit();return dump(a)
def create_remedy(db,user,id,data):
    case,a=lock_agreement(db,id);require(a.state in ('active','breached'),'仅生效/复发协议可新增整改')
    require(data.responsible in (a.party_a,a.party_b),'整改责任人须为协议参与方')
    row=Remedy(agreement_id=id,**data.model_dump());db.add(row);db.flush();record(db,user,'remedy.create',row.id,data.instruction);db.commit();return dump(row)
def complete_remedy(db,user,id,data):
    task=get(db,Remedy,id);case,a=lock_agreement(db,task.agreement_id);db.refresh(task)
    require(a.state in ('active','breached'),'协议当前不可整改')
    require(task.state in ('open','reopened'),'该整改项已完成')
    task.state='completed';task.receipt=data.receipt;task.completed_at=now(db);record(db,user,'remedy.complete',id,data.receipt);db.commit();return dump(task)
