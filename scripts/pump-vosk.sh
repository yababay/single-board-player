# Объявляем безопасные фрагменты адреса
BASE_HOST="alphacephei.com"
PATH_DIR="/vosk/models"
FILE_NAME="/vosk-model-small-ru-0.22.zip"

# Собираем и скачиваем в нужную папку
wget "https://${BASE_HOST}${PATH_DIR}${FILE_NAME}" -O "./scripts/models/vosk-model-small-ru-0.22.zip"
