from sqlalchemy import select
from fastapi import HTTPException
from .models import Complaint,DemoClock,Audit,Agreement,FulfillmentCycle

def require(ok,message,code=409):
    if not ok: raise HTTPException(code,message)
def get(db,model,id):
    row=db.get(model,id)
    if not row:raise HTTPException(404,'记录不存在')
    return row
def lock_case(db,id):
    row=db.scalar(select(Complaint).where(Complaint.id==id).with_for_update().execution_options(populate_existing=True))
    if not row:raise HTTPException(404,'投诉记录不存在')
    return row
def get_cycle(db,id):
    row=db.get(FulfillmentCycle,id)
    if not row:raise HTTPException(404,'履约周期不存在')
    return row
def current_cycle(db,caseid):
    # 最新周期即当前周期；历史周期仅留档，不再承接任何写入。
    return db.scalar(select(FulfillmentCycle).where(FulfillmentCycle.complaint_id==caseid).order_by(FulfillmentCycle.seq.desc()).limit(1))
def lock_current_cycle(db,caseid):
    row=db.scalar(select(FulfillmentCycle).where(FulfillmentCycle.complaint_id==caseid).order_by(FulfillmentCycle.seq.desc()).limit(1).with_for_update().execution_options(populate_existing=True))
    if not row:raise HTTPException(404,'履约周期尚未建立')
    return row
def ensure_current(db,caseid,row):
    # 并发重开后，旧周期上的写入一律按最新周期裁决并拒绝。
    cur=current_cycle(db,caseid)
    require(row.cycle_id==cur.id,'该记录属于历史履约周期，不能作为当前周期依据，请在最新周期重新办理')
    return cur
def lock_agreement(db,id):
    item=get(db,Agreement,id);case=lock_case(db,item.complaint_id)
    db.refresh(item)
    ensure_current(db,case.id,item)
    return case,item
def now(db):return get(db,DemoClock,1).at
def record(db,user,action,subject,detail=''):
    db.add(Audit(actor=user.username,action=action,subject=str(subject),detail=str(detail)))
def dump(row):
    if row is None:return None
    return {col.name:getattr(row,col.name) for col in row.__table__.columns}
def within_window(dt,agreement):
    n=dt.hour*60+dt.minute;a=agreement.quiet_from;b=agreement.quiet_to
    return a<=n<b if a<b else n>=a or n<b
