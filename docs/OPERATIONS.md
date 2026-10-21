# Operations guide

This guide describes daily tasks for the tool. On the VPS, run the commands in the directory with `compose.yaml` and `.env`. For Kubernetes, run the commands from the repository root.

## Follow the logs

On the VPS:

```bash
docker compose logs -f
```

On Kubernetes:

```bash
kubectl -n kindergarten logs -f deployment/kindergarten-email-checker
```

## Update the tool on the VPS

Pull the last build from `main` and start it:

```bash
docker compose pull && docker compose up -d
```

## Run a branch build

CI tags each branch build with the branch name, with `/` replaced by `-`. For example, the branch `feature/imap-loop` gives the tag `feature-imap-loop`.

On the VPS:

1. Set `IMAGE_TAG` in `.env` to the branch tag, for example `IMAGE_TAG=feature-imap-loop`.
2. Pull the image and start it:

```bash
docker compose pull && docker compose up -d
```

On Kubernetes, `IMAGE_TAG` in `.env` has no effect. Set the chart value `image.tag`:

```bash
helm upgrade --install kindergarten-email-checker charts/kindergarten-email-checker -n kindergarten --set image.tag=feature-imap-loop
```

## Change a setting on Kubernetes

The pod reads the secret only when it starts.

1. Edit `.env`.
2. Replace the secret:

```bash
kubectl -n kindergarten create secret generic kindergarten-email-checker --from-env-file=.env --dry-run=client -o yaml | kubectl apply -f -
```

3. Restart the pod:

```bash
kubectl -n kindergarten rollout restart deployment/kindergarten-email-checker
```

## Remove the tool from Kubernetes

```bash
helm uninstall kindergarten-email-checker -n kindergarten
```

## CI pipeline

The workflow is in [.github/workflows/ci.yml](../.github/workflows/ci.yml). It has two jobs.

| Job | What it does | When it runs |
|-----|--------------|--------------|
| `test` | Ruff lint, Ruff format check, pytest | Manual run from any branch. Pull request opened or updated |
| `build-and-push` | Builds the Docker image and pushes it to `ghcr.io/dev1l/kindergarten-email-checker` | Manual run from any branch, after `test` passes. Merge to `main` |

Image tags:

| Tag | Image |
|-----|-------|
| `latest` | The last build from `main` |
| Branch name, for example `feature-imap-loop` | The last build from that branch |
| `sha-<commit>` | One tag for each build |

Start a manual run:

1. In the repository on GitHub, click the **Actions** tab.
2. Click the workflow **CI**.
3. Click **Run workflow**. Select the branch.

## Local development

The tool needs Python 3.10 or newer. The container uses Python 3.13.

1. Create a virtual environment and activate it:

```bash
python3 -m venv .venv && . .venv/bin/activate
```

2. Install the package with the development tools:

```bash
pip install -e ".[dev]"
```

3. Run the linter:

```bash
ruff check .
```

4. Run the tests:

```bash
pytest
```

Build and run the image locally:

```bash
docker build -t kindergarten-email-checker .
```

```bash
docker run --rm --env-file .env kindergarten-email-checker
```

Run the tool locally without Docker. Put a filled `.env` in the project directory first:

```bash
python -m kindergarten_email_checker
```
