package com.loka.agent.agent

import android.content.Context
import android.os.BatteryManager
import com.loka.agent.Repos
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/** Data class describing a local tool exposed to the agent loop. */
data class ToolDef(
    val name: String,
    val description: String,
    val params: String,
    val safe: Boolean
)

object Tools {
    val DEFS = listOf(
        ToolDef("calc", "Kalkulator matematika aman. Mendukung '% dari' Indonesia.", "{\"expression\": \"20/100*250000\"}", true),
        ToolDef("now", "Waktu & tanggal sekarang.", "{}", true),
        ToolDef("battery", "Status baterai perangkat.", "{}", true),
        ToolDef("note_save", "Simpan catatan.", "{\"title\": \"..\", \"body\": \"..\"}", false),
        ToolDef("note_list", "Daftar catatan.", "{}", true),
        ToolDef("note_read", "Baca catatan.", "{\"name\": \"file.md\"}", false),
        ToolDef("file_write", "Tulis file di sandbox.", "{\"name\": \"a.txt\", \"content\": \"..\"}", false),
        ToolDef("file_read", "Baca file di sandbox.", "{\"name\": \"a.txt\"}", false),
        ToolDef("file_list", "Daftar file sandbox.", "{\"name\": \"\"}", true),
        ToolDef("mem_save", "Simpan fakta permanen tentang user ke memory.", "{\"content\": \"..\"}", false),
        ToolDef("mem_list", "Daftar memori permanen.", "{}", true),
        ToolDef("mem_forget", "Hapus memori yang memuat teks.", "{\"content\": \"..\"}", false),
        ToolDef("shell", "Jalankan perintah terbatas di project (allowlist).", "{\"command\": \"ls\", \"project\": \"nama\"}", false)
    )

    val SAFE = DEFS.filter { it.safe }.map { it.name }.toSet()

    private val timeFmt = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US)

    fun exec(ctx: Context, name: String, args: Map<String, Any?>): String = try {
        when (name) {
            "calc" -> calc(args["expression"]?.toString() ?: "")
            "now" -> "{\"time\": \"" + timeFmt.format(Date()) + "\"}"
            "battery" -> battery(ctx)
            "note_save" -> {
                val title = args["title"]?.toString() ?: (args["judul"]?.toString() ?: "catatan")
                val body = args["body"]?.toString() ?: (args["isi"]?.toString() ?: "")
                val dir = File(Repos.sandbox, "notes").apply { mkdirs() }
                val f = File(dir, System.currentTimeMillis().toString() + "_" + title.replace(" ", "_").take(40) + ".md")
                f.writeText("# " + title + "\n\n" + body + "\n")
                "{\"saved\": \"" + f.name + "\"}"
            }
            "note_list" -> {
                val dir = File(Repos.sandbox, "notes")
                val list = if (dir.isDirectory) dir.listFiles()?.map { it.name }?.sortedDescending() else emptyList()
                "{\"notes\": " + jsonList(list ?: emptyList()) + "}"
            }
            "note_read" -> "{\"content\": " + jsonStr(File(Repos.sandbox, "notes/" + (args["name"] ?: "")).readText()) + "}"
            "file_write" -> {
                val f = safeFile(Repos.sandbox, args["name"]?.toString() ?: "")
                f.parentFile?.mkdirs()
                f.writeText(args["content"]?.toString() ?: "")
                "{\"written\": \"" + f.name + "\"}"
            }
            "file_read" -> "{\"content\": " + jsonStr(safeFile(Repos.sandbox, args["name"]?.toString() ?: "").readText()) + "}"
            "file_list" -> {
                val d = safeFile(Repos.sandbox, args["name"]?.toString() ?: "")
                "{\"files\": " + jsonList(if (d.isDirectory) d.listFiles()?.map { it.name }?.sorted() ?: emptyList() else emptyList()) + "}"
            }
            "mem_save" -> Repos.Memory.save(args["content"]?.toString() ?: "")
            "mem_list" -> Repos.Memory.list()
            "mem_forget" -> Repos.Memory.forget(args["content"]?.toString() ?: "")
            "shell" -> Shell.run(ctx, args["command"]?.toString() ?: "", args["project"]?.toString())
            else -> "{\"error\": \"tool tidak dikenal: " + name + "\"}"
        }
    } catch (e: Exception) {
        "{\"error\": " + jsonStr(e.message ?: e.javaClass.simpleName) + "}"
    }

    fun safeFile(root: File, rel: String): File {
        val f = File(root, rel.removePrefix("/"))
        val rp = f.canonicalPath
        if (!rp.startsWith(root.canonicalPath)) throw SecurityException("Akses di luar sandbox tidak diizinkan")
        return f
    }

    fun jsonStr(s: String): String {
        val sb = StringBuilder("\"")
        for (ch in s) when (ch) {
            '"' -> sb.append("\\\"")
            '\\' -> sb.append("\\\\")
            '\n' -> sb.append("\\n")
            '\r' -> sb.append("\\r")
            '\t' -> sb.append("\\t")
            else -> if (ch < ' ') sb.append("\\u%04x".format(ch.code)) else sb.append(ch)
        }
        sb.append("\"")
        return sb.toString()
    }

    fun jsonList(items: List<String>): String =
        items.joinToString(",", "[", "]") { jsonStr(it) }

    // ---------- calc ----------
    fun calc(expr: String): String {
        if (expr.isBlank()) return "{\"error\": \"butuh expression\"}"
        val e = preprocessIndoPercent(expr)
        return try {
            "{\"result\": " + CalcEval.eval(e) + "}"
        } catch (err: Exception) {
            "{\"error\": " + jsonStr(err.message ?: "gagal hitung") + "}"
        }
    }

    /** "20% dari 250000" -> "(20)/100*(250000)" with juta/ribu/miliar. */
    fun preprocessIndoPercent(s0: String): String {
        var s = s0
        val re = Regex("(\\d+(?:[.,]\\d+)?)\\s*(?:%|persen|percent)\\s*(?:dari|of)?\\s*([\\d.,\\s]*(?:juta|miliar|ribu)?)", RegexOption.IGNORE_CASE)
        val m = re.find(s) ?: return s
        var valStr = m.groupValues[2].trim().lowercase()
        var mult = 1.0
        if (valStr.contains("juta")) { mult = 1e6; valStr = valStr.replace("juta", "").trim() }
        else if (valStr.contains("miliar")) { mult = 1e9; valStr = valStr.replace("miliar", "").trim() }
        else if (valStr.contains("ribu")) { mult = 1e3; valStr = valStr.replace("ribu", "").trim() }
        val norm = normalizeNumber(valStr)
        return "(" + m.groupValues[1].replace(",", ".") + ")/100*(" + (norm * mult).toString() + ")"
    }

    fun normalizeNumber(t: String): Double {
        val s = t.trim()
        return if (s.contains(",") && s.contains(".")) s.replace(".", "").replace(",", ".").toDouble()
        else if (s.contains(",")) s.replace(",", ".").toDouble()
        else if (Regex("^\\d{1,3}(\\.\\d{3})+$").matches(s)) s.replace(".", "").toDouble()
        else s.toDouble()
    }

    private fun battery(ctx: Context): String {
        val bm = ctx.getSystemService(Context.BATTERY_SERVICE) as BatteryManager
        val pct = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
        val status = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_STATUS)
        val st = when (status) {
            BatteryManager.BATTERY_STATUS_CHARGING -> "charging"
            BatteryManager.BATTERY_STATUS_FULL -> "full"
            else -> "discharging"
        }
        return "{\"percent\": " + pct + ", \"status\": \"" + st + "\"}"
    }
}

/** Shell terbatas: allowlist binary, cwd = sandbox/projects/<nama>, blok path absolut & traversal. */
object Shell {
    private val ALLOW = setOf("git", "node", "npm", "npx", "python3", "ls", "cat", "head", "tail", "wc",
        "grep", "find", "du", "sed", "awk", "sort", "uniq", "cut", "tr", "diff", "touch", "mkdir", "cp", "mv")

    fun run(ctx: Context, command: String, projectName: String?): String {
        if (command.isBlank()) return "{\"error\": \"butuh command\"}"
        val parts = command.trim().split(Regex("\\s+"))
        val bin = parts[0]
        if (bin.contains("/") || bin !in ALLOW) return "{\"error\": \"perintah tidak diizinkan: " + bin + "\"}"
        if (parts.any { it.startsWith("/") || it.contains("..") }) return "{\"error\": \"path absolut & traversal diblokir\"}"

        val projectsRoot = File(Repos.sandbox, "projects").apply { mkdirs() }
        val dir = projectName?.let {
            val d = File(projectsRoot, it)
            if (d.canonicalPath.startsWith(projectsRoot.canonicalPath)) d else null
        } ?: File(projectsRoot, "default").apply { mkdirs() }
        dir.mkdirs()

        return try {
            val pb = ProcessBuilder(*parts.toTypedArray()).directory(dir)
            val env = pb.environment()
            env.put("HOME", Repos.sandbox.canonicalPath)
            env.put("PATH", System.getenv("PATH") ?: "/system/bin")
            val p = pb.start()
            val out = p.inputStream.bufferedReader().readText()
            val err = p.errorStream.bufferedReader().readText()
            val code = p.waitFor()
            val body = if (code == 0) out else out + err
            "{\"exit\": " + code + ", \"output\": " + Tools.jsonStr(body.take(4000)) + "}"
        } catch (e: Exception) {
            "{\"error\": " + Tools.jsonStr(e.message ?: "gagal eksekusi") + "}"
        }
    }
}

/** Evaluator aritmetika aman (tanpa eval bebas): + - * / % ^ ( ) dan angka. */
object CalcEval {
    private var pos = 0
    private var s = ""

    fun eval(expr: String): Double {
        s = expr.replace(" ", "").replace(",", "")
        pos = 0
        val r = parseExpr()
        if (pos < s.length) throw IllegalArgumentException("karakter tak terduga: " + s[pos])
        return r
    }

    private fun peek(): Char? = s.getOrNull(pos)

    private fun parseExpr(): Double {
        var v = parseTerm()
        while (true) {
            when (peek()) {
                '+' -> { pos++; v = v + parseTerm() }
                '-' -> { pos++; v = v - parseTerm() }
                else -> return v
            }
        }
    }

    private fun parseTerm(): Double {
        var v = parseFactor()
        while (true) {
            when (peek()) {
                '*' -> { pos++; v = v * parseFactor() }
                '/' -> { pos++; val d = parseFactor(); if (d == 0.0) throw ArithmeticException("bagi nol"); v = v / d }
                '%' -> { pos++; v = v % parseFactor() }
                else -> return v
            }
        }
    }

    private fun parseFactor(): Double {
        val base = parseUnary()
        if (peek() == '^') { pos++; return Math.pow(base, parseFactor()) }
        return base
    }

    private fun parseUnary(): Double {
        when (peek()) {
            '-' -> { pos++; return -parseUnary() }
            '+' -> { pos++; return parseUnary() }
        }
        if (peek() == '(') {
            pos++
            val v = parseExpr()
            if (peek() != ')') throw IllegalArgumentException("kurung tidak seimbang")
            pos++
            return v
        }
        val start = pos
        while (peek()?.isDigit() == true || peek() == '.') pos++
        if (start == pos) throw IllegalArgumentException("angka tidak valid di posisi " + pos)
        return s.substring(start, pos).toDouble()
    }
}
