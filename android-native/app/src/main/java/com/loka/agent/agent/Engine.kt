package com.loka.agent.agent

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/** Pluggable brain: HTTP (Termux localhost:8088) / Cloud (OpenAI-compatible) / Stub. */
interface Engine {
    suspend fun chat(messages: List<JSONObject>): String
    val label: String
}

class HttpEngine(private val baseUrl: String) : Engine {
    override val label = "Lokal HTTP"
    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(300, TimeUnit.SECONDS).build()

    override suspend fun chat(messages: List<JSONObject>): String {
        val body = JSONObject().apply {
            put("messages", JSONArray(messages))
        }.toString().toRequestBody("application/json".toMediaType())
        val req = Request.Builder().url(baseUrl.trimEnd('/') + "/chat").post(body).build()
        client.newCall(req).execute().use { resp ->
            val text = resp.body?.string() ?: ""
            if (!resp.isSuccessful) throw RuntimeException("HTTP " + resp.code + ": " + text.take(200))
            return try {
                JSONObject(text).optString("reply").ifEmpty { text }
            } catch (e: Exception) { text }
        }
    }
}

class CloudEngine(
    private val baseUrl: String,
    private val apiKey: String,
    private val model: String
) : Engine {
    override val label = "Cloud API"
    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(300, TimeUnit.SECONDS).build()

    override suspend fun chat(messages: List<JSONObject>): String {
        val body = JSONObject().apply {
            put("model", model)
            put("messages", JSONArray(messages))
        }.toString().toRequestBody("application/json".toMediaType())
        val req = Request.Builder()
            .url(baseUrl.trimEnd('/') + "/chat/completions")
            .header("Authorization", "Bearer " + apiKey)
            .post(body).build()
        client.newCall(req).execute().use { resp ->
            val text = resp.body?.string() ?: ""
            if (!resp.isSuccessful) throw RuntimeException("HTTP " + resp.code + ": " + text.take(200))
            return JSONObject(text).getJSONArray("choices").getJSONObject(0)
                .getJSONObject("message").getString("content")
        }
    }
}

class StubEngine : Engine {
    override val label = "Stub (lokal)"
    override suspend fun chat(messages: List<JSONObject>): String {
        val last = messages.last().optString("content")
        return "Halo! Saya Loka dengan otak stub (belum ada model lokal). " +
            "Kamu bilang: \"" + last.take(200) + "\".\n\n" +
            "Untuk jawaban cerdas, hubungkan Otak API (cloud) atau server Termux (HTTP 127.0.0.1:8088). " +
            "Saya tetap bisa memakai tools lokal: hitung, catatan, file, waktu, baterai, dan memori."
    }
}
