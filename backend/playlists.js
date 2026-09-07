const fs = require('fs');
const path = require('path');

// 💡 Исправлено: Напрямую указываем явную ручную точку монтирования в функции
const MOUNT_PATH = '/function/storage/playlists'; 

/**
 * Точка входа Cloud Function
 */
exports.handler = async function (event, context) {
    const method = event.httpMethod || event.requestContext?.http?.method || '';
    if (method !== 'GET') {
        return _jsonResponse(405, { error: "Method Not Allowed" });
    }

    const queryParams = event.queryStringParameters || {};
    const fileName = queryParams.name;

    try {
        // Проверяем физическое наличие смонтированной директории
        if (!fs.existsSync(MOUNT_PATH)) {
            return _jsonResponse(500, { 
                error: `Директория хранения ${MOUNT_PATH} недоступна. Проверьте параметры флага --storage-mounts в скрипте деплоя.` 
            });
        }

        // РЕЖИМ 1: Чтение содержимого конкретного выбранного файла
        if (fileName) {
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

        // РЕЖИМ 2: Возврат списка имен всех YAML-файлов
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
