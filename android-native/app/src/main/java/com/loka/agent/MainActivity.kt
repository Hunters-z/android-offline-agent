package com.loka.agent

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Chat
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.loka.agent.ui.*

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val vm = ChatViewModel(applicationContext)
        setContent { LokaTheme { App(vm) } }
    }
}

private data class Tab(val label: String, val icon: ImageVector)

@Composable
fun App(vm: ChatViewModel) {
    var tab by remember { mutableStateOf(0) }
    val tabs = listOf(
        Tab("Chat", Icons.AutoMirrored.Filled.Chat),
        Tab("Feed", Icons.Default.List),
        Tab("Rutinitas", Icons.Default.Schedule),
        Tab("Model", Icons.Default.Psychology),
        Tab("Skills", Icons.Default.Build),
        Tab("Otak API", Icons.Default.Api)
    )
    val ctx = LocalContext.current

    Scaffold(
        containerColor = Color(0xFFF4F6FA),
        bottomBar = {
            NavigationBar(containerColor = Color.White) {
                tabs.forEachIndexed { i, t ->
                    NavigationBarItem(
                        selected = tab == i,
                        onClick = { tab = i },
                        icon = { Icon(t.icon, null) },
                        label = { Text(t.label, fontSize = 10.sp) }
                    )
                }
            }
        }
    ) { pad ->
        Box(Modifier.padding(pad).background(Color(0xFFF4F6FA))) {
            when (tab) {
                0 -> ChatScreen(vm)
                1 -> FeedScreen()
                2 -> RutinScreen()
                3 -> ModelScreen(ctx)
                4 -> SkillsScreen()
                5 -> OtakScreen()
            }
        }
    }
}
