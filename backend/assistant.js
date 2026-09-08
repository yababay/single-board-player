const { OpenAI } = require('openai');
const fs = require('fs');

const FOLDER_ID = process.env.FOLDER_ID;
const API_KEY = process.env.YANDEX_API_KEY;
const MODEL_NAME = process.env.MODEL_NAME || "qwen3.6-35b-a3b";
const BASE_URL = process.env.BASE_URL || "https" + "://rest-assistant.api.cloud.yandex.net/v1";

exports.handler = async function (event, context) {
    let body;
    try {
        body = typeof event.body === 'string' ? JSON.parse(event.body) : (event.body || {});
    } catch (e) {
        return _jsonResponse(400, { error: "Invalid JSON in request body" });
    }

    const query = (body.query || "").trim();
    // Фронтенд теперь передает текст выбранной инструкции прямо в body запроса!
    const customInstruction = (body.instruction || "").trim(); 

    if (!query) return _jsonResponse(400, { error: "Missing 'query' field" });
    if (!customInstruction) return _jsonResponse(400, { error: "Missing 'instruction' field" });

    const client = new OpenAI({
        apiKey: API_KEY,
        baseURL: BASE_URL,
        defaultHeaders: { "x-folder-id": FOLDER_ID }
    });

    let rawText = "";
    try {
        const response = await client.responses.create({
            model: `gpt://${FOLDER_ID}/${MODEL_NAME}`, 
            instructions: customInstruction, // Используем динамическую инструкцию
            input: query,
            temperature: 0.1,
        });
        rawText = response.output_text || "";
    } catch (e) {
        return _jsonResponse(500, { error: `AI Studio error: ${e.message}` });
    }

    // Если ответ содержит наш маркер плоского списка лингвистического агента
    if (rawText.includes('|=>')) {
        // Получаем динамический конфигуратор тегов от фронтенда
        const clientTags = body.tagsConfig || [];
        
        const clientPlaylistName = body.playlistName || "apply_tags.yaml";
        const downloadFileName = clientPlaylistName.replace(/\.yam?l$/i, '.sh');

        let bashScript = "#!/bin/bash\n\n# Скрипт сгенерирован автоматически динамическим бэкендом\n\n";
        
        const lines = rawText.split('\n');
        for (let line of lines) {
            if (!line.includes('|=>')) continue;
            
            const parts = line.split('|=>');
            const filePath = parts[0].trim();
            const cleanTitle = parts[1].trim();

            // Начинаем многострочную сборку команды eyeD3
            let cmd = `eyeD3 \\\n`;
            
            // Динамически обходим все теги, заполненные пользователем в интерфейсе
            for (let tag of clientTags) {
                if (!tag.value || !tag.value.trim()) continue; // Пропускаем пустые поля
                
                const val = tag.value.trim();
                
                if (tag.type === 'standard') {
                    // Обычные теги: --artist, --composer, --release-year
                    cmd += `  ${tag.flag} "${val}" \\\n`;
                } else if (tag.type === 'tpub') {
                    // Тег издателя: TPUB
                    cmd += `  --user-text-frame "TPUB:${val}" \\\n`;
                } else if (tag.type === 'txxx') {
                    // Любые кастомные пользовательские фреймы TXXX (Instrument, Style, Form и т.д.)
                    cmd += `  --user-text-frame "${tag.flag}:${val}" \\\n`;
                }
            }

            // Добавляем обязательное название трека и путь к файлу
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

    // В противном случае (если это был обычный диалог или подсчет) — возвращаем текст как есть
    return {
        statusCode: 200,
        headers: { "Content-Type": "text/plain; charset=utf-8" },
        body: rawText
    };
};

function _jsonResponse(statusCode, data) {
    return { statusCode, headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) };
}
