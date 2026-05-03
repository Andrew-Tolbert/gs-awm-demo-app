# Iteration Process

Repo: https://github.com/Andrew-Tolbert/gs-awm-demo-app  
App: https://gs-awm-demo-1444828305810485.aws.databricksapps.com

Edit `app.py`, commit, push, then deploy:

```bash
git add -A && git commit -m "..." && git push
databricks apps deploy -p e2-demo
```

`databricks bundle deploy` is only needed if you change `databricks.yml` (app config, resources, permissions).
