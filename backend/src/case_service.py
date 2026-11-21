from sqlalchemy import select,func
from .models import Complaint,NoiseEvent,Agreement,Audit,DemoClock,FulfillmentCycle
from .common import require,lock_case,get,record,now,dump

def list_cases(db):
    rows=db.scalars(select(Complaint).order_by(Complaint.id)).all()
    out=[]
    for c in rows:
        cur=db.scalar(select(FulfillmentCycle).where(FulfillmentCycle.complaint_id==c.id).order_by(FulfillmentCycle.seq.desc()).limit(1))
        out.append({**dump(c),
                    'event_count':db.scalar(select(func.count()).select_from(NoiseEvent).where(NoiseEvent.complaint_id==c.id)),
                    'cycle_seq':cur.seq if cur else 0,
                    'cycle_id':cur.id if cur else None,
                    'cycle_count':db.scalar(select(func.count()).select_from(FulfillmentCycle).where(FulfillmentCycle.complaint_id==c.id))})
    return out
def create_case(db,user,data):
    require(not db.scalar(select(Complaint).where(Complaint.code==data.code)),'投诉编号重复')
    row=Complaint(**data.model_dump(),consent_note='来访已授权' if data.consent else '未授权，仅建卷');db.add(row);db.flush()
    # 建卷即开启第1个履约周期，后续所有事件/归因/协议都挂到当前周期。
    cyc=FulfillmentCycle(complaint_id=row.id,seq=1,state='active',reopen_note='首次建卷',opened_at=now(db));db.add(cyc)
    record(db,user,'complaint.create',row.id,data.code);db.commit();return dump(row)
def consent(db,user,id,data):
    case=lock_case(db,id);require(case.status!='closed','已结案卷宗请先重开')
    case.consent=data.granted;case.consent_note=data.note
    record(db,user,'consent.grant' if data.granted else 'consent.withdraw',id,data.note);db.commit();return dump(case)
def advance(db,user,data):
    clock=db.scalar(select(DemoClock).where(DemoClock.id==1).with_for_update().execution_options(populate_existing=True))
    require(data.at>=clock.at,'演示时钟只能向前推进')
    clock.at=data.at;record(db,user,'clock.advance',1,data.at.isoformat());db.commit();return {'at':clock.at}
def list_cycles(db,caseid):
    rows=db.scalars(select(FulfillmentCycle).where(FulfillmentCycle.complaint_id==caseid).order_by(FulfillmentCycle.seq.desc())).all()
    out=[]
    for cyc in rows:
        agreements=db.scalars(select(Agreement).where(Agreement.cycle_id==cyc.id)).all()
        out.append({**dump(cyc),
                    'event_count':db.scalar(select(func.count()).select_from(NoiseEvent).where(NoiseEvent.cycle_id==cyc.id)),
                    'agreement_count':len(agreements),
                    'agreement_states':[a.state for a in agreements]})
    return out
def reopen(db,user,id,note):
    # 重开只允许已结案卷宗；同一结案态下重试不会重复建周期，
    # 与“新事件/新协议”并发时，已存在的更新周期即最新周期并据此裁决。
    case=lock_case(db,id);require(case.status=='closed','只可重开已结案投诉')
    latest=db.scalar(select(FulfillmentCycle).where(FulfillmentCycle.complaint_id==id).order_by(FulfillmentCycle.seq.desc()).limit(1).with_for_update().execution_options(populate_existing=True))
    require(latest is not None,'卷宗缺少历史周期，无法重开')
    if latest.state=='closed' and case.status=='closed':
        nxt=FulfillmentCycle(complaint_id=id,seq=latest.seq+1,state='active',reopen_note=note,opened_at=now(db));db.add(nxt);db.flush()
        case.status='monitoring'
        record(db,user,'cycle.reopen',nxt.id,f'complaint={id};from_seq={latest.seq};{note}')
    else:
        # 并发重开已由另一事务建立新周期：复用最新周期，不覆盖旧链。
        record(db,user,'cycle.reopen.retry',latest.id,f'complaint={id};{note}')
    db.commit();return dump(case)
