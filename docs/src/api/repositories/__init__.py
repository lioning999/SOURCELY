# repositories/ — 数据库操作封装。封装连接生命周期（get → try → commit → finally close）。
# Service 层只调 repository 方法，不手写 SQL、不管连接。
