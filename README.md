# Akoakoa restoration activities

`AkoakoaWHIRestoration_latest.geojson` is the published layer of Akoakoa restoration
activities in West Hawaii. It's built from the project spreadsheet on Dropbox. The list is
cumulative, so each update should only add points.

Updates run on CircleCI, and nothing is published until you approve it.

## Updating the layer

1. In CircleCI, open **akk_activities** and click **Trigger Pipeline**. Pick branch `main`,
   add the parameter `run` = `update`, and trigger it. (Without the parameter, only the
   `checks` job runs.)
2. When `prepare-update` finishes, open it and go to **Artifacts** → `review/map.html`.
   New points are green, removed points red and unchanged points grey. Click a point, or an
   entry in the side list, to see its details. The same summary is in the job log, under
   *Review summary*.
3. If it looks right, click **Approve** on `hold-for-review`. `publish-update` then commits
   the file to `main` with the date (`YYYYMMDD`) as the message. If it doesn't look right,
   **Cancel** the workflow and nothing is published.

Removed points get a red warning because the list should only grow. An edited row shows up
the same way: its old version is listed as removed and its new version as new, at the same
spot.

## How it works

| Job | What it does |
|---|---|
| `prepare-update` | Downloads the spreadsheet from `DROPBOX_XLSX_URL` and runs `make_current_geojson.sh`, just like a local run. `preview_changes.py` compares the result with the published file and writes the map. |
| `hold-for-review` | Pauses the workflow until someone approves or cancels it. |
| `publish-update` | `ci/push_geojson.sh` commits exactly the reviewed file to `main` using a write deploy key. It refuses if the published file changed after `prepare-update`. |

Every push also runs `checks`, which confirms the scripts compile and the published GeoJSON
reads. It uses no secrets. Dates follow Pacific time (`TZ` in `.circleci/config.yml`).

## One-time setup

You need admin rights on the GitHub repository and in the CircleCI organization.

1. **Push this configuration** to `main`.
2. **Add the project:** in CircleCI, go to **Projects → Set Up Project →
   ASU-GDCS/akk_activities** and choose *use existing config* (`.circleci/config.yml`,
   branch `main`).
3. **Spreadsheet link:** go to **Project Settings → Environment Variables → Add Environment
   Variable**. Name it `DROPBOX_XLSX_URL` and paste the Dropbox share link, which must end in
   `dl=1`.
4. **Deploy key**, so CircleCI can push the approved file:
   ```bash
   ssh-keygen -t ed25519 -N "" -C "circleci akk_activities" -f ./akk_activities_deploy_key
   ```
   - In GitHub, go to **Settings → Deploy keys → Add deploy key**. Paste
     `akk_activities_deploy_key.pub` and tick **Allow write access**.
   - In CircleCI, go to **Project Settings → SSH Keys → Additional SSH Keys → Add SSH Key**.
     Set the hostname to `github.com` and paste the private `akk_activities_deploy_key`.
   - Then delete both local files: `rm akk_activities_deploy_key akk_activities_deploy_key.pub`.
5. **Forked PRs:** go to **Project Settings → Advanced** and turn **off** *Pass secrets to
   builds from forked pull requests* and *Build forked pull requests*. Build logs and
   artifacts of a public project are public. The Dropbox link is masked in logs, but the
   review map is visible to anyone with its link.
6. **Notifications** (optional): in **User Settings → Notifications**, turn on email for
   workflows awaiting approval.

## Running it locally

```bash
export DROPBOX_XLSX_URL='<Dropbox share link ending in dl=1>'
uv run bash make_current_geojson.sh
git show HEAD:AkoakoaWHIRestoration_latest.geojson > /tmp/published.geojson
uv run python preview_changes.py /tmp/published.geojson AkoakoaWHIRestoration_latest.geojson /tmp/map.html
```

The spreadsheet is saved under `Updates/`, which is ignored by git.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `Set DROPBOX_XLSX_URL to the Dropbox share link (dl=1)` | The environment variable is missing from the CircleCI project (setup step 3). |
| `Got HTML instead of a spreadsheet` | The link doesn't end in `dl=1`, or it has expired. |
| `Expected exactly one additional SSH key` | The deploy key is missing from CircleCI (setup step 4). |
| `marked as read only` or `Permission denied (publickey)` | The GitHub deploy key lacks **Allow write access**, or CircleCI holds a different private key. |
| `…changed on main since this update was prepared` | Someone committed the GeoJSON after `prepare-update`. Trigger the update again. |
| `Refusing to publish from branch` | The pipeline was triggered on a branch other than `main`. |
