const fs = require('fs');
const path = require('path');

// Имя вашего бакета данных в Yandex Object Storage
const BUCKET_NAME = 'playlists-dispatcher'; 
// Официальная точка монтирования папки хранения внутри файловой системы функций
const MOUNT_PATH = path.join('/function/storage', BUCKET_NAME); 

/**
 * Точка входа Cloud Function
 */
exports.handler = async function (event, context) {
    const method = event.httpMethod || event.requestContext?.http?.method || '';
    if (method !== 'GET') {
        return _jsonResponse(405, { error: "Method Not Allowed" });
    }

    // Извлекаем query-параметры (например, ?name=mozart.yaml)
    const queryParams = event.queryStringParameters || {};
    const fileName = queryParams.name;

    try {
        // Проверяем физическое наличие смонтированной директории в ОС функции
        if (!fs.existsSync(MOUNT_PATH)) {
            return _jsonResponse(500, { 
                error: `Директория хранения ${MOUNT_PATH} недоступна. Проверьте монтирование бакета в консоли.` 
            });
        }

        // РЕЖИМ 1: Чтение содержимого конкретного выбранного файла
        if (fileName) {
            // Защита от атаки обхода директории (Path Traversal)
            const safeName = path.basename(fileName);
            const filePath = path.join(MOUNT_PATH, safeName);

            if (!fs.existsSync(filePath)) {
                return _jsonResponse(404, { error: `Файл ${safeName} не найден в вашем бакете.` });
            }

            const fileContent = fs.readFileSync(filePath, 'utf-8');
            return {
                statusCode: 200,
                headers: { 
                    "Content-Type": "text/yaml; charset=utf-8",
                    "Cache-Control": "no-cache"
                },
                body: fileContent
            };
        }

        // РЕЖИМ 2: Возврат списка имен всех YAML-файлов (если параметр ?name пуст)
        const files = fs.readdirSync(MOUNT_PATH);
        const yamlPlaylists = files.filter(file => {
            const ext = path.extname(file).toLowerCase();
            return ext === '.yaml' || ext === '.yml';
        });

        return {
            statusCode: 200,
            headers: { 
                "Content-Type": "application/json; charset=utf-8",
                "Cache-Control": "no-cache"
            },
            body: JSON.stringify(yamlPlaylists)
        };

    } catch (e) {
        return _jsonResponse(500, { error: `Ошибка файловой системы бэкенда: ${e.message}` });
    }
};

function _jsonResponse(statusCode, data) {
    return {
        statusCode: statusCode,
        headers: { "Content-Type": "application/json; charset=utf-8" },
        body: JSON.stringify(data)
    };
}
