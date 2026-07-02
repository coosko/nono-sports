

cd ~/dev/nono-sport

NONO_SPORT_DATA_ROOT="/mnt/h/Mi unidad/01_ambitos/02_personal/40_deporte"

while true; do
  echo ""
  echo "--------------------------------"
  echo "[$(date --iso-8601=seconds)] Ejecutando nono_sports garmin fetch-activities..."
  #./.venv/bin/python -m nono_sports garmin fetch-activities \
  #--start 20 \
  #--limit 20 \
  #--max-activities 1
  
  #./.venv/bin/python -m nono_sports garmin decode-fit --force

  #./.venv/bin/python -m nono_sports garmin normalize

  #./.venv/bin/python -m nono_sports build-consolidated

  ./.venv/bin/python -m nono_sports garmin sync \
  --limit 60 \
  --max-activities 3 \
  --max-pages 100

  echo "[$(date --iso-8601=seconds)] A dormir 90 minutos..."
  echo "--------------------------------"

  sleep 5400  # 90 minutos
done


