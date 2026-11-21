import {api} from './api.js';
export const store={user:JSON.parse(sessionStorage.getItem('quiet-user')||'null'),cases:[],selected:Number(sessionStorage.getItem('quiet-case')||1),clock:''};
export async function refresh(){[store.cases,{at:store.clock}]=await Promise.all([api('/complaints'),api('/clock')]);if(!store.cases.some(c=>c.id===store.selected))store.selected=store.cases[0]?.id||0}
export function choose(id){store.selected=Number(id);sessionStorage.setItem('quiet-case',id)}
export const currentCase=()=>store.cases.find(c=>c.id===store.selected);
// 当前周期=最新周期；列表接口已带 cycle_id/cycle_seq/cycle_count。
export const currentCycle=()=>{const c=currentCase();return c?{id:c.cycle_id,seq:c.cycle_seq,count:c.cycle_count}:null};
export async function listCycles(){return api(`/complaints/${store.selected}/cycles`)}
export async function latestAgreement(){
  const rows=await api(`/complaints/${store.selected}/agreements`);
  const cyc=currentCycle();
  // 优先当前周期的在途协议；当前周期尚无协议时返回 undefined，历史协议不再被当作可操作对象。
  return rows.find(a=>a.cycle_id===cyc?.id&&!['cancelled','fulfilled'].includes(a.state))
      ||rows.find(a=>a.cycle_id===cyc?.id)
      ||undefined;
}
