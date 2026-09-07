const { OpenAI } = require('openai');
const fs = require('fs');
const path = require('path');

// ─── Настройки из переменных окружения ───────────────────────────
const FOLDER_ID = process.env.FOLDER_ID;
const API_KEY = process.env.YANDEX_API_KEY;
const MODEL_NAME = process.env.MODEL_NAME || "yandexgpt/latest";
const VECTOR_STORE_ID = process.env.VECTOR_STORE_ID;

const BASE_URL = "https://yandex.net";

// Путь к файлу инструкции рядом с index.js
const PROMPT_PATH = path.join(__dirname, 'system-prompt.txt');

// Добавьте в начало index.js облачной функции
const https = require('https');

// Вынесем проверку токена в отдельный метод
exports.handler = async function (event, context) {
    // 1. Безопасное извлечение заголовка независимо от регистра букв (Authorization, authorization, AUTHORIZATION)
    const headers = event.headers || {};
    const authHeader = headers['Authorization'] || headers['authorization'] || headers['Authorization '] || '';
    
    const token = authHeader.replace(/^Bearer\s+/i, '').trim();

    if (!token) {
        return _jsonResponse(401, { error: "Unauthorized: Missing IAM token" });
    }

    // 2. Проверяем токен в Яндексе
    const isValid = await validateIamToken(token);
    if (!isValid) {
        return _jsonResponse(401, { error: "Unauthorized: Invalid or expired IAM token" });
    }
    
    // ── 1. Разбираем входящий запрос ──────────────────────────────
    let body;
    try {
        body = typeof event.body === 'string' ? JSON.parse(event.body) : (event.body || {});
    } catch (e) {
        return _jsonResponse(400, { error: "Invalid JSON in request body" });
    }

    const query = (body.query || "").trim();
    if (!query) {
        return _jsonResponse(400, { error: "Missing 'query' field" });
    }

    // ── 2. Читаем инструкцию из локального файла ──────────────────
    let systemPrompt;
    try {
        systemPrompt = fs.readFileSync(PROMPT_PATH, 'utf-8');
    } catch (e) {
        return _jsonResponse(500, { error: `Failed to read system-prompt.txt: ${e.message}` });
    }

    // ── 3. Вызываем агента через Responses API ───────────────────
    const client = new OpenAI({
        apiKey: API_KEY, // Использует ваш YANDEX_API_KEY
        baseURL: "https://rest-assistant.api.cloud.yandex.net/v1", // ВАЖНО: в JS свойство называется baseURL (с большой URL)
        defaultHeaders: {
            "x-folder-id": FOLDER_ID // Жестко привязываем запрос к вашему каталогу
        }
    });

    let rawText = "";
    try {
        const response = await client.responses.create({
            // Передает: gpt://<ваш_folder_id>/qwen3.6-35b-a3b
            model: `gpt://${FOLDER_ID}/${MODEL_NAME}`, 
            instructions: systemPrompt,
            /*tools: [
                {
                    type: "file_search",
                    vector_store_ids: [VECTOR_STORE_ID],
                }
            ],*/
            input: query,
            temperature: 0.2,
        });
        
        rawText = response.output_text || "";
    } catch (e) {
        return _jsonResponse(500, { error: `AI Studio request failed: ${e.message}` });
    }

    if (!/eyeD3/.test(rawText)) {
        return {
            statusCode: 200,
            headers: { "Content-Type": "text/plain; charset=utf-8" },
            body: rawText.trim() || "Пустой ответ"
        };
    }

    // ── 4. Извлекаем чистый Bash-код из ответа ИИ ───────────────────
    const bashScript = _extractBashScript(rawText);

    // ── 5. Формируем ответ в виде скачиваемого файла .sh ────────────
    return {
        statusCode: 200,
        headers: {
            "Content-Type": "text/x-shellscript; charset=utf-8",
            "Content-Disposition": 'attachment; filename="apply_tags.sh"',
            "Cache-Control": "no-cache"
        },
        body: bashScript
    };
};

/**
 * Очищает ответ от Markdown-тегов
 */
/**
 * Извлекает чистый Bash-код, если он есть, 
 * либо возвращает текст модели как есть, если это обычный диалог.
 */
function _extractBashScript(text) {
    if (!text) return "# Скрипт пуст или не был сгенерирован моделью";

    let cleaned = text.trim();

    // Проверяем, завернул ли ИИ код в маркеры ```bash ... ```
    const match = cleaned.match(/```(?:bash)?\s*([\s\S]*?)\s*```/);
    if (match) {
        cleaned = match[1].trim(); // Извлекаем только то, что внутри маркеров
        
        // Принудительно добавляем шебанг, если ИИ внутри блоков его забыл
        if (!cleaned.startsWith("#!/bin/bash")) {
            cleaned = "#!/bin/bash\n\n" + cleaned;
        }
        return cleaned;
    }

    // Если ИИ просто сгенерировал команды eyeD3 без оформления в блоки кода,
    // но в тексте явно есть вызовы утилиты:
    if (cleaned.includes("eyeD3")) {
        if (!cleaned.startsWith("#!/bin/bash")) {
            cleaned = "#!/bin/bash\n\n" + cleaned;
        }
        return cleaned;
    }

    // ГРАНИЧНЫЙ СЛУЧАЙ: Если в ответе нет ни eyeD3, ни блоков кода — значит, 
    // модель просто ответила текстом на ваш вопрос (например, "В файле 94 трека").
    // Возвращаем этот текст без изменений.
    return cleaned;
}

function _jsonResponse(statusCode, data) {
    return {
        statusCode: statusCode,
        headers: { "Content-Type": "application/json; charset=utf-8" },
        body: JSON.stringify(data)
    };
}
