const fs = require('fs');
const path = require('path');

// ⚠️ Укажите точное имя вашего бакета
const BUCKET_NAME = 'playlists'; 
// Официальная точка монтирования в Yandex Cloud: /function/storage/<имя_бакета>
const MOUNT_PATH = path.join('/function/storage', BUCKET_NAME); 

exports.handler = async function (event, context) {
    const method = event.httpMethod || event.requestContext?.http?.method || '';
    if (method !== 'GET') {
        return { statusCode: 405, body: JSON.stringify({ error: "Method Not Allowed" }) };
    }

    // Извлекаем query-параметры (например, ?name=playlist.yaml)
    const queryParams = event.queryStringParameters || {};
    const fileName = queryParams.name;

    try {
        // Проверяем физическое наличие смонтированной папки
        if (!fs.existsSync(MOUNT_PATH)) {
            return {
                statusCode: 500,
                headers: { "Content-Type": "application/json; charset=utf-8" },
                body: JSON.stringify({ error: `Точка монтирования ${MOUNT_PATH} недоступна. Проверьте настройки интеграции функции с бакетом.` })
            };
        }

        // СЦЕНАРИЙ 1: Чтение содержимого конкретного файла
        if (fileName) {
            // Защита от выхода из директории (Path Traversal)
            const safeName = path.basename(fileName);
            const filePath = path.join(MOUNT_PATH, safeName);

            if (!fs.existsSync(filePath)) {
                return {
                    statusCode: 404,
                    headers: { "Content-Type": "application/json; charset=utf-8" },
                    body: JSON.stringify({ error: `Файл ${safeName} не найден в бакете.` })
                };
            }

            const fileContent = fs.readFileSync(filePath, 'utf-8');
            return {
                statusCode: 200,
                headers: { "Content-Type": "text/yaml; charset=utf-8" },
                body: fileContent
            };
        }

        // СЦЕНАРИЙ 2: Возвращаем список всех YAML файлов (если параметр ?name не передан)
        const files = fs.readdirSync(MOUNT_PATH);
        const yamlPlaylists = files.filter(file => {
            const ext = path.extname(file).toLowerCase();
            return ext === '.yaml' || ext === '.yml';
        });

        return {
            statusCode: 200,
            headers: { "Content-Type": "application/json; charset=utf-8" },
            body: JSON.stringify(yamlPlaylists)
        };

    } catch (e) {
        return {
            statusCode: 500,
            headers: { "Content-Type": "application/json; charset=utf-8" },
            body: JSON.stringify({ error: `Ошибка файловой системы: ${e.message}` })
        };
    }
};
