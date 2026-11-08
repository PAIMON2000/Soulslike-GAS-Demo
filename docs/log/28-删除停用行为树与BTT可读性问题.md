# 删除停用行为树与BTT可读性问题

2026-11-09。用户指出大部分BTT内部蓝图仍极其复杂，并明确要求先删除旧行为树，避免再次打开错误入口。

确认控制器绑定`StandardReadable/BT_DS3_CombatOverview`及`BB_DS3_Standard`后，逐一确认8棵旧树和试建树无资产引用、逐文件备份并校验哈希，再通过Unreal正常资产删除接口删除。没有重新构建图或重命名资产内部对象。

删除范围：原`BT_Enemy`、Archive下两版EnemyMeleeCombat、原`BT_DS3BrokenSword`，以及Readable、ReadableStandard、Standard目录下共4棵试建树。空目录同步移除。

保留当前总览、四棵行动子树，以及Validation目录下的概率测试树。离线备份在`LocalBackups/RemovedBehaviorTrees-2026-11-09`，不再作为Content资产显示；删除记录见`docs/reproduction/obsolete-behavior-trees-removed-2026-11-09.json`。快照及恢复清单同步删除旧树，避免恢复时重新出现。

原11种行动的拓扑、装饰器与配置固化为`docs/reproduction/ds3-standard-action-reference.json`。验证导出工具改为在旧树不存在时读取基准；清理后再次通过11种行动校验。

BTT审计：DSInit 23节点，DSDecide 268，DSLocomotion 61，DSAttack 39，DSRelativeMove 124，DSAfterAttack 136，DSComboChoice 6。以上为各任务事件图的图节点数量，不等于行为树节点数量。

目前解决的是入口清理，尚未重构BTT内部。后续优先处理DSDecide与DSAfterAttack：将局势采样、规则匹配、权重配置、冷却过滤、抽取分别表达，再拆分相对移动的侧移、后退、靠近和转向职责。任务入口应能先看出输入、调用阶段、完成与中止，而不是直接铺开所有计算。重构须保持已有行为，通过运行检查后再判断可读性。
