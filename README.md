# aws-atuh-poc




## AWS便利コマンド
前提としてawsにはCLIでログインしている

### RDS起動確認
```
aws rds describe-db-instances --db-instance-identifier auth-poc-kc-db --query 'DBInstances[0].DBInstanceStatus' --output text
```

### cognitoユーザ追加コマンド
```
aws cognito-idp admin-create-user \
  --user-pool-id ap-northeast-1_DaWOBYyg8 \
  --username suepie.sute.1+tmp3@gmail.com \
  --user-attributes Name=email,Value=suepie.sute.1+tmp3@gmail.com Name=email_verified,Value=true \
  --temporary-password 'TempPass1!' \
  --message-action SUPPRESS

aws cognito-idp admin-set-user-password \
  --user-pool-id ap-northeast-1_DaWOBYyg8 \
  --username suepie.sute.1+tmp3@gmail.com \
  --password 'Partner1!' \
  --permanent
```

### メモリ仕様率確認
5分おき3時間分
```
aws cloudwatch get-metric-statistics --namespace AWS/ECS --metric-name MemoryUtilization --dimensions Name=ClusterName,Value=auth-poc-kc-cluster Name=ServiceName,Value=auth-poc-kc-service --start-time $(date -u -v-2H +%Y-%m-%dT%H:%M:%S) --end-time $(date -u +%Y-%m-%dT%H:%M:%S) --period 300 --statistics Average Maximum --query 'sort_by(Datapoints, &Timestamp)[*].{Time:Timestamp,AvgPct:Average,MaxPct:Maximum}' --output table 2>&1
```

### CPU使用率確認コマンド
5分おき3時間分
```
aws cloudwatch get-metric-statistics --namespace AWS/ECS --metric-name CPUUtilization --dimensions Name=ClusterName,Value=auth-poc-kc-cluster Name=ServiceName,Value=auth-poc-kc-service --start-time $(date -u -v-2H +%Y-%m-%dT%H:%M:%S) --end-time $(date -u +%Y-%m-%dT%H:%M:%S) --period 300 --statistics Average Maximum --query 'sort_by(Datapoints, &Timestamp)[*].{Time:Timestamp,AvgPct:Average,MaxPct:Maximum}' --output table 2>&1
```

解説
```
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \                    # ECSのメトリクス
  --metric-name CPUUtilization \           # CPU使用率（MemoryUtilization も同様）
  --dimensions \
    Name=ClusterName,Value=auth-poc-kc-cluster \  # 対象クラスタ
    Name=ServiceName,Value=auth-poc-kc-service \  # 対象サービス
  --start-time ... --end-time ... \        # 取得期間 $(date -u +%Y-%m-%dT%H:%M:%S)←現在 $(date -u -v-2H +%Y-%m-%dT%H:%M:%S)←二時間前 
  --period 300 \                           # 5分間隔で集計
  --statistics Average Maximum \           # 平均と最大を取得
  --query 'sort_by(Datapoints, &Timestamp)[*]...' \  # ★ 時間でソート
  --output table
```