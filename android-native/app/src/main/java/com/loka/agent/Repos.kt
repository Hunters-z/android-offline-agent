package com.loka.agent

import android.content.Context
import com.loka.agent.agent.Tools
import java.io.File

/** Persistent storage repos: sandbox dir, memory.md, approval policy, settings. */
object Repos {
    lateinit var appCtx: Context
        private set
    lateinit var sandbox: File
        private set

    fun init(ctx: Context) {
        appCtx = ctx.applicationContext
        sandbox = File(ctx.filesDir, "loka").apply { mkdirs() }
    }

    // ---------- memory.md ----------
    object Memory {
        private val file: File get() = File(Repos.sandbox, "memory.md")
        private fun lines(): MutableList<String> =
            if (file.exists()) file.readLines().filter { it.isNotBlank() }.toMutableList() else mutableListOf()

        fun save(content: String): String {
            if (content.isBlank()) return "{\"error\": \"butuh content\"}"
            val l = lines()
            if (content.trim() in l) return "{\"ok\": true, \"note\": \"sudah ada\"}"
            l.add(content.trim())
            while (l.size > 30) l.removeAt(0)
            file.writeText(l.joinToString("\n") + "\n")
            return "{\"ok\": true, \"total\": " + l.size + "}"
        }

        fun list(): String {
            val l = lines()
            return "{\"count\": " + l.size + ", \"items\": " + Tools.jsonList(l) + "}"
        }

        fun forget(content: String): String {
            if (content.isBlank()) return "{\"error\": \"butuh content\"}"
            val l = lines().filter { !it.contains(content, ignoreCase = true) }
            file.writeText(if (l.isEmpty()) "" else l.joinToString("\n") + "\n")
            return "{\"ok\": true, \"sisa\": " + l.size + "}"
        }
    }
}
