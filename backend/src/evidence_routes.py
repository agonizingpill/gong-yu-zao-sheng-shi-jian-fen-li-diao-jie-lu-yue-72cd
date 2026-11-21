from fastapi import APIRouter,Depends
from sqlalchemy import select
from .database import session
from .auth import current,operator,supervisor
from .models import NoiseEvent,Separation,Attribution
from .common import dump,get
from .evidence_schemas import EventInput,AttributionInput
from . import evidence_service as service
router=APIRouter()
@router.get('/complaints/{id}/events')
def events(id:int,cycle_id:int|None=None,db=Depends(session),u=Depends(current)):
    stmt=select(NoiseEvent).where(NoiseEvent.complaint_id==id)
    if cycle_id is not None:stmt=stmt.where(NoiseEvent.cycle_id==cycle_id)
    return [dump(x) for x in db.scalars(stmt.order_by(NoiseEvent.measured_at))]
@router.post('/complaints/{id}/events')
def event(id:int,data:EventInput,db=Depends(session),u=Depends(operator)):return service.create_event(db,u,id,data)
@router.get('/complaints/{id}/separations')
def separations(id:int,cycle_id:int|None=None,db=Depends(session),u=Depends(current)):
    stmt=select(Separation).where(Separation.complaint_id==id)
    if cycle_id is not None:stmt=stmt.where(Separation.cycle_id==cycle_id)
    return [dump(x) for x in db.scalars(stmt.order_by(Separation.id.desc()))]
@router.post('/complaints/{id}/separations')
def separate(id:int,db=Depends(session),u=Depends(operator)):return service.start_separation(db,u,id)
@router.get('/complaints/{id}/attributions')
def attributions(id:int,cycle_id:int|None=None,db=Depends(session),u=Depends(current)):
    stmt=select(Attribution).where(Attribution.complaint_id==id)
    if cycle_id is not None:stmt=stmt.where(Attribution.cycle_id==cycle_id)
    return [dump(x) for x in db.scalars(stmt.order_by(Attribution.id.desc()))]
@router.post('/complaints/{id}/attributions')
def attribution(id:int,data:AttributionInput,db=Depends(session),u=Depends(supervisor)):return service.confirm(db,u,id,data)
