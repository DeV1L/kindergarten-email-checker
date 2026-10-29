# Operations guide

This guide describes daily tasks for the app on Docker Compose and on Kubernetes. On the VPS, run the commands in the directory with `compose.yaml` and `.env`. For Kubernetes, run the commands from the repository root.

## Follow the logs

The app writes one log line for each processed email: UID, sender, subject, urgency, deadline, Telegram message id and duration. An invalid model answer gives one warning line with a JSON object: the problem, the input of the tool call and the validation errors. The app also posts failures to the group, so the owner sees them where the summaries are.

A poll that finds no new email writes no log line at the `INFO` level. A poll that cannot connect to the mailbox writes one warning line. The next poll tries again. To see each poll, set `LOG_LEVEL=DEBUG`. Read "Change a setting".

On the VPS:

```bash
docker compose logs -f
```

On Kubernetes:

```bash
kubectl -n kindergarten logs -f deployment/kindergarten-email-checker
```

## Health checks

At start, the app checks Telegram, Gmail and DeepSeek. Telegram must accept the bot token and find the group. Gmail must accept the app password. DeepSeek must accept the API key and report that the account can call the API. With a zero balance, it cannot. The app does not poll the mailbox before all three checks pass. The log line of a passed check shows the DeepSeek balance. After a failed check, the app writes one error line and stops. Docker or Kubernetes starts it again, with a longer delay after each failure. On Kubernetes, the pod status is then `CrashLoopBackOff`.

On Kubernetes, two probes call an HTTP server in the app, port 8080:

| Probe | Path | What it does |
|-------|------|--------------|
| Readiness | `/readyz` | The pod is ready after the start check passes. With wrong credentials, the pod stays not ready |
| Liveness | `/livez` | Kubernetes restarts the container when the app does not answer. The probe runs every `livenessPeriodSeconds` seconds, a chart value, default 60 |

Show the pod. The column `READY` shows `1/1` after the start check. The column `RESTARTS` counts the restarts:

```bash
kubectl -n kindergarten get pods
```

Show why a probe failed. The reason is in the events at the end of the output:

```bash
kubectl -n kindergarten describe pods -l app.kubernetes.io/name=kindergarten-email-checker
```

Show why the start check failed:

```bash
kubectl -n kindergarten logs deployment/kindergarten-email-checker | grep "start check"
```

## Update the app

On the VPS, `IMAGE_TAG` in `.env` selects the image tag.

1. To run a branch build, set `IMAGE_TAG` to the branch tag, for example `IMAGE_TAG=feature-imap-loop`. To go back to the last build from `main`, set `IMAGE_TAG=latest`.
2. Pull the image and start the container:

```bash
docker compose pull && docker compose up -d
```

On Kubernetes, deploy with the workflow **Deploy**:

1. In the repository on GitHub, click the **Actions** tab.
2. Click the workflow **Deploy**.
3. Click **Run workflow**. In **Use workflow from**, select the branch. The workflow uses the chart from this branch.
4. Keep the tag `latest`, or enter another image tag. The tags are in "CI pipeline".
5. Click **Run workflow**.

The workflow replaces the pod, and the new pod pulls the image again. The old pod finishes the email it is working on, then exits. The workflow waits until the new pod is ready. If the pod is not ready in 5 minutes, the workflow fails, for example with wrong credentials. The old pod keeps working. Read "Health checks". The one-time setup is in "Deploy from GitHub" in [SETUP.md](SETUP.md).

To go back to an older build, run **Deploy** with the tag `sha-<commit>` of that build.

Without GitHub, use Helm or kubectl. The chart value `image.tag` selects the image tag. The pull policy is `Always`, and each `helm upgrade` replaces the pod, so the new pod pulls the image again. The next run of **Deploy** replaces the values that you set with `--set`.

- To run the last build of the current tag, restart the pod:

```bash
kubectl -n kindergarten rollout restart deployment/kindergarten-email-checker
```

- To run a branch build, set `image.tag`. To go back to the last build from `main`, use `image.tag=latest`:

```bash
helm upgrade --install kindergarten-email-checker charts/kindergarten-email-checker -n kindergarten --set image.tag=feature-imap-loop
```

## Change a setting

The app reads the settings only when it starts.

On the VPS:

1. Edit `.env`.
2. Create the container again with the new settings. The old container finishes the current email first:

```bash
docker compose up -d --force-recreate
```

On Kubernetes:

1. Edit `.env`.
2. Replace the secret:

```bash
kubectl -n kindergarten create secret generic kindergarten-email-checker --from-env-file=.env --dry-run=client -o yaml | kubectl apply -f -
```

3. Restart the pod:

```bash
kubectl -n kindergarten rollout restart deployment/kindergarten-email-checker
```

## Remove the app from Kubernetes

```bash
helm uninstall kindergarten-email-checker -n kindergarten
```

## CI pipeline

The workflow is in [.github/workflows/ci.yml](../.github/workflows/ci.yml). It has two jobs.

| Job | What it does | When it runs |
|-----|--------------|--------------|
| `test` | Ruff lint, Ruff format check, pytest | Manual run from any branch. Pull request opened or updated |
| `build-and-push` | Builds the Docker image and pushes it to `ghcr.io/dev1l/kindergarten-email-checker` | Manual run from any branch, after `test` passes. Merge to `main` |

On a merge to `main`, the tests do not run again. They ran on the pull request.

Image tags:

| Tag | Image |
|-----|-------|
| `latest` | The last build from `main` |
| Branch name, with `/` replaced by `-` | The last build from that branch. For example, the branch `feature/imap-loop` gives the tag `feature-imap-loop` |
| `sha-<commit>` | One tag for each build |

Start a manual run:

1. In the repository on GitHub, click the **Actions** tab.
2. Click the workflow **CI**.
3. Click **Run workflow**. Select the branch.

The workflow **Deploy** is in [.github/workflows/deploy.yml](../.github/workflows/deploy.yml). It runs only when you start it. Read "Update the app".
