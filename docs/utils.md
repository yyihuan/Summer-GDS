# gds_utils.utils

## setup_logging(show_log=True) -> logging.Logger
初始化日志系统。

- **参数**
  - `show_log`: 是否在控制台显示日志。
- **返回**
  - 日志 Logger 对象。
[查看源码](../gds_utils/utils.py#L8)

## um_to_db(v) -> int
微米转数据库单位。

- **参数**
  - `v`: 浮点数，微米数值。
- **返回**
  - 整数，数据库单位。
[查看源码](../gds_utils/utils.py#L34)

## logger
全局日志对象。 