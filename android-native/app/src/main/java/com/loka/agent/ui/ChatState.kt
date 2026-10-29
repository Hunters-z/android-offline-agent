package com.loka.agent.ui

import android.content.Context
import com.loka.agent.Repos
import com.loka.agent.agent.AgentLoop
import com.loka.agent.agent.Approval
import com.loka.agent.agent.Settings
import com.loka.agent.agent.Tools
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

data class Msg(
    val role: String,          // user / assistant
    val text: String,
    val attachment: String? = null
)

class ChatStore(private val ctx: Context) {
    private val dir = File(Repos.sandbox, "chat").apply { mkdirs() }
    private val file = File(dir, "current.json")

    fun load(): MutableList<Msg> = try {
        val arr = JSONArray(file.readText())
        (0 until arr.length()).map {
            val o = arr.getJSONObject(it)
            Msg(o.getString("role"), o.getString("text"), o.optString("attachment", null))
        }.toMutableList()
    } catch (e: Exception) { mutableListOf() }

    fun save(msgs: List<Msg>) {
        val arr = JSONArray()
        msgs.forEach { arr.put(JSONObject().put("role", it.role).put("text", it.text)
            .put("attachment", it.attachment ?: JSONObject.NULL)) }
        file.writeText(arr.toString())
    }

    fun clear() { file.delete() }
}

class ChatViewModel(private val ctx: Context) {
    private val store = ChatStore(ctx)
    private val _messages = MutableStateFlow(store.load())
    val messages = _messages.asStateFlow()

    private val _busy = MutableStateFlow(false)
    val busy = _busy.asStateFlow()

    private val _typing = MutableStateFlow(false)
    val typing = _typing.asStateFlow()

    /** Approval sheet state: tool name + args, or null when hidden. */
    private val _approval = MutableStateFlow<AgentLoop.ToolCall?>(null)
    val approval = _approval.asStateFlow()

    private var history: MutableList<JSONObject> = mutableListOf()

    fun newChat() {
        store.clear()
        _messages.value = mutableListOf()
        history.clear()
    }

    fun send(text: String, attachment: String? = null) {
        if (_busy.value) return
        val list = _messages.value.toMutableList()
        list.add(Msg("user", text, attachment))
        _messages.value = list
        store.save(list)
        _busy.value = true

        CoroutineScope(Dispatchers.IO).launch { runLoop(text) }
    }

    private suspend fun runLoop(userText: String) {
        val settings = Settings.load(ctx)
        val engine = Settings.buildEngine(ctx, settings)
        history.clear()
        history.add(JSONObject().put("role", "system").put("content", AgentLoop.systemPrompt(ctx)))
        var history2 = mutableListOf<JSONObject>()
        // prior conversation (compact)
        _messages.value.dropLast(1).takeLast(8).forEach {
            history2.add(JSONObject().put("role", if (it.role == "user") "user" else "assistant")
                .put("content", it.text))
        }
        history2.add(JSONObject().put("role", "user").put("content", userText))

        val toolLog = mutableListOf<String>()
        var iteration = 0
        while (iteration < AgentLoop.MAX_ITER) {
            iteration++
            _typing.value = true
            val reply = try {
                engine.chat(history2)
            } catch (e: Exception) {
                finish(if (toolLog.isEmpty()) "Gagal terhubung otak: " + (e.message ?: "?") else toolLog.joinToString("\n") + "\n\nError otak: " + e.message)
                return
            }
            _typing.value = false
            val call = AgentLoop.parseToolCall(reply)
            if (call == null) {
                finish(reply); return
            }
            // approval gate
            val decision = Approval.decide(ctx, call.name)
            val allowed = decision == 3 || Approval.sessionAllows(call.name)
            if (!allowed) {
                _approval.value = call
                finish(if (toolLog.isEmpty()) "" else toolLog.joinToString("\n")) // wait for user
                return
            }
            val result = Tools.exec(ctx, call.name, call.args)
            toolLog.add(call.name + " -> " + result.take(200))
            history2.add(JSONObject().put("role", "assistant").put("content", reply))
            history2.add(JSONObject().put("role", "user").put("content", AgentLoop.TAG + " " + call.name + "\n" + result))
        }
        finish("Batas iterasi (" + AgentLoop.MAX_ITER + ") tercapai. Hasil terakhir:\n" + toolLog.takeLast(1).joinToString())
    }

    /** User tapped an approval button. */
    fun approve(call: AgentLoop.ToolCall, code: Int) {
        _approval.value = null
        Approval.remember(ctx, call.name, code)
        if (code == 4) { // Tolak
            appendAssistant("Oke, aksi " + call.name + " dibatalkan.")
            _busy.value = false
            return
        }
        _busy.value = true
        CoroutineScope(Dispatchers.IO).launch {
            val result = Tools.exec(ctx, call.name, call.args)
            appendAssistant("Hasil " + call.name + ":\n" + result.take(1500))
            _busy.value = false
        }
    }

    private fun appendAssistant(text: String) {
        val list = _messages.value.toMutableList()
        list.add(Msg("assistant", text))
        _messages.value = list
        store.save(list)
    }

    private fun finish(text: String) {
        _typing.value = false
        _busy.value = false
        if (text.isNotBlank()) appendAssistant(text)
    }
}
