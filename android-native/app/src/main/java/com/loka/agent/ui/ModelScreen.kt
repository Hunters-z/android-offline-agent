package com.loka.agent.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.loka.agent.agent.Settings

data class ModelInfo(val key: String, val name: String, val size: String, val ram: String, val desc: String)

val MODELS = listOf(
    ModelInfo("tiny", "Qwen 0.5B · Tiny", "491 MB", "RAM 3 GB+", "Cepat & ringan — HP apa saja"),
    ModelInfo("small", "Qwen 1.5B · Small", "986 MB", "RAM 4 GB+", "Seimbang — paling disarankan"),
    ModelInfo("medium", "Qwen 3B · Medium", "2 GB", "RAM 6 GB+", "Pintar — HP kelas menengah"),
    ModelInfo("smart", "Qwen 7B · Smart", "4.7 GB", "RAM 8 GB+", "Terpintar — HP flagship")
)

@OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)
@Composable
fun ModelScreen(ctx: android.content.Context) {
    var active by remember { mutableStateOf(Settings.load(ctx).activeModelKey) }
    Column(Modifier.fillMaxSize().padding(16.dp)) {
        Text("Model AI", fontSize = 22.sp, fontWeight = FontWeight.Bold)
        Text("Semua tersimpan lokal di perangkat. Model lebih besar = lebih pintar, butuh RAM lebih.",
            fontSize = 12.sp, color = Color(0xFF5C6470), modifier = Modifier.padding(top = 4.dp, bottom = 12.dp))
        LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            items(MODELS) { m ->
                val downloaded = com.loka.agent.Repos.sandbox.resolve("models/" + m.key + ".gguf").exists()
                Card(
                    colors = CardDefaults.cardColors(containerColor = if (m.key == active) Color(0xFFEAF0FE) else Color.White),
                    onClick = {
                        active = m.key
                        val s = Settings.load(ctx); Settings.save(ctx, s.copy(activeModelKey = m.key))
                    }
                ) {
                    Row(Modifier.padding(14.dp).fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text(m.name, fontWeight = FontWeight.SemiBold, fontSize = 15.sp)
                            Text(m.desc + " · " + m.size + " · " + m.ram, fontSize = 12.sp, color = Color(0xFF5C6470))
                        }
                        when {
                            m.key == active -> Surface(color = Blue, shape = RoundedCornerShape(99.dp)) {
                                Text("AKTIF", color = Color.White, fontSize = 10.sp, fontWeight = FontWeight.Bold,
                                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp))
                            }
                            downloaded -> Text("terunduh", color = Color(0xFF16A34A), fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                            else -> Text("belum unduh", color = Color(0xFF94A3B8), fontSize = 12.sp)
                        }
                    }
                }
            }
        }
        Spacer(Modifier.height(14.dp))
        Text("Model GGUF dapat ditempatkan di folder sandbox app (models/<key>.gguf). " +
            "Runtime llama.cpp JNI akan mengaktifkannya saat tersedia.",
            fontSize = 11.sp, color = Color(0xFF94A3B8))
    }
}
