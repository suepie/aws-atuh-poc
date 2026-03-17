# aws-atuh-poc

## ユーザ追加コマンド

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
