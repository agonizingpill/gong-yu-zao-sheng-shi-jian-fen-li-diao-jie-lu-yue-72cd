"""幂等迁移：为既有库引入履约周期（fulfillment_cycles）。

- 全新库由 Base.metadata.create_all 建立完整结构，本脚本只负责回填/补缺。
- 旧库：create_all 仅建立新表，cycle_id 列需要本脚本 ALTER 添加（可空），
  随后为每个投诉补建 seq=1 周期并回填全部历史行的 cycle_id。
- 可重复执行：按 information_schema 判断列是否存在，已回填的行不会重复处理。
MySQL 8 / READ COMMITTED；演示库无外键级联依赖冲突。
"""
from sqlalchemy import text
from src.database import engine,Session
from src.models import FulfillmentCycle
from src.common import now

TABLES=('noise_events','separations','attributions','agreements','closures')

def column_exists(db,table,column):
    return db.scalar(text(
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE table_schema=DATABASE() AND table_name=:t AND column_name=:c"),
        {'t':table,'c':column})>0

def table_exists(db,table):
    return db.scalar(text(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema=DATABASE() AND table_name=:t"),{'t':table})>0

def migrate():
    with engine.begin() as conn:
        db=conn
        if not table_exists(db,'fulfillment_cycles'):
            FulfillmentCycle.__table__.create(conn)
        for t in TABLES:
            if not column_exists(db,t,'cycle_id'):
                db.execute(text(f"ALTER TABLE {t} ADD COLUMN cycle_id INT NULL"))
    with Session() as db:
        case_ids=[r[0] for r in db.execute(text("SELECT id FROM complaints ORDER BY id"))]
        for caseid in case_ids:
            cyc=db.execute(text(
                "SELECT id FROM fulfillment_cycles WHERE complaint_id=:c ORDER BY seq DESC LIMIT 1"),
                {'c':caseid}).first()
            if cyc is None:
                opened=db.execute(text("SELECT MIN(created_at) FROM complaints WHERE id=:c"),{'c':caseid}).scalar() or now(db)
                status=db.execute(text("SELECT status FROM complaints WHERE id=:c"),{'c':caseid}).scalar()
                # 与卷宗状态对齐：已结案卷宗的补建周期直接置为 closed，
                # 否则主管首次重开会被“重试”分支跳过而无法开启新周期。
                if status=='closed':
                    closed_at=db.execute(text(
                        "SELECT MAX(closed_at) FROM closures WHERE complaint_id=:c"),{'c':caseid}).scalar() or now(db)
                    db.execute(text(
                        "INSERT INTO fulfillment_cycles (complaint_id,seq,state,reopen_note,opened_at,closed_at) "
                        "VALUES (:c,1,'closed','首次建卷（迁移补建）',:o,:x)"),
                        {'c':caseid,'o':opened,'x':closed_at})
                else:
                    db.execute(text(
                        "INSERT INTO fulfillment_cycles (complaint_id,seq,state,reopen_note,opened_at,closed_at) "
                        "VALUES (:c,1,'active','首次建卷（迁移补建）',:o,NULL)"),{'c':caseid,'o':opened})
                cid=db.execute(text("SELECT LAST_INSERT_ID()")).scalar()
            else:
                cid=cyc[0]
            for t in TABLES:
                db.execute(text(f"UPDATE {t} SET cycle_id=:cid WHERE complaint_id=:c AND cycle_id IS NULL"),
                           {'cid':cid,'c':caseid})
        db.commit()
        # 回填后收紧：所有历史行均已归属周期，列改为 NOT NULL。
        for t in TABLES:
            nulls=db.execute(text(f"SELECT COUNT(*) FROM {t} WHERE cycle_id IS NULL")).scalar()
            if nulls==0 and column_exists(db,t,'cycle_id'):
                nullable=db.scalar(text(
                    "SELECT is_nullable FROM information_schema.columns "
                    "WHERE table_schema=DATABASE() AND table_name=:t AND column_name='cycle_id'"),{'t':t})
                if nullable=='YES':
                    db.execute(text(f"ALTER TABLE {t} MODIFY cycle_id INT NOT NULL"))
                    db.commit()
        print({'cases':len(case_ids),'tables':TABLES})

if __name__=='__main__':migrate()
