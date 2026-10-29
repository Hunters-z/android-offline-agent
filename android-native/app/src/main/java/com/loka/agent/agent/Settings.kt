package com.loka.agent.agent

import android.content.Context
import org.json.JSONObject

/** Otak API settings: mode Lokal/Cloud/Hybrid, provider preset, base_url, api_key, model. */
object Settings {
    private const val PREFS = "otak_settings"

    data class Otak(
        val mode: String = "Stub",       // Stub / HTTP / Cloud
        val provider: String = "OpenAI", // OpenAI / Gemini / OpenRouter / Custom
        val baseUrl: String = "",
        val apiKey: String = "",
        val model: String = "",
        val activeModelKey: String = "tiny"
    )

    fun load(ctx: Context): Otak {
        val j = JSONObject(ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString("json", "{}") ?: "{}")
        return Otak(
            mode = j.optString("mode", "Stub"),
            provider = j.optString("provider", "OpenAI"),
            baseUrl = j.optString("baseUrl", ""),
            apiKey = j.optString("apiKey", ""),
            model = j.optString("model", ""),
            activeModelKey = j.optString("activeModelKey", "tiny")
        )
    }

    fun save(ctx: Context, o: Otak) {
        val j = JSONObject().apply {
            put("mode", o.mode); put("provider", o.provider); put("baseUrl", o.baseUrl)
            put("apiKey", o.apiKey); put("model", o.model); put("activeModelKey", o.activeModelKey)
        }
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString("json", j.toString()).apply()
    }

    fun preset(provider: String): String = when (provider) {
        "OpenAI" -> "https://api.openai.com/v1"
        "OpenRouter" -> "https://openrouter.ai/api/v1"
        "Gemini" -> "https://generativelanguage.googleapis.com/v1beta/openai"
        else -> ""
    }

    fun buildEngine(ctx: Context, o: Otak = load(ctx)): Engine = when (o.mode) {
        "HTTP" -> HttpEngine(o.baseUrl.ifEmpty { "http://127.0.0.1:8088" })
        "Cloud" -> if (o.baseUrl.isNotEmpty() && o.apiKey.isNotEmpty() && o.model.isNotEmpty())
            CloudEngine(o.baseUrl, o.apiKey, o.model) else StubEngine()
        else -> StubEngine()
    }

    /** Tes koneksi Otak API. */
    suspend fun test(ctx: Context, o: Otak): String = try {
        val eng = buildEngine(ctx, o)
        val reply = eng.chat(listOf(JSONObject().put("role", "user").put("content", "Balas hanya: OK")))
        "OK: " + reply.take(80)
    } catch (e: Exception) {
        "GAGAL: " + (e.message ?: e.javaClass.simpleName)
    }
}
