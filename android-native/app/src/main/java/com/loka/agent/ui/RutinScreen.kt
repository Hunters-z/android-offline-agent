package com.loka.agent.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.loka.agent.Rutin

@OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)
@Composable
fun RutinScreen() {
    val jobs = Rutin.jobs()
    var name by remember { mutableStateOf("") }
    var prompt by remember { mutableStateOf("") }
    var minutes by remember { mutableStateOf("30") }

    Column(Modifier.fillMaxSize().padding(16.dp)) {
        Text("Rutinitas", fontSize = 22.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(10.dp))
        OutlinedTextField(value = name, onValueChange = { name = it }, label = { Text("Nama job") },
            modifier = Modifier.fillMaxWidth(), singleLine = true)
        Spacer(Modifier.height(8.dp))
        OutlinedTextField(value = prompt, onValueChange = { prompt = it }, label = { Text("Prompt / perintah") },
            modifier = Modifier.fillMaxWidth())
        Spacer(Modifier.height(8.dp))
        OutlinedTextField(value = minutes, onValueChange = { minutes = it.filter { c -> c.isDigit() } },
            label = { Text("Interval (menit)") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
        Spacer(Modifier.height(10.dp))
        Button(
            onClick = { if (name.isNotBlank() && prompt.isNotBlank())
                Rutin.addJob(name.trim(), prompt.trim(), minutes.toIntOrNull() ?: 30) },
            colors = ButtonDefaults.buttonColors(containerColor = androidx.compose.ui.graphics.Color(0xFF2563EB)),
            modifier = Modifier.fillMaxWidth()
        ) { Text("Tambah Rutinitas") }
        Spacer(Modifier.height(16.dp))
        Text("Job Aktif", fontWeight = FontWeight.SemiBold, fontSize = 15.sp)
        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            items(jobs) { j ->
                Card {
                    Row(Modifier.padding(12.dp).fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Column(Modifier.weight(1f)) {
                            Text(j.name, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
                            Text("setiap " + j.minutes + " menit — " + j.prompt, fontSize = 12.sp, color = Color(0xFF5C6470))
                        }
                        TextButton(onClick = { Rutin.removeJob(j.id) }) { Text("Hapus", color = Color(0xFFDC2626)) }
                    }
                }
            }
        }
    }
}
