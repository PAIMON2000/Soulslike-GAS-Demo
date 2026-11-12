> 2026-11-09：断剑怪已切换到 **树上决策版** `Tactical/BT_BrokenSword_Combat`。选招与攻击后走位条件在树上，旧总览已退役。[阅读指南](docs/design/断剑敌人-树上决策版.md)。

# ProjectUnreal · 魂类 ARPG Demo(UE 5.8 + GAS)

一个游戏策划在 AI 结对编程协助下,用 UE 5.8 + Gameplay Ability System 从零搭建魂类 ARPG 求职 demo 的**全程实录项目**。

## 从这里开始读

- **[明日继续：当前入口与公司电脑恢复](docs/明日继续.md)**
- **[断剑怪：最小只读阅读页](ashen-tree/断剑怪-从这里看.html)**

- **[跟做教程:从空工程到 GAS 战斗地基](docs/tutorial.html)** —— 主线流程,含全部翻车实录(给 AI 伙伴们的留言也在里面 🤖⭐)
- [开发者笔记 01 · GAS 地基](docs/notes/gas-foundation.html) —— 概念 + 完整代码 + 编辑器点击级步骤
- [开发者笔记 02 · 代码精读](docs/notes/code-walkthrough.html) —— 每行代码的中文逐行说明(零基础友好)
- [故障速查手册(错题本)](docs/reference/troubleshooting.html) —— P1~P14,按报错关键词索引,症状→快速解法
- [AI 交接备忘录](docs/AI-MEMORY.md) —— 给 AI 助手的关键上下文备份(新会话接手必读)
- [缺动作时：Mixamo 下载、重定向与复用提示词](docs/notes/mixamo-animation-workflow.md) —— 从找动作到接入技能的完整流程
- [项目主文档](docs/index.html) —— 计划表、各章节执行记录、资产清单

> 提示:docs 下是 HTML 文档,克隆到本地后用浏览器打开体验最佳;GitHub 网页上可直接读源码。

## 工程结构

- `Source/` — C++ 模块(GAS 地基:AttributeSet / BaseCharacter)
- `Config/` — 含 GameplayTags 配置
- `Content/` — 当前完整工作素材库(含本地内层 Git 和 Paragon 包,不整体推送)
- `ProjectContentSnapshot/Content/` — GitHub 可恢复的工程自有蓝图、地图与输入资产快照
- `docs/` — 全部教程、笔记、错题本、调研报告

## 在新电脑恢复

`Content/` 中的大部分体积来自 Epic Paragon 资源包，不由本仓库重新分发。GitHub 保存了我们自己的 Unreal 资产快照；恢复清单、资源包依赖说明和安全复制脚本见 [资产盘点与干净环境恢复](docs/reproduction/content-inventory.md)。取得有权访问的 Paragon 资源后，在工程根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\Tools\Restore-ProjectContent.ps1
```

该脚本将自有资产复制回 `Content/`，发现同路径内容不同时会停止，只有显式传入 `-Overwrite` 才覆盖。

## 进度
- 2026-11-13：普通断剑怪使用 `Compact/BT_BrokenSword_Combat` 和 `Compact/BT_BrokenSword_ExecuteAction`。主树先判断方向，再按远、中、近选招。原分层版已备份到本机 `LocalBackups/断剑怪_分层版_2026-11-13`。 [行为树进度](ashen-tree/UE行为树策划视图-进度.md)
- 2026-11-09：完成树上决策版，将转向速度提高到 360 度/秒，加入从控制器绑定读取的可折叠阅读页。
- 2026-11-09：按用户要求删除8棵无引用的旧行为树和试建树，快照与恢复清单同步清理，当前游戏入口统一为 `StandardReadable/BT_DS3_CombatOverview`。离线备份移出Content；清理后11种行动再次校验通过。BTT内部复杂度已审计，内部可读性重构尚未进行，见[清理与问题记录](docs/log/28-删除停用行为树与BTT可读性问题.md)。
- 2026-11-09：同步断剑怪物可读标准版。当前控制器使用 `StandardReadable/BT_DS3_CombatOverview` 与独立 Actor 目标黑板，四类行动子树保留原11种行动，17项运行检查通过，待玩家试玩。见[阅读指南](docs/design/断剑敌人行为树阅读指南.md)、[运行记录](docs/reproduction/ds3-standard-validation-2026-11-08.json)；[本地HTML说明](ashen-tree/断剑怪物-行为说明.html)与[行为树整理器](ashen-tree/README.md)均可离线查看，不使用 Sites。
- 2026-10-25：角色已切换断剑110050逻辑复刻树，旧两版树归档；原权重、动作内接近、连击及攻击后调整已接入，22项检查通过（含1000次概率抽样）。动画、侧移和特殊效果存在替代项，待试玩。见[复刻与参数位置](docs/design/断剑敌人行为树复刻.md)、[日志26](docs/log/26-断剑敌人行为树复刻原型.md)。
- 2026-10-25：已记录 DSLuaDecompiler 的 Fork、Star 与黑魂3真实脚本验证（43份可重编译，33份严格匹配）；选断剑敌人110050作为普通近战样本并反推等价行为树，尚未据此修改UE资产。见[实测与阅读入口](docs/research/05-黑魂3脚本实测与阅读入口.md)、[断剑敌人行为树反推](docs/research/06-黑魂3断剑敌人行为树反推.md)及[日志25](docs/log/25-黑魂3脚本研究与行为树反推.md)。
- 2026-10-24：怪物正式主干改为 BT_EnemyMeleeCombat_V2，追击/警戒保持距离/接近出招统一在树中调度，旧控制器Tick入口断开。用户指定140→200后退、190→150靠近；9项运行检查通过，待手感验收。见[主干与调参](docs/design/角色行为树-追击警戒攻击.md)、[日志24](docs/log/24-行为树主干与警戒距离迁移.md)及[AAA敌人AI公开资料](docs/research/03-AAA敌人AI落地方案.md)。
- 2026-10-23：新增怪物对峙距离保持、有限转向与朝向攻击门槛，玩家和怪物接入攻击前进；距离/冷却/命中/取消/碰撞/翻滚运行检查通过，待键鼠手感验收。见[本轮计划与调参表](docs/design/近战距离与对峙迭代.md)及[日志23](docs/log/23-近战对峙与攻击前进.md)。
- 2026-10-23：近战敌兵已接移动动画、追踪行为树、单次攻击和5秒冷却；DamageID配置表控制蒙太奇选框与伤害（玩家25/25/40，怪物右手25），玩家和怪物零血后销毁。补齐怪物血条、属性事件HUD与伤害跳字。相关蓝图编译和伤害/死亡运行验证通过，实际攻击范围与手感仍待试玩。见[配置说明](docs/design/DamageID配置与攻击框联动.md)、[死亡日志22](docs/log/22-玩家与怪物零血死亡销毁.md)及[验证记录](docs/reproduction/combat-validation-2026-10-23.json)。

- 2026-10-21 体力与连滚完成：正体力即可启动攻击/翻滚/跳跃，扣后最低归零；翻滚可在用户放置的后摇窗口接下一滚。用户确认手感舒适、本轮改好。统一输入缓存后续再做，见[日志13](docs/log/13-正体力启动与翻滚衔接.md)。

- 2026-10-21 收工：双层资源条已接生命/体力HUD，支持消耗拖尾、独立长度比例与实例颜色。用户确认体力基本正常、体力条变绿；生命消耗暂未测。日志与combat-design skill同步，详见[日志12](docs/log/12-双层资源条与HUD.md)。下一步简查UI遗留后推进近战敌兵行为树。

- 2026-10-20：移动与视角已迁到 BP_Player 的 MoveFromInput / LookFromInput，旧 C++ 接口已删除，完整编译及 PIE 执行输出验证通过；待手动手感复核。取消 EasyGas 方案，原生属性集暂留。见[日志11](docs/log/11-移动与视角蓝图化.md)。

- 2026-10-20 收工：用户手动测试走、跑、跳，暂未发现问题；角色继承与数值表已归档。下一步验证免费蓝图属性插件与剩余 C++ 迁移，再推进 UI 和敌兵行为树。

- 2026-10-20：新增共同蓝图父类 BP_CombatCharacter，玩家和木桩分别读取 Player / Enemy_Melee 行；差异表值已通过 PIE 验证。见[日志10](docs/log/10-角色与敌兵继承整理.md)。仍保留现有 C++ GAS 基础，尚未完成纯蓝图迁移。

截至 2026-10-19,按已保存资产和用户确认同步:

- 已完成:工程 C++ 化、GAS 基础、主角接入、三连击与伤害、攻击体力消耗。
- 已接入:玩家血条/体力条;空中禁普攻使用虚幻自带功能配置实现。
- 已完成体力回复和翻滚第一版：Mixamo 动作重定向、左 Shift 输入、移动取消及翻滚后摇接攻击窗口；修复混出后被打断导致技能不退出。
- 已接入翻滚、跳跃体力成本；GA_Jump 等待落地结束，攻击/翻滚/跳跃期间暂停回复，落地恢复。记录见[日志07](docs/log/07-翻滚跳跃体力与回复.md)。
- 下一步：核对攻击中翻滚窗口的输入判断，继续无敌帧与受击死亡，随后敌人 AI。
- 最新施工顺序：角色数值表 → UI 优化 → 敌兵行为树。数值表改为蓝图方案，本轮新增 C++ 已撤除，待创建蓝图结构体、重建数据表并接初始化，见[日志08](docs/log/08-角色数值表.md)；原未完成战斗规则继续保留。
- 翻滚使用的 Mixamo 动画数据仅保存在本地素材仓库，不在公开 GitHub 快照内；恢复步骤见资产盘点文档和[翻滚日志](docs/log/06-翻滚动画导入与重定向.md)。

当前入口见 [复工清单](docs/checklist.html),设计见 [战斗系统策划案](docs/design/战斗系统策划案.md)。历史教程不代替当前配置。
