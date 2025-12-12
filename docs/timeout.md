我在前端调用/chat接口, 和收这个svc 的llm 返回的ai 消息, 如果消息比较长
我会在前端见到后端的llm回复会被timeout截断

我已经测试过在curl-test-pod 中直接调用cluster ip是没有timeout 问题的

相信timeout发生在gke gateway
帮我检查gke env 对象和修复

gateway url of /chat: 
https://gateway.jpgcp.cloud/chat-api-svc/api/v1