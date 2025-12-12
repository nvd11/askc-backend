
# 指南二：GKE连接私有Cloud SQL疑难问题排查实录

本文档记录了一次完整的、从GKE Pod无法连接到私有Cloud SQL实例的疑难问题的排查过程。

## 1. 问题描述

在成功创建私有Cloud SQL实例后，我们发现：
-   从位于同一VPC的GCE虚拟机可以成功连接到Cloud SQL。
-   从GKE集群的Pod中无法连接，`psql`客户端报告`Connection timed out`。

这表明问题特定于GKE的网络环境。

## 2. 排查过程

我们按照从易到难、从高层到底层的顺序，系统地排查了所有可能性。

### 2.1. 检查VPC防火墙规则 (已解决)

**怀疑**: 是否有防火墙规则阻止了从GKE Pod到Cloud SQL的流量？

**验证**:
1.  我们首先检查了GKE节点的IP范围，命令如下：
    ```bash
    gcloud container clusters describe my-cluster2 --region=europe-west2 --project=jason-hsbc --format="json(clusterIpv4Cidr, servicesIpv4Cidr)"
    ```
    输出为 `192.171.16.0/20` (Pods) 和 `192.172.16.0/20` (Services)。

2.  我们发现现有的防火墙规则没有覆盖这些IP段。因此，我们在`Terraform-GCP-config`项目中添加了一条新的防火墙规则，允许所有内部流量。

    ```terraform
    # network/tf-vpc0.tf
    resource "google_compute_firewall" "allow_internal" {
      name      = "allow-all-internal-traffic"
      network   = google_compute_network.tf-vpc0.name
      direction = "INGRESS"
      allow {
        protocol = "all"
      }
      source_ranges = [
        "192.168.0.0/16",   # For VPC subnets
        "192.171.16.0/20",  # For GKE Pods
        "192.172.16.0/20"   # For GKE Services
      ]
    }
    ```
3.  通过`terraform apply`成功应用了此规则。

**结果**: 问题依旧，连接仍然超时。这排除了VPC防火墙是问题根源的可能性。

### 2.2. 检查GKE网络策略 (已排除)

**怀疑**: GKE集群内部是否有`NetworkPolicy`资源，默认拒绝了Pod的出站流量？

**验证**:
```bash
kubectl get networkpolicy --all-namespaces
```
**输出**: `No resources found`

**结果**: 集群中没有任何网络策略。此可能性被排除。

### 2.3. 检查IP伪装 (IP Masquerade) (已排除)

**怀疑**: 从Pod发出的流量，其源IP是否被错误地“伪装”（NAT）成了节点的IP，导致防火墙规则不匹配？

**验证**:
1.  我们创建了一个`ConfigMap` (`ip-masq-agent-config.yaml`)，明确告诉GKE的IP伪装代理，所有到私有IP范围（`10.0.0.0/8`等）的流量都**不**应该被伪装。
    ```yaml
    apiVersion: v1
    kind: ConfigMap
    metadata:
      name: ip-masq-agent-config
      namespace: kube-system
    data:
      config: |
        nonMasqueradeCIDRs:
          - 10.0.0.0/8
          - 172.16.0.0/12
          - 192.168.0.0/16
    ```
2.  通过`kubectl apply`应用了此配置。

**结果**: 问题依旧。这基本排除了IP伪装是问题根源的可能性。

### 2.4. 检查VPC Peering路由传播 (已尝试修复)

**怀疑**: 在排除了以上所有可能后，问题最终指向了VPC Peering的路由传播。即Cloud SQL所在的Google服务网络的路由，没有被正确地通告给GKE的子网。

**验证**:
1.  我们首先确认了Peering连接确实存在。
    ```bash
    gcloud compute networks peerings list --project=jason-hsbc
    ```
    输出显示名为`servicenetworking-googleapis-com`的`ACTIVE`连接。

2.  我们尝试通过`gcloud`命令更新Peering连接，以期“刷新”路由。
    ```bash
    gcloud compute networks peerings update servicenetworking-googleapis-com --network=tf-vpc0 --project=jason-hsbc --export-subnet-routes-with-public-ip --no-import-subnet-routes-with-public-ip
    ```

**结果**: 问题依旧。这表明问题是一个更深层次的、无法通过简单刷新解决的路由配置问题。

## 3. 最终解决方案：切换到Cloud SQL Auth Proxy

在对直接IP连接进行了详尽的排查后，我们确定问题出在难以直接干预的GCP高级网络层面。此时，我们切换到了Google官方推荐的最佳实践：**使用Cloud SQL Auth Proxy**。

以下是我们成功实现连接的详细步骤：

### 3.1. 准备工作：服务账号与权限

我们决定使用节点绑定的服务账号`vm-common@jason-hsbc.iam.gserviceaccount.com`。首先，需要为它授予连接Cloud SQL的权限。

**命令**:
```bash
gcloud projects add-iam-policy-binding jason-hsbc --member="serviceAccount:vm-common@jason-hsbc.iam.gserviceaccount.com" --role="roles/cloudsql.client"
```
**输出**:
```
Updated IAM policy for project [jason-hsbc].
...
```
**结论**: `vm-common`服务账号现在拥有了`Cloud SQL Client`角色。

### 3.2. 创建测试Deployment (`proxy-test-deployment.yaml`)

我们创建了一个包含两个容器的Deployment：一个作为Auth Proxy边车，另一个作为psql客户端。我们让Proxy使用其从节点环境自动获取的服务账号凭证。

**YAML配置**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: proxy-test-deployment
spec:
  replicas: 1
  selector:
    matchLabels:
      app: proxy-test
  template:
    metadata:
      labels:
        app: proxy-test
    spec:
      containers:
      - name: cloud-sql-proxy
        image: gcr.io/cloud-sql-connectors/cloud-sql-proxy:2.8.0
        args:
          - "--private-ip"
          - "jason-hsbc:europe-west2:my-database-instance"
        securityContext:
          runAsNonRoot: true
      - name: psql-client
        image: postgres:13
        command: ["/bin/sh", "-c"]
        args:
        - |
          sleep 5;
          echo "--- Attempting to connect via proxy ---";
          export PGPASSWORD=[YOUR_PASSWORD];
          psql -h 127.0.0.1 -U nvd11 -d default_db -c "\\l";
          echo "--- Test complete, sleeping forever ---";
          sleep infinity;
```

### 3.3. 部署并验证

1.  **应用Deployment**:
    ```bash
    kubectl apply -f proxy-test-deployment.yaml
    ```
    **输出**: `deployment.apps/proxy-test-deployment created`

2.  **查看测试日志**: 我们等待Pod启动，然后查看`psql-client`容器的日志。
    ```bash
    POD_NAME=$(kubectl get pods -l app=proxy-test -o jsonpath='{.items[0].metadata.name}') && kubectl logs $POD_NAME -c psql-client
    ```

**最终测试日志 (成功)**:
```
--- Attempting to connect via proxy ---
                                                List of databases
     Name      |       Owner       | Encoding |  Collate   |   Ctype    |            Access privileges
---------------+-------------------+----------+------------+------------+-----------------------------------------
 cloudsqladmin | cloudsqladmin     | UTF8     | en_US.UTF8 | en_US.UTF8 |
 default_db    | cloudsqlsuperuser | UTF8     | en_US.UTF8 | en_US.UTF8 |
 postgres      | cloudsqlsuperuser | UTF8     | en_US.UTF8 | en_US.UTF8 |
 ...
(5 rows)

--- Test complete, sleeping forever ---
```

## 4. 结论

当遇到从GKE到Cloud SQL私有IP的连接问题，并且已确认VPC防火墙和网络策略无误时，应高度怀疑是VPC Peering的路由传播问题。

在这种情况下，与其花费大量时间进行深层网络调试，**切换到使用Cloud SQL Auth Proxy是最高效、最可靠、最安全的解决方案**。
