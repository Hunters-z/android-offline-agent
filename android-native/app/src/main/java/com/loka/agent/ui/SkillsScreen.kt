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
import com.loka.agent.Skills
import kotlinx.coroutines.launch

@OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)
@Composable
fun SkillsScreen() {
    val scope = rememberCoroutineScope()
    var skills by remember { mutableStateOf(Skills.list()) }
    var url by remember { mutableStateOf("") }
    var status by remember { mutableStateOf("") }

    fun refresh() { skills = Skills.list() }

    Column(Modifier.fillMaxSize().padding(16.dp)) {
        Text("Skills", fontSize = 22.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(10.dp))
        OutlinedTextField(value = url, onValueChange = { url = it },
            label = { Text("URL GitHub (owner/repo/skill)") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
        Spacer(Modifier.height(8.dp))
        Button(
            onClick = {
                scope.launch {
                    status = "Menginstal…"
                    status = Skills.install(url.trim())
                    refresh()
                }
            },
            colors = ButtonDefaults.buttonColors(containerColor = Blue),
            modifier = Modifier.fillMaxWidth()
        ) { Text("Instal dari GitHub") }
        if (status.isNotBlank()) Text(status, fontSize = 12.sp, color = Color(0xFF5C6470),
            modifier = Modifier.padding(vertical = 6.dp))
        Spacer(Modifier.height(12.dp))
        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            items(skills) { s ->
                Card {
                    Row(Modifier.padding(12.dp).fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Column(Modifier.weight(1f)) {
                            Text(s.second, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
                            Text(s.third.take(100), fontSize = 12.sp, color = Color(0xFF5C6470), maxLines = 2)
                        }
                        TextButton(onClick = { Skills.remove(s.second); refresh() }) {
                            Text("Hapus", color = Color(0xFFDC2626))
                        }
                    }
                }
            }
        }
    }
}
