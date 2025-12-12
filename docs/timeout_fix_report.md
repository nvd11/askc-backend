# GKE Gateway 超时问题排查与修复报告

## 1. 问题描述

在 Web UI 上调用 `/chat` 接口进行长文本生成（如请求讲一个长故事）时，响应会被截断并报错。经过初步分析，这是由于 Gateway 层的请求超时导致的。

当使用 `curl` 命令进行测试时，观察到如下错误：
```
curl: (92) HTTP/2 stream 1 was not closed cleanly: INTERNAL_ERROR (err 2)
```
这通常是由于服务端或中间代理（在此场景下为 GKE Gateway/Load Balancer）主动断开连接引起的超时。

## 2. 问题分析

### 2.1 应用层排查
首先检查了应用代码 `src/services/chat_service.py`，发现应用内部对 LLM 流式响应的超时设置已经是 **300秒（5分钟）**：
```python
timeout_seconds = 300.0
# ...
chunk = await asyncio.wait_for(chunk_task, timeout=timeout_seconds)
```
这排除了应用代码导致短时间超时的可能性。

### 2.2 基础设施层排查
随后检查了 GKE 的路由配置对象 `HTTPRoute` (`py-api-route`)。
通过命令 `kubectl get httproute py-api-route -n default -o yaml` 获取的实时配置显示，`status` 字段中存在一个关键错误：

```yaml
status:
  parents:
  - conditions:
    - message: 'Error GWCER104: HTTPRoute "default/py-api-route" is misconfigured, err: Timeouts are not supported.'
      reason: Invalid
      status: "False"
```

**结论**：
虽然我们在本地的 `gke-gateway-and-route.yaml` 文件中定义了 `timeouts: request: 600s`，但当前使用的 GKE Gateway 控制器（`gke-l7-global-external-managed`）**不支持**直接在 `HTTPRoute` 资源中配置超时。
这导致整个路由配置被视为“无效”或部分忽略，系统因此回退到了默认的短超时设置（通常为 15-30 秒），从而导致长请求被截断。

## 3. 解决方案

GKE 推荐通过 `BackendConfig` CRD（Custom Resource Definition）来配置后端服务的高级参数（包括超时、健康检查等），而不是直接在 `HTTPRoute` 中定义。

### 3.1 修复步骤

1.  **清理无效配置**：
    从 `HTTPRoute` 对象中移除了不支持的 `timeouts` 字段，使路由配置恢复为有效状态。

2.  **创建 BackendConfig**：
    创建了一个新的 `BackendConfig` 资源，专门用于定义超时策略。
    *文件：`chat-api-backendconfig.yaml`*
    ```yaml
    apiVersion: cloud.google.com/v1
    kind: BackendConfig
    metadata:
      name: chat-api-backendconfig
      namespace: default
    spec:
      timeoutSec: 300  # 设置超时为 5 分钟
    ```

3.  **关联 Service**：
    将这个 `BackendConfig` 绑定到 Kubernetes Service (`clusterip-chat-api-svc`) 上。这是通过给 Service 添加特定的注解（Annotation）实现的。
    *命令：*
    ```bash
    kubectl patch service clusterip-chat-api-svc -n default -p '{"metadata":{"annotations":{"cloud.google.com/backend-config":"{\"default\": \"chat-api-backendconfig\"}"}}}'
    ```

## 4. 验证结果

检查 Service 对象确认注解已添加：
```yaml
metadata:
  annotations:
    cloud.google.com/backend-config: '{"default": "chat-api-backendconfig"}'
```

配置生效后（通常需要几分钟让 GKE Ingress 控制器同步更新底层的 Google Cloud Load Balancer），长请求应该能够正常持续到 300 秒而不被中断。
