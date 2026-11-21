import {esc,stamp,minute} from '../utils.js';
import {LABELS,BANDS,SOURCES,CASE_STATES,CYCLE_LABELS} from '../constants.js';
import {currentCycle} from '../store.js';
export const badge=s=>`<span class="badge ${esc(s)}">${esc(LABELS[s]||s)}</span>`;
// 周期标签：当前周期高亮，历史周期置灰，明确旧链不可再操作。
export const cycleBadge=(row)=>{const cur=currentCycle();const isCurrent=row&&cur&&row.cycle_id===cur.id;
  return `<span class="cycle-badge ${isCurrent?'current':'history'}">${isCurrent?'当前':'历史'} · 第${row?.cycle_seq??cur?.seq??1}周期</span>`};
export const empty=(title,action)=>`<div class="empty"><span>待办 / NEXT</span><h3>${esc(title)}</h3><p>${esc(action)}</p></div>`;
export const caseRibbon=c=>c?`<div class="case-ribbon"><div class="case-id">${esc(c.code)}</div><div><strong>${esc(c.alias)} · ${esc(c.building)}</strong><p>${esc(c.summary)}</p></div><div>${badge(c.status)}<small>履约周期 · 第 ${c.cycle_seq??1} 轮 / 共 ${c.cycle_count??1} 轮</small><small>监测授权 · ${c.consent?'已取得':'未取得 / 已撤回'}</small></div></div>`:empty('先建立匿名投诉','在收件页填写楼栋、别名和问题，不收集住户真实姓名。');
export const flow=c=>`<div class="flow-strip">${CASE_STATES.map((x,i)=>`<span class="${c?.status===x?'here':''}"><b>0${i+1}</b>${LABELS[x]}</span>`).join('')}</div>`;
export const note=(title,text)=>`<aside class="margin-note"><strong>${esc(title)}</strong><p>${esc(text)}</p></aside>`;
export const agreementRibbon=a=>a?`<div class="agreement-ribbon"><b>协议 QTA-${a.id}</b>${cycleBadge(a)}${badge(a.state)}<span>${esc(a.party_a)} ↔ ${esc(a.party_b)}</span><span>静音 ${minute(a.quiet_from)} — ${minute(a.quiet_to)}</span><span>能量阈值 ${a.threshold}</span></div>`:empty('当前周期尚无调解协议','重开后须重新人工归因，旧协议仅作历史留档；再由主管在新周期起草。');
export const bandBars=events=>`<div class="band-profile">${BANDS.map((b,i)=>{const n=events.length?events.reduce((s,e)=>s+e.energies[i],0)/events.length:0;return `<div><label>${b}</label><span style="width:${Math.min(100,n*7)}%"></span><small>${n.toFixed(2)}</small></div>`}).join('')}</div>`;
export const sourceComposition=weights=>`<div class="source-line">${Object.entries(weights).map(([s,n])=>`<span style="flex:${Math.max(.02,n)}" class="source-${s}" title="${SOURCES[s]} ${(n*100).toFixed(1)}%">${SOURCES[s]} ${(n*100).toFixed(0)}%</span>`).join('')}</div>`;
