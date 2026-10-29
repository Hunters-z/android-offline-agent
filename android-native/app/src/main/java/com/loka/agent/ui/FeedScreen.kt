package com.loka.agent.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.loka.agent.Rutin

@OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)
@Composable
fun FeedScreen() {
    val items = Rutin.feed()
    Column(Modifier.fillMaxSize().padding(16.dp)) {
        Text("Feed", fontSize = 22.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(12.dp))
        if (items.isEmpty()) {
            Text("Belum ada hasil rutinitas. Tambahkan job di tab Rutinitas.",
                fontSize = 13.sp, color = androidx.compose.ui.graphics.Color(0xFF5C6470))
        }
        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            items(items) { it ->
                Card {
                    Column(Modifier.padding(12.dp)) {
                        Text(it.first, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
                        Text(it.second, fontSize = 12.sp, color = androidx.compose.ui.graphics.Color(0xFF5C6470))
                    }
                }
            }
        }
    }
}
