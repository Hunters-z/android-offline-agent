package com.loka.agent

import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.util.concurrent.TimeUnit

/** Skills: install dari GitHub raw SKILL.md, hapus, list. */
object Skills {
    private val dir: File get() = File(Repos.sandbox, "skills").apply { mkdirs() }
    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS).readTimeout(30, TimeUnit.SECONDS).build()

    fun list(): List<Triple<String, String, String>> =
        dir.listFiles { f -> f.isDirectory }
            ?.map { f -> Triple(f.name, f.name, f.resolve("SKILL.md").takeIf { it.exists() }?.readText() ?: "") }
            ?: emptyList()

    /** input: owner/repo[/path] — fetch raw SKILL.md. */
    fun install(url: String): String {
        if (url.isBlank()) return "URL kosong"
        val parts = url.removePrefix("https://").removePrefix("http://")
            .removePrefix("github.com/").removePrefix("raw.githubusercontent.com/").trim('/').split("/")
        if (parts.size < 2) return "Format: owner/repo[/path]"
        val owner = parts[0]; val repo = parts[1].removeSuffix(".git")
        val branch = if (parts.size > 2 && parts[2] != "tree") parts[2] else "main"
        val sub = if (parts.size > 3) parts.drop(3).joinToString("/") + "/" else ""
        val urls = listOf(
            "https://raw.githubusercontent.com/" + owner + "/" + repo + "/" + branch + "/" + sub + "SKILL.md",
            "https://raw.githubusercontent.com/" + owner + "/" + repo + "/master/" + sub + "SKILL.md"
        )
        for (u in urls) {
            try {
                val body = client.newCall(Request.Builder().url(u).build()).execute().use { r ->
                    if (r.isSuccessful) r.body?.string() else null
                }
                if (body != null) {
                    val name = sub.trim('/').ifEmpty { repo }
                    val d = File(dir, name).apply { mkdirs() }
                    d.resolve("SKILL.md").writeText(body)
                    d.resolve("origin.txt").writeText(u)
                    return "Terinstal: " + name + " (" + body.length + " chars)"
                }
            } catch (_: Exception) { }
        }
        return "Gagal fetch SKILL.md dari " + owner + "/" + repo
    }

    fun remove(name: String) {
        File(dir, name).deleteRecursively()
    }
}
