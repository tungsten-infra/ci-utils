export REPO=${REPO:-centos-base}
export DL_PATH=${DL_PATH:-./mirrors/centos-base}
mkdir -p "$DL_PATH"
reposync -c yum.conf -r "$REPO" --download_path "$DL_PATH" --norepopath --download-metadata
createrepo -v "$DL_PATH"
