package com.loka.agent.agent

import android.content.Context
import com.loka.agent.Repos
import org.json.JSONObject

/**
 * Agent loop: otak memutuskan -> device eksekusi tool -> hasil dikirim balik
 * sebagai [HASIL TOOL] -> maks 6 iterasi -> jawaban final.
 */
object AgentLoop {
    const val MAX_ITER = 6
    const val TAG = "[HASIL TOOL]"

    data class Turn(
        val finalText: String,
        val toolCalls: List<String>,       // untuk feed / log
        val pendingApproval: ToolCall? = null
    )

    data class ToolCall(val name: String, val args: Map<String, Any?>)

    /** Parse satu tool call dari jawaban otak. Format: ```tool\n{"name":..,"args":{..}}\n``` */
    fun parseToolCall(text: String): ToolCall? {
        val re = Regex("```tool\\s*\\n(.*?)\\n```", RegexOption.DOT_MATCHES_ALL)
        val m = re.find(text) ?: return null
        return try {
            val j = JSONObject(m.groupValues[1])
            val args = mutableMapOf<String, Any?>()
            val a = j.optJSONObject("args") ?: JSONObject()
            for (k in a.keys()) args[k] = a.get(k)
            ToolCall(j.optString("name"), args)
        } catch (e: Exception) { null }
    }

    fun systemPrompt(ctx: Context): String {
        val toolDocs = Tools.DEFS.joinToString("\n") {
            "- " + it.name + "(" + it.params + "): " + it.description
        }
        val mem = Repos.Memory.list()
        return "Kamu adalah Loka, agent AI offline di perangkat Android. Bahasa: Indonesia.\n" +
            "Kamu punya tools lokal. Untuk memakai tool, jawab HANYA dengan:\n" +
            "```tool\n{\"name\": \"calc\", \"args\": {\"expression\": \"1+2\"}}\n```\n" +
            "Setelah eksekusi, hasil akan dikirim sebagai " + TAG + ". Maksimal " + MAX_ITER + " iterasi. " +
            "Jika tidak butuh tool, jawab langsung sebagai teks biasa.\n\nTOOLS:\n" + toolDocs +
            "\n\nMEMORI USER:\n" + mem
    }
}
