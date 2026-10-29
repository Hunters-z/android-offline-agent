package com.loka.agent.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.platform.LocalContext
import com.loka.agent.agent.Settings
import kotlinx.coroutines.launch

@OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)
@Composable
fun OtakScreen() {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    var s by remember { mutableStateOf(Settings.load(ctx)) }
    var status by remember { mutableStateOf("") }

    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp)) {
        Text("Otak API", fontSize = 22.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(10.dp))
        Text("Mode", fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(vertical = 8.dp)) {
            listOf("Stub", "HTTP", "Cloud").forEach { mode ->
                FilterChip(
                    selected = s.mode == mode,
                    onClick = { s = s.copy(mode = mode) },
                    label = { Text(mode) }
                )
            }
        }
        if (s.mode == "HTTP") {
            OutlinedTextField(value = s.baseUrl, onValueChange = { s = s.copy(baseUrl = it) },
                label = { Text("Base URL Termux (default http://127.0.0.1:8088)") },
                modifier = Modifier.fillMaxWidth(), singleLine = true)
            Text("App akan konek ke {base}/chat dengan {messages:[...]}.", fontSize = 11.sp, color = Color(0xFF5C6470))
        }
        if (s.mode == "Cloud") {
            Text("Provider", fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(vertical = 8.dp)) {
                listOf("OpenAI", "Gemini", "OpenRouter", "Custom").forEach { p ->
                    FilterChip(selected = s.provider == p, onClick = {
                        s = s.copy(provider = p, baseUrl = if (p == "Custom") s.baseUrl else Settings.preset(p))
                    }, label = { Text(p) })
                }
            }
            OutlinedTextField(value = s.baseUrl, onValueChange = { s = s.copy(baseUrl = it) },
                label = { Text("Base URL (…/v1)") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
            Spacer(Modifier.height(8.dp))
            OutlinedTextField(value = s.apiKey, onValueChange = { s = s.copy(apiKey = it) },
                label = { Text("API Key") }, visualTransformation = PasswordVisualTransformation(),
                modifier = Modifier.fillMaxWidth(), singleLine = true)
            Spacer(Modifier.height(8.dp))
            OutlinedTextField(value = s.model, onValueChange = { s = s.copy(model = it) },
                label = { Text("Model (mis. qwen2.5-7b-instruct)") },
                modifier = Modifier.fillMaxWidth(), singleLine = true)
        }
        Spacer(Modifier.height(14.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Button(
                onClick = { Settings.save(ctx, s); status = "Tersimpan." },
                colors = ButtonDefaults.buttonColors(containerColor = Blue)
            ) { Text("Simpan") }
            OutlinedButton(onClick = {
                scope.launch {
                    status = "Menguji…"
                    status = Settings.test(ctx, s)
                }
            }) { Text("Tes") }
        }
        if (status.isNotBlank()) Text(status, fontSize = 12.sp, color = Color(0xFF5C6470),
            modifier = Modifier.padding(top = 10.dp))
        Spacer(Modifier.height(10.dp))
        Text("Hybrid: pilih Cloud untuk jawaban cerdas online; mode Stub tetap jalan offline dengan tools lokal.",
            fontSize = 11.sp, color = Color(0xFF94A3B8))
    }
}
