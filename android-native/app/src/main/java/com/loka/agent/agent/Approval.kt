package com.loka.agent.agent

import android.content.Context
import com.loka.agent.Repos

/** Approval 3 tingkat: Sekali / Chat ini / Selalu / Tolak. Persisten. */
object Approval {
    private const val PREFS = "approval_policy"
    private const val KEY_PREFIX = "tool_"

    // decision codes: 0 = belum pernah, 1 = sekali, 2 = chat ini, 3 = selalu
    private val session = mutableMapOf<String, Int>() // chat-scoped

    fun decide(ctx: Context, tool: String): Int {
        if (tool in Tools.SAFE) return 3 // auto-approve SAFE_TOOLS
        val prefs = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        return prefs.getInt(KEY_PREFIX + tool, 0)
    }

    fun remember(ctx: Context, tool: String, code: Int) {
        if (code == 2) { session[tool] = 2; return }
        if (code == 3) {
            ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .edit().putInt(KEY_PREFIX + tool, 3).apply()
        }
    }

    fun sessionAllows(tool: String) = session[tool] == 2
}
