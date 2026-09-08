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
        // Собираем полноценный Bash-скрипт программным путем
        const globalTags = body.globalTags || {};
        let bashScript = "#!/bin/bash\n\n# Скрипт сгенерирован автоматически бэкендом\n";
        
        const lines = rawText.split('\n');
        for (let line of lines) {
            if (!line.includes('|=>')) continue;
            const parts = line.split('|=>');
            const filePath = parts[0].trim();
            const cleanTitle = parts[1].trim();

            // Формируем строгую команду eyeD3
            let cmd = `eyeD3`;
            if (globalTags.artist) cmd += ` --artist "${globalTags.artist}"`;
            if (globalTags.composer) cmd += ` --composer "${globalTags.composer}"`;
            if (globalTags.album) cmd += ` --album "${globalTags.album}"`;
            if (globalTags.genre) cmd += ` --genre "${globalTags.genre}"`;
            cmd += ` --title "${cleanTitle}" "${filePath}"`;

            bashScript += `${cmd}\n`;
        }

        return {
            statusCode: 200,
            headers: {
                "Content-Type": "text/x-shellscript; charset=utf-8",
                "Content-Disposition": 'attachment; filename="apply_tags.sh"'
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
