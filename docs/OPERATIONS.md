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

## Update the app

On the VPS, `IMAGE_TAG` in `.env` selects the image tag.

1. To run a branch build, set `IMAGE_TAG` to the branch tag, for example `IMAGE_TAG=feature-imap-loop`. To go back to the last build from `main`, set `IMAGE_TAG=latest`.
2. Pull the image and start the container:

```bash
docker compose pull && docker compose up -d
```

On Kubernetes, the chart value `image.tag` selects the image tag. The pull policy is `Always`, so each new pod pulls the image again.

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
2. Create the container again with the new settings:

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
