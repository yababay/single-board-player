const { OpenAI } = require('openai');
const fs = require('fs');
const path = require('path');

// Настройки из переменных окружения Яндекс Облака
const FOLDER_ID = process.env.FOLDER_ID;
const API_KEY = process.env.YANDEX_API_KEY;
const MODEL_NAME = process.env.MODEL_NAME || "yandexgpt/latest";
const VECTOR_STORE_ID = process.env.VECTOR_STORE_ID;

// Путь к файлу инструкции (скрипт деплоя автоматически переименует system-instruction.md в system-prompt.md)
const PROMPT_PATH = path.join(__dirname, 'system-prompt.md');

/**
 * Точка входа Cloud Function
 */
exports.handler = async function (event, context) {
    // Авторизация проверена API-шлюзом на входе, сразу разбираем body
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

    // Читаем системную Markdown-инструкцию из локального файла
    let systemPrompt;
    try {
        systemPrompt = fs.readFileSync(PROMPT_PATH, 'utf-8');
    } catch (e) {
        return _jsonResponse(500, { error: `Failed to read system-prompt.md: ${e.message}` });
    }

    // Инициализируем клиента OpenAI API для Yandex AI Studio
    const client = new OpenAI({
        apiKey: API_KEY,
        baseURL: "https://yandex.net", // Без /v1 на конце, библиотека добавит сама
        defaultHeaders: {
            "x-folder-id": FOLDER_ID
        }
    });

    let rawText = "";
    try {
        const response = await client.responses.create({
            model: `gpt://${FOLDER_ID}/${MODEL_NAME}`, 
            instructions: systemPrompt,
            tools: [
                {
                    type: "file_search",
                    vector_store_ids: [VECTOR_STORE_ID],
                }
            ],
            input: query,
            temperature: 0.2,
        });
        
        rawText = response.output_text || "";
    } catch (e) {
        return _jsonResponse(500, { error: `AI Studio request failed: ${e.message}` });
    }

    // Если модель просто ответила текстом на вопрос (например, посчитала треки)
    if (!/eyeD3/.test(rawText)) {
        return {
            statusCode: 200,
            headers: { "Content-Type": "text/plain; charset=utf-8" },
            body: rawText 
        };
    }

    // Если в ответе есть команды eyeD3 — извлекаем чистый Bash-код
    const bashScript = _extractBashScript(rawText);

    // Формируем ответ в виде скачиваемого файла .sh
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
 * Извлекает чистый Bash-код, убирая markdown-теги
 */
function _extractBashScript(text) {
    if (!text) return "# Скрипт пуст или не был сгенерирован моделью";

    let cleaned = text.trim();

    // Проверяем, завернул ли ИИ код в маркеры ```bash ... ```
    const match = cleaned.match(/```(?:bash)?\s*([\s\S]*?)\s*```/);
    if (match) {
        cleaned = match[1].trim();
        if (!cleaned.startsWith("#!/bin/bash")) {
            cleaned = "#!/bin/bash\n\n" + cleaned;
        }
        return cleaned;
    }

    // Если ИИ выдал команды без обертки в блоки кода
    if (cleaned.includes("eyeD3")) {
        if (!cleaned.startsWith("#!/bin/bash")) {
            cleaned = "#!/bin/bash\n\n" + cleaned;
        }
        return cleaned;
    }

    return cleaned;
}

function _jsonResponse(statusCode, data) {
    return {
        statusCode: statusCode,
        headers: { "Content-Type": "application/json; charset=utf-8" },
        body: JSON.stringify(data)
    };
}
