#!/usr/bin/env bash
echo python download_latest_xlsx.py
if ! newxlsx=$(python download_latest_xlsx.py); then
  exit 1
fi
echo XLS: ${newxls}

echo python updated_json_from_xlsx.py "$newxlsx"
if ! newjson=$(python updated_json_from_xlsx.py "$newxlsx"); then
  exit 1
fi
echo JSON: ${newjson}

curr="AkoakoaWHIRestoration_latest.geojson"
echo Copying latest to $curr
if [ -e ${newjson} ]; then
  echo Found $newjson
  echo rm -fv $curr
  rm -fv $curr

  echo cp -v $newjson $curr
  cp -v $newjson $curr
fi
echo Done
