# 002 履约周期分离

结案后主管重开本卷时开启**新的履约周期**。新增 `fulfillment_cycles` 表，并在
`noise_events / separations / attributions / agreements / closures` 上增加
`cycle_id` 外键。旧协议、整改、复验、复发与结案记录继续可查，但全部冻结在其所属周期，
不能成为新周期的归因、整改或结案依据；重开后新增事件只进入新周期分离，只有新的人工归因
才能起草新协议。

本项目不附自动迁移器，显式升级脚本见 `scripts/migrate_cycles.py`，对已存在的列/表幂等：
先以可空列加入 `cycle_id`，为每个既有投诉补建第 1 周期并回填全部历史行，再收紧约束。
全新库由 `create_all` 直接建立带外键的结构，迁移脚本会跳过已完成的步骤。
