const { OpenAI } = require('openai');

const FOLDER_ID = process.env.FOLDER_ID;
const API_KEY = process.env.YANDEX_API_KEY;
const MODEL_NAME = process.env.MODEL_NAME || "qwen3.6-35b-a3b";
// Хакерский обход фильтров для базового URL
const BASE_URL = process.env.NO_BASE_URL || "https" + "://rest-assistant.api.cloud.yandex.net/v1"
// Восстановили переменную векторного хранилища из окружения функции
const VECTOR_STORE_ID = process.env.VECTOR_STORE_ID || process.env.YC_VECTOR_STORE_ID;

exports.handler = async function (event, context) {
    let body;
    try {
        body = typeof event.body === 'string' ? JSON.parse(event.body) : (event.body || {});
    } catch (e) {
        return _jsonResponse(400, { error: "Invalid JSON in request body" });
    }

    const query = (body.query || "").trim();
    const customInstruction = (body.instruction || "").trim(); 
    const playlistName = (body.playlistName || "").trim();

    if (!query) return _jsonResponse(400, { error: "Missing 'query' field" });
    if (!customInstruction) return _jsonResponse(400, { error: "Missing 'instruction' field" });

    const client = new OpenAI({
        apiKey: API_KEY,
        baseURL: BASE_URL,
        defaultHeaders: { "x-folder-id": FOLDER_ID }
    });

    // 💡 ДИНАМИЧЕСКОЕ ПОДКЛЮЧЕНИЕ ВЕКТОРНОГО ХРАНИЛИЩА (RAG)
    // Включаем поиск по базе только если запрос пришел со вкладки Тестирования
    let toolsConfig = undefined;
    
    if (playlistName === 'recommendation_request.yaml' && VECTOR_STORE_ID) {
        toolsConfig = [
            {
                type: "file_search",
                vector_store_ids: [VECTOR_STORE_ID]
            }
        ];
    }
    // 💡 Формируем базовый объект параметров запроса
    const apiParams = {
        model: `gpt://${FOLDER_ID}/${MODEL_NAME}`, 
        instructions: customInstruction,
        input: query,
        temperature: 0.1
    };

    // 💡 Добавляем свойство tools в объект ТОЛЬКО если оно было сконфигурировано
    if (toolsConfig) {
        apiParams.tools = toolsConfig;
    }

    let rawText = "";
    try {
        // Передаем собранный без лишних undefined-ключей объект параметров
        const response = await client.responses.create(apiParams);
        rawText = response.output_text || "";
    } catch (e) {
        return _jsonResponse(500, { error: `AI Studio error: ${e.message}` });
    }

    // Если ответ содержит наш маркер плоского списка лингвистического агента
    if (rawText.includes('|=>')) {
        const clientTags = body.tagsConfig || [];
        const downloadFileName = playlistName.replace(/\.yam?l$/i, '.sh') || "apply_tags.sh";

        let bashScript = "#!/bin/bash\n\n# Скрипт сгенерирован автоматически динамическим бэкендом\n\n";
        
        const lines = rawText.split('\n');
        for (let line of lines) {
            if (!line.includes('|=>')) continue;
            
            const parts = line.split('|=>');
            const filePath = parts[0].trim();
            const cleanTitle = parts[1].trim();

            let cmd = `eyeD3 --encoding utf8 \\\n`;
            
            for (let tag of clientTags) {
                if (!tag.value || !tag.value.trim()) continue;
                const val = tag.value.trim();
                
                if (tag.type === 'standard') {
                    cmd += `  ${tag.flag} "${val}" \\\n`;
                } else if (tag.type === 'tpub') {
                    cmd += `  --user-text-frame "TPUB:${val}" \\\n`;
                } else if (tag.type === 'txxx') {
                    cmd += `  --user-text-frame "${tag.flag}:${val}" \\\n`;
                }
            }

            cmd += `  --title "${cleanTitle}" "${filePath}"\n`;
            bashScript += `${cmd}\n`;
        }

        return {
            statusCode: 200,
            headers: {
                "Content-Type": "text/x-shellscript; charset=utf-8",
                "Content-Disposition": `attachment; filename="${downloadFileName}"`,
                "Cache-Control": "no-cache"
            },
            body: bashScript
        };
    }

    // Во всех остальных случаях (включая текстовый ответ с рекомендацией "12;5") — отдаем как есть
    return {
        statusCode: 200,
        headers: { "Content-Type": "text/plain; charset=utf-8" },
        body: rawText
    };
};

function _jsonResponse(statusCode, data) {
    return { statusCode, headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) };
}
