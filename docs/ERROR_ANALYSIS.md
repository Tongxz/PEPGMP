# 错误深度分析报告

## 错误概览

在系统重构和集成过程中，遇到了以下一系列错误：

1. **数据库并发操作错误**: `cannot perform operation: another operation is in progress`
2. **数据库表结构错误**: `column 'confidence' does not exist`
3. **ID类型不匹配错误**: `invalid input for query argument $1: 'vid1_1762228085102' ('str' object cannot be interpreted as an integer)`
4. **事件循环关闭错误**: `Event loop is closed`
5. **Confidence对象转换错误**: `float() argument must be a string or a real number, not 'Confidence'`
6. **变量作用域错误**: `local variable 'concurrent' referenced before assignment`
7. **枚举类型序列化错误**: `Object of type ViolationType is not JSON serializable`
8. **Timestamp对象转换错误**: `invalid input for query argument $3: Timestamp(...) (expected a datetime.date or datetime.datetime instance, got 'Timestamp')`
