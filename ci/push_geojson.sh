#!/usr/bin/env bash
# Commit the reviewed GeoJSON and push it to main using the repo's write deploy key.
# Runs in the CircleCI publish-update job after the approval step.
set -euo pipefail

layer="AkoakoaWHIRestoration_latest.geojson"
candidate="build/${layer}"   # built by prepare-update, passed on through the workspace

branch="${CIRCLE_BRANCH:-$(git rev-parse --abbrev-ref HEAD)}"
if [[ "${branch}" != "main" ]]; then
  echo "Refusing to publish from branch '${branch}' (only main is published)" >&2
  exit 1
fi

# Pick the write deploy key that add_ssh_keys installed (not CircleCI's read-only checkout key).
if [[ -n "${DEPLOY_KEY_PATH:-}" ]]; then
  key="${DEPLOY_KEY_PATH}"
else
  mapfile -t keys < <(ls "${HOME}"/.ssh/id_rsa_* 2>/dev/null | grep -v '\.pub$' || true)
  if [[ ${#keys[@]} -ne 1 ]]; then
    echo "Expected exactly one additional SSH key in ~/.ssh (found ${#keys[@]})." >&2
    echo "Add the write deploy key under Project Settings > SSH Keys, or set DEPLOY_KEY_PATH." >&2
    exit 1
  fi
  key="${keys[0]}"
fi

# Trust GitHub's published SSH host keys (no trust-on-first-use).
mkdir -p "${HOME}/.ssh"
curl -fsSL https://api.github.com/meta \
  | python3 -c 'import json,sys; [print("github.com", k) for k in json.load(sys.stdin)["ssh_keys"]]' \
  >> "${HOME}/.ssh/known_hosts"

# ssh remote for this repo, whatever form the checkout used
origin="$(git remote get-url origin)"
slug="$(printf '%s' "${origin}" | sed -E 's#^(https://([^@]*@)?github\.com/|git@github\.com:|ssh://git@github\.com/)##; s#\.git$##')"
push_url="git@github.com:${slug}.git"
export GIT_SSH_COMMAND="ssh -i ${key} -o IdentitiesOnly=yes"

# Build on the latest main, but refuse if the published file changed since the preview.
git fetch --quiet "${push_url}" main
if ! git diff --quiet "${CIRCLE_SHA1:-HEAD}" FETCH_HEAD -- "${layer}"; then
  echo "${layer} changed on main since this update was prepared. Re-run the update." >&2
  exit 1
fi
git checkout --quiet -B main FETCH_HEAD

old_count="$(jq '.features | length' "${layer}")"
cp "${candidate}" "${layer}"   # cp keeps the tracked file's permissions
if git diff --quiet -- "${layer}"; then
  echo "${layer} unchanged; nothing to commit."
  exit 0
fi
new_count="$(jq '.features | length' "${layer}")"
datestr="$(jq -r '.name | split("_") | last' "${layer}")"   # name is AkoakoaWHIRestoration_YYYYMMDD

git config user.name "akk-activities-bot"
git config user.email "akk-activities-bot@users.noreply.github.com"
git add "${layer}"
git commit --quiet -m "${datestr}" \
  -m "${new_count} points (was ${old_count}). Reviewed and approved in CircleCI: ${CIRCLE_BUILD_URL:-local run}"
git push "${push_url}" HEAD:main
echo "Pushed $(git rev-parse --short HEAD) to ${slug}@main"
