(function(scope){
const SUCCESS='SUCCESS',FAILURE='FAILURE',RUNNING='RUNNING',UNKNOWN='UNKNOWN';
function evaluate(expr,ctx){
  if(expr==='true')return true;if(expr==='false')return false;
  const terms=expr.split(/\s*&&\s*/).map(p=>{const m=p.trim().match(/^(\w+)\s*(==|!=|<=|>=|<|>)\s*(true|false|-?\d+(?:\.\d+)?)$/);if(!m||!(m[1] in ctx))return null;const a=ctx[m[1]],b=m[3]==='true'?true:m[3]==='false'?false:Number(m[3]);return {'==':()=>a===b,'!=':()=>a!==b,'<=':()=>a<=b,'>=':()=>a>=b,'<':()=>a<b,'>':()=>a>b}[m[2]]()});return terms.includes(false)?false:terms.includes(null)?null:true;
}
function tick(nodes,ctx,memory={}){
 let trace=[],visited=new Set(),old=memory.active,active=null,blocked=false;
 const children=id=>nodes.filter(n=>n.parent===id).sort((a,b)=>b.priority-a.priority||a.id.localeCompare(b.id));
 function visit(n,path=new Set()){
  if(path.has(n.id)){trace.push(n.name+'：父子循环');return UNKNOWN}path=new Set(path).add(n.id);visited.add(n.id);
  let result;
  if(n.type==='条件'){let value=evaluate(n.condition,ctx);result=value===null?UNKNOWN:value?SUCCESS:FAILURE;}
  else if(n.type==='动作'){
   if(memory.active===n.id&&ctx.animationEnd){result=SUCCESS;}
   else if(n.instant){result=SUCCESS;}
   else{active=n.id;result=RUNNING;}
  }else{
   const list=children(n.id);if(!list.length)result=FAILURE;
   else if(n.type==='顺序器'){
    let i=memory.sequence?.[n.id]||0;result=SUCCESS;
    for(let g=0;g<i;g++){if(list[g].type==='条件'){const guard=visit(list[g],path);if(guard!==SUCCESS){if(memory.sequence)delete memory.sequence[n.id];trace.push(n.name+' → '+guard);return guard;}}}
    for(;i<list.length;i++){result=visit(list[i],path);if(result!==SUCCESS)break;}
    if(!memory.sequence)memory.sequence={};
    if(result===RUNNING)memory.sequence[n.id]=i;else delete memory.sequence[n.id];
   }else{
    result=FAILURE;for(let c of list){result=visit(c,path);if(result!==FAILURE)break;}
   }
  }
  if(result===UNKNOWN)blocked=true;trace.push(n.name+' → '+result);return result;
 }
 const root=nodes.find(n=>n.id==='root');const status=root?visit(root):UNKNOWN;
 const interrupted=old&&old!==active&&status!==SUCCESS;
 if(old&&old!==active){const wasCompleted=ctx.animationEnd&&visited.has(old);if(!wasCompleted)trace.push('中断：'+(nodes.find(n=>n.id===old)?.name||old)+'；调用 OnAbort / CancelAbility');}
 for(let id of Object.keys(memory.sequence||{}))if(!visited.has(id))delete memory.sequence[id];
 memory.active=active;
 return {status:blocked?UNKNOWN:status,trace,active,interrupted};
}
scope.BT={evaluate,tick,SUCCESS,FAILURE,RUNNING,UNKNOWN};
if(typeof module!=='undefined')module.exports=scope.BT;
})(typeof window==='undefined'?globalThis:window);
