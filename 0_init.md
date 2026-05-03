# Iteration Process

Repo: https://github.com/Andrew-Tolbert/gs-awm-demo-app  
App: https://gs-awm-demo-1444828305810485.aws.databricksapps.com

Edit `app/app.py`, commit, push, then deploy:

```bash
git add -A && git commit -m "..." && git push
databricks bundle deploy -p e2-demo && databricks bundle run gs_awm_demo -p e2-demo
```
