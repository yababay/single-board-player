const fs = require('fs');
const path = require('path');

const STORAGE_ROOT = '/function/storage';
const PLAYLISTS_PATH = path.join(STORAGE_ROOT, 'playlists'); 
const INSTRUCTIONS_PATH = path.join(STORAGE_ROOT, 'instructions'); 

exports.handler = async function (event, context) {
    const method = event.httpMethod || event.requestContext?.http?.method || '';
    if (method !== 'GET') {
        return _jsonResponse(405, { error: "Method Not Allowed" });
    }

    const queryParams = event.queryStringParameters || {};
    const fileName = queryParams.name;
    const type = queryParams.type || 'playlist'; // 'playlist' или 'instruction'

    const targetDir = type === 'instruction' ? INSTRUCTIONS_PATH : PLAYLISTS_PATH;

    try {
        if (!fs.existsSync(targetDir)) {
            return _jsonResponse(500, { error: `Директория хранения ${targetDir} недоступна.` });
        }

        // РЕЖИМ 1: Чтение содержимого конкретного файла
        if (fileName) {
            const safeName = path.basename(fileName);
            const filePath = path.join(targetDir, safeName);

            if (!fs.existsSync(filePath)) {
                return _jsonResponse(404, { error: `Файл ${safeName} не найден.` });
            }

            const fileContent = fs.readFileSync(filePath, 'utf-8');
            return {
                statusCode: 200,
                headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-cache" },
                body: fileContent
            };
        }

        // РЕЖИМ 2: Возврат списка файлов
        const files = fs.readdirSync(targetDir);
        const filteredFiles = files.filter(file => {
            const ext = path.extname(file).toLowerCase();
            return ext === '.yaml' || ext === '.yml' || ext === '.txt' || ext === '.md';
        });

        return {
            statusCode: 200,
            headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-cache" },
            body: JSON.stringify(filteredFiles)
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
