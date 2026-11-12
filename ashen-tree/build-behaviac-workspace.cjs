const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const source=JSON.parse(fs.readFileSync('data/断剑怪-策划阅读树.json','utf8'));
const out=path.resolve('behaviac-workspace');fs.mkdirSync(path.join(out,'behaviors','behaviac_meta'),{recursive:true});
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));
const attrs=o=>Object.entries(o).map(([k,v])=>k+'="'+esc(String(v).replace(/[\r\n]+/g,'；'))+'"').join(' ');
const properties=new Map(),methods=new Map();let serial=0;
function prop(name,type,description){properties.set(name,{type,description});return type+' Self.BrokenSword::'+name;}
function node(cls,title,values={},children=[],connectors){const id=serial++;return '<Node '+attrs({Class:cls.includes('.')?cls:'PluginBehaviac.Nodes.'+cls,Enable:'true',HasOwnPrefabData:'false',Id:id,PrefabName:'',PrefabNodeId:'-1',...values})+'><Comment '+attrs({Background:'NoColor',Text:title})+'/>'+(connectors|| (children.length?'<Connector Identifier="GenericChildren">'+children.join('')+'</Connector>':''))+'</Node>';}
function sequence(title,children){return node('Sequence',title,{},children);}
function action(title,description=''){const name='动作_'+methods.size;methods.set(name,{title,description});return node('Action',title,{Method:'Self.BrokenSword::'+name+'()',ResultFunctor:'""',ResultOption:'BT_INVALID'});}
function comparison(name,type,operator,value,title){return node('Condition',title,{Operator:operator,Opl:prop(name,type,title),Opr:'const '+type+' '+value});}
function cond(n){const s=n.name;const match=s.match(/(≥|≤|>|<|=)\s*(-?[\d.]+)(%?)/);let field,type='float',value,op;
 if(/目标对象有效/.test(s))return comparison('玩家目标有效','bool','Equal','true',s);
 if(/指定动作请求|外部请求/.test(s))return comparison('外部动作请求码','int','Equal',100,'外部请求分支：触发方与用途尚未核实');
 if(/只接近的变体/.test(s))return comparison('怪物配置编号','int','Equal',110054,s);
 if(/专用招式变体/.test(s))return comparison('怪物配置编号','int','Equal',144041,s);
 if(/受伤后改变招式/.test(s))return comparison('怪物配置编号','int','Equal',144040,s);
 if(/旁观角色/.test(s))return comparison('队伍角色','int','Equal',1,'队伍角色为旁观（枚举值1，接入前核对映射）');
 if(/围攻角色/.test(s))return comparison('队伍角色','int','Equal',2,'队伍角色为围攻（枚举值2，接入前核对映射）');
 if(/队伍职责/.test(s))return node('Or',s,{},[comparison('队伍角色','int','Equal',1,'旁观'),comparison('队伍角色','int','Equal',2,'围攻')]);
 if(/三段/.test(s))return comparison('本轮连击段数','int','Equal',3,s);
 if(match){value=Number(match[2]);op={'≥':'GreaterEqual','≤':'LessEqual','>':'Greater','<':'Less','=':'Equal'}[match[1]];
 if(/生命/.test(s)){field='自身生命比例';if(match[3])value/=100;}
 else if(/本次随机值/.test(s)){field='是否恢复走位随机值';type='int';}
 else if(/随机值/.test(s)){field='恢复走位分支随机值';type='int';}
 else if(/右侧|左侧|偏离正面/.test(s))field='玩家相对方向角';
 else if(/间距/.test(s))field='与玩家间距';
 if(field)return comparison(field,type,op,value,s);
 }
 return comparison('待核实条件_'+properties.size,'bool','Equal','true',s+'；此条件尚需人工映射，不能作为已实现逻辑');
}
const names={rules:'01_完整条件与行动',spacing:'30_按间距选择攻击后走位',recover:'31_普通攻击后的恢复',specialRecover:'32_替代招式后的恢复','连击A':'10_连续挥砍A','连击B':'11_连续挥砍B','固定两段':'12_固定两次挥砍','3003冷却攻击':'13_带冷却的单次攻击','前冲攻击':'14_向前冲刺攻击','后退':'20_后退拉开距离','侧移':'21_绕玩家侧移','转身':'22_转身面向玩家','特殊20005':'40_替代招式甲_效果待核实','特殊20006':'41_替代招式乙_效果待核实','变体专用接近':'42_只接近玩家的变体'};
function reference(key,title){assert(names[key]);return node('Behaviac.Design.Nodes.ReferencedBehavior',title,{ReferenceBehavior:'const string "'+names[key]+'"',Task:'""'});}
function ifelse(title,test,yes,no){return node('IfElse',title,{},[],[[' _condition'.trim(),test],['_if',yes],['_else',no]].map(([id,c])=>'<Connector Identifier="'+id+'">'+c+'</Connector>').join(''));}
function parallel(title,children){return node('Parallel',title,{ChildFinishPolicy:'CHILDFINISH_ONCE',ExitPolicy:'EXIT_ABORT_RUNNINGSIBLINGS',FailurePolicy:'FAIL_ON_ONE',SuccessPolicy:'SUCCEED_ON_ONE'},children);}
function weighted(n,excludeCooldown){return node('SelectorProbability',excludeCooldown?'冷却单击不可用：在剩余行动中抽取':'在本组行动中按权重抽取一次',{RandomGenerator:'""'},n.children.filter(c=>!excludeCooldown||c.refAction!=='3003冷却攻击').map(c=>node('DecoratorWeight',c.name+'，权重'+c.weight,{Weight:'const int '+c.weight,DecorateWhenChildEnds:'false'},c.children.map(convert))));}
function convert(n){
 if(n.ref)return reference(n.ref,n.name);
 const text=n.name+(n.detail?'\n'+n.detail:'')+(n.parameters?.length?'\n'+n.parameters.join('；'):'');
 switch(n.kind){
 case '顺序':return sequence(n.name,n.children.map(convert));
 case '选择':return node('Selector',n.name,{},n.children.map(convert));
 case '条件':return cond(n);
 case '如果 / 否则':return ifelse(n.name,...n.children.map(convert));
 case '每轮循环':return node('DecoratorLoop',n.name,{Count:'const int -1',DecorateWhenChildEnds:'true',DoneWithinFrame:'false'},[node('DecoratorAlwaysSuccess','本轮成功或失败后进入下一轮',{DecorateWhenChildEnds:'true'},n.children.map(convert))]);
 case '结果转成功':return node('DecoratorAlwaysSuccess',text,{DecorateWhenChildEnds:'true'},n.children.map(convert));
 case '持续检查目标':return parallel(n.name,[action('持续监测玩家目标有效','有效返回RUNNING，失效返回FAILURE。另一分支结束后中止此监测。待接入UE。'),...n.children.map(convert)]);
 case '超时':return parallel('接近与超时计时同时执行：谁先结束就中止另一边',[...n.children.map(convert),node('DecoratorAlwaysFailure','计时结束返回失败',{DecorateWhenChildEnds:'true'},[node('Wait','接近时限待核对；默认0仅表示未配置',{Time:prop('接近时限毫秒','float','必须核对ApproachLife并换算，不可使用默认0运行')})])]);
 case '加权选择':return n.children.some(c=>c.refAction==='3003冷却攻击')?ifelse('冷却单击是否可以参加本轮抽签？',comparison('距冷却单击上次发动秒数','float','Greater',20,'仅此招检查20秒冷却'),weighted(n,false),weighted(n,true)):weighted(n,false);
 case '成功':return node('Noop',n.name);
 case '动作':
 if(n.name.includes('0.2秒'))return node('Wait',n.name,{Time:'const float 200'});
 if(n.name.includes('抽一次段数'))return node('SelectorProbability','开始连击时只抽一次段数',{RandomGenerator:'""'},[2,3].map((count,i)=>node('DecoratorWeight',count+'段连击',{Weight:'const int '+[25,75][i],DecorateWhenChildEnds:'false'},[node('Assignment','本轮使用'+count+'段',{CastRight:'false',Opl:prop('本轮连击段数','int','只在连击开始时抽取'),Opr:'const int '+count})])));
 return action(n.name,text+'\n游戏方法占位声明：需实现并返回成功、失败或运行中；当前用于编辑阅读。');
 default:throw new Error('Unmapped kind '+n.kind);
 }
}
function tree(file,n){serial=0;const child=convert(n);const xml='<?xml version="1.0" encoding="utf-8"?><Behavior Version="5"><Node '+attrs({Class:'Behaviac.Design.Nodes.Behavior',AgentType:'BrokenSword',Domains:'',Enable:'true',HasOwnPrefabData:'false',Id:'-1',PrefabName:'',PrefabNodeId:'-1'})+'><Comment Background="NoColor" Text="'+esc(n.name+'\n策划整理稿：未连接游戏，未验证与UE执行一致')+'"/><DescriptorRefs value="0:"/><Connector Identifier="GenericChildren">'+child+'</Connector></Node></Behavior>';fs.writeFileSync(path.join(out,'behaviors',file+'.xml'),xml);}
tree('00_从这里开始_完整战斗循环',source.root);
for(const [key,n]of Object.entries(source.subtrees))tree(names[key],n);
tree('02_普通断剑怪_方向与间距',{...source.subtrees.rules,name:'阅读情形：基础配置、无外部请求、非队伍配合；从上到下检查',children:[5,6,7,8,14,16,18].map(i=>source.subtrees.rules.children[i])});
const typeNames={bool:'System.Boolean',int:'System.Int32',float:'System.Single'};
const enumXml='<enumtype Type="behaviac::EBTStatus" Namespace="behaviac" IsImplemented="true" DisplayName="行为状态" Desc="成功、失败或运行中">'+['INVALID','SUCCESS','FAILURE','RUNNING'].map(t=>'<enum '+attrs({NativeValue:'behaviac::BT_'+t,Value:'BT_'+t,DisplayName:'BT_'+t,Desc:'BT_'+t,MemberValue:'-1'})+'/>').join('')+'</enumtype>';
const meta='<?xml version="1.0" encoding="utf-8"?><meta><types>'+enumXml+'</types><agents><agent classfullname="behaviac::Agent" DisplayName="Agent" Desc="behaviac基础代理" IsRefType="true" IsImplemented="true"/><agent classfullname="BrokenSword" base="behaviac::Agent" DisplayName="断剑怪（设计稿）" Desc="未接入UE，方法仅为编辑器声明" IsRefType="true" IsCustomized="true">'+[...properties].map(([name,p])=>'<Member '+attrs({Name:name,DisplayName:name,Desc:p.description,Class:'BrokenSword',Type:p.type,TypeFullName:typeNames[p.type],defaultvalue:p.type==='bool'?'false':'0',Static:'false',Public:'true',Readonly:'false'})+'/>').join('')+[...methods].map(([name,m])=>'<Method '+attrs({Name:name,DisplayName:m.title,Desc:m.description,Class:'BrokenSword',ReturnType:'behaviac::EBTStatus',ReturnTypeFullName:'XMLPluginBehaviac.behaviac_EBTStatus',Static:'false',Public:'true',istask:'false'})+'/>').join('')+'</agent></agents><instances/></meta>';
fs.writeFileSync(path.join(out,'behaviors/behaviac_meta/BrokenSword.meta.xml'),meta);
fs.writeFileSync(path.join(out,'BrokenSword.workspace.xml'),'<?xml version="1.0" encoding="utf-8"?><workspace name="BrokenSword" metafilename="." folder="behaviors" export="exported" language="cpp" promptmergingmeta="false" version="3"><export><xml><isexported>True</isexported></xml></export></workspace>');
fs.writeFileSync(path.join(out,'阅读说明.md'),'# 断剑怪 behaviac 整理稿\n\n打开 BrokenSword.workspace.xml。00是完整循环，01保留全部19条分支，02只展示基础配置下的方向与间距规则。10至22为常规行动，30至32为共用恢复，40至42为待核实的特殊分支。双击引用子树可继续阅读。\n\n这是一套可编辑的设计稿。游戏方法是占位声明，未接入或改动UE。间距仍为原脚本单位。接近时限、外部请求来源、角色枚举映射、恢复随机值生成与中断取消需要核对。\n\n使用标准选择、顺序、条件、概率选择、权重、子树引用、并行、等待和结果修饰节点。冷却先通过条件分叉，再在相应候选中抽签。接近超时通过并行等待后失败表示，避免把时长节点误当成超时失败。\n\n重新运行上级目录 build-behaviac-workspace.cjs 会覆盖生成内容；在编辑器手调前另存工作区。\n');
console.log('Created 17 behavior trees, '+properties.size+' properties and '+methods.size+' design-only methods at '+out);
