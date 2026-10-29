package com.loka.agent

import android.content.Context
import androidx.work.*
import kotlinx.coroutines.runBlocking
import com.loka.agent.agent.Settings
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

data class RutinJob(val id: String, val name: String, val minutes: Int, val prompt: String)

/** Rutinitas/cron via WorkManager periodic. Hasil ditulis ke feed. */
object Rutin {
    private const val PREFS = "rutin_jobs"
    private const val FEED = "rutin_feed"
    private const val KEY = "jobs_json"
    private const val FEED_KEY = "feed_json"

    private fun prefs(): android.content.SharedPreferences = Repos.appCtx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun jobs(): List<RutinJob> = try {
        val arr = JSONArray(prefs().getString(KEY, "[]") ?: "[]")
        (0 until arr.length()).map { i ->
            val o = arr.getJSONObject(i)
            RutinJob(o.getString("id"), o.getString("name"), o.getInt("minutes"), o.getString("prompt"))
        }
    } catch (e: Exception) { emptyList() }

    fun addJob(name: String, prompt: String, minutes: Int) {
        val id = "job_" + System.currentTimeMillis()
        val arr = JSONArray(prefs().getString(KEY, "[]") ?: "[]")
        arr.put(JSONObject().put("id", id).put("name", name).put("minutes", minutes).put("prompt", prompt))
        prefs().edit().putString(KEY, arr.toString()).apply()
        schedule(id, name, prompt, minutes)
    }

    fun removeJob(id: String) {
        val arr = JSONArray(prefs().getString(KEY, "[]") ?: "[]")
        val out = JSONArray()
        for (i in 0 until arr.length()) {
            if (arr.getJSONObject(i).getString("id") != id) out.put(arr.getJSONObject(i))
        }
        prefs().edit().putString(KEY, out.toString()).apply()
        WorkManager.getInstance(Repos.appCtx).cancelUniqueWork(id)
    }

    fun schedule(id: String, name: String, prompt: String, minutes: Int) {
        val req = PeriodicWorkRequestBuilder<RutinWorker>(minutes.toLong().coerceAtLeast(15), TimeUnit.MINUTES)
            .setInputData(workDataOf("id" to id, "name" to name, "prompt" to prompt))
            .build()
        WorkManager.getInstance(Repos.appCtx)
            .enqueueUniquePeriodicWork(id, ExistingPeriodicWorkPolicy.UPDATE, req)
    }

    fun feed(): List<Pair<String, String>> = try {
        val arr = JSONArray(Repos.appCtx.getSharedPreferences(FEED, Context.MODE_PRIVATE)
            .getString(FEED_KEY, "[]") ?: "[]")
        (0 until arr.length()).map { i ->
            val o = arr.getJSONObject(i)
            Pair(o.getString("title"), o.getString("body"))
        }
    } catch (e: Exception) { emptyList() }

    fun addFeed(title: String, body: String) {
        val prefs = Repos.appCtx.getSharedPreferences(FEED, Context.MODE_PRIVATE)
        val arr = JSONArray(prefs.getString(FEED_KEY, "[]") ?: "[]")
        val out = JSONArray()
        out.put(JSONObject().put("title", title).put("body", body))
        for (i in 0 until arr.length().coerceAtMost(49)) out.put(arr.getJSONObject(i))
        prefs.edit().putString(FEED_KEY, out.toString()).apply()
    }
}

class RutinWorker(ctx: Context, params: WorkerParameters) : Worker(ctx, params) {
    override fun doWork(): Result {
        val name = inputData.getString("name") ?: "job"
        val prompt = inputData.getString("prompt") ?: ""
        val engine = Settings.buildEngine(applicationContext)
        return try {
            val msgs = listOf(
                JSONObject().put("role", "system")
                    .put("content", "Kamu Loka, agent rutinitas. Jalankan perintah berikut ringkas."),
                JSONObject().put("role", "user").put("content", prompt)
            )
            val reply = runBlocking { engine.chat(msgs) }
            Rutin.addFeed(name, reply.take(500))
            Result.success()
        } catch (e: Exception) {
            Rutin.addFeed(name, "Gagal: " + (e.message ?: "?"))
            Result.success()
        }
    }
}
