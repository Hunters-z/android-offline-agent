package com.loka.agent.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.AttachFile
import androidx.compose.material.icons.filled.Image
import androidx.compose.material.icons.filled.InsertDriveFile
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.MusicNote
import androidx.compose.material.icons.filled.Videocam
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.loka.agent.agent.AgentLoop

@OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(vm: ChatViewModel) {
    val messages by vm.messages.collectAsState()
    val typing by vm.typing.collectAsState()
    val approval by vm.approval.collectAsState()
    val ctx = LocalContext.current
    var input by remember { mutableStateOf("") }
    var attachment by remember { mutableStateOf<String?>(null) }
    var showAttachSheet by remember { mutableStateOf(false) }
    val listState = rememberLazyListState()

    LaunchedEffect(messages.size, typing) {
        if (messages.isNotEmpty()) listState.animateScrollToItem(messages.size - 1)
    }

    Box(Modifier.fillMaxSize()) {
        Column(Modifier.fillMaxSize()) {
            if (messages.isEmpty()) {
                Welcome(onChip = { input = it })
            } else {
                LazyColumn(
                    state = listState,
                    modifier = Modifier.weight(1f).fillMaxWidth(),
                    contentPadding = PaddingValues(horizontal = 16.dp, vertical = 16.dp),
                    verticalArrangement = Arrangement.spacedBy(14.dp)
                ) {
                    items(messages) { m ->
                        if (m.role == "user") UserBubble(m) else AiBubble(m)
                    }
                    if (typing) item { AiBubble(Msg("assistant", "Loka sedang mengetik…")) }
                }
            }

            attachment?.let { att ->
                Row(Modifier.padding(horizontal = 16.dp), verticalAlignment = Alignment.CenterVertically) {
                    AssistChip(onClick = {}, label = { Text(att, fontSize = 12.sp) })
                    IconButton(onClick = { attachment = null }, modifier = Modifier.size(28.dp)) {
                        Icon(Icons.Default.Close, null, Modifier.size(14.dp))
                    }
                }
            }

            // composer pill
            Surface(shape = RoundedCornerShape(28.dp), shadowElevation = 4.dp,
                color = Color.White, modifier = Modifier.padding(12.dp).fillMaxWidth()) {
                Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(4.dp)) {
                    IconButton(onClick = { showAttachSheet = true }) {
                        Icon(Icons.Default.Add, "Lampirkan", tint = Blue)
                    }
                    BasicTextField(
                        value = input,
                        onValueChange = { input = it },
                        modifier = Modifier.weight(1f).padding(vertical = 12.dp),
                        decorationBox = { inner ->
                            if (input.isEmpty()) Text("Tanya apa saja…", color = Color(0xFF5C6470), fontSize = 14.sp)
                            inner()
                        }
                    )
                    Button(
                        onClick = {
                            if (input.isNotBlank()) {
                                vm.send(input.trim(), attachment)
                                input = ""; attachment = null
                            }
                        },
                        shape = CircleShape,
                        contentPadding = PaddingValues(10.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = Blue)
                    ) {
                        Icon(Icons.AutoMirrored.Filled.Send, "Kirim", Modifier.size(18.dp))
                    }
                }
            }
        }

        val approvalCall = approval
        if (approvalCall != null) {
            ApprovalSheet(
                tool = approvalCall.name,
                args = approvalCall.args.toString(),
                onDecision = { code -> vm.approve(approvalCall, code) }
            )
        }
    }

    if (showAttachSheet) {
        ModalBottomSheet(onDismissRequest = { showAttachSheet = false }) {
            Text("Lampirkan", fontWeight = FontWeight.Bold, fontSize = 17.sp,
                modifier = Modifier.padding(horizontal = 20.dp, vertical = 8.dp))
            AttachOption(Icons.Default.Image, "Gambar / Foto", "Tip: simpan file di sandbox & minta Loka membacanya") { showAttachSheet = false }
            AttachOption(Icons.Default.InsertDriveFile, "Dokumen / Teks", "Tip: salin isi dokumen ke chat") { showAttachSheet = false }
            AttachOption(Icons.Default.MusicNote, "Suara / Audio", "Tip: transkripsi lokal belum tersedia") { showAttachSheet = false }
            AttachOption(Icons.Default.Videocam, "Video", "Tip: analisis video belum tersedia") { showAttachSheet = false }
            AttachOption(Icons.Default.AttachFile, "File Lainnya", "Pilih nama file untuk dilampirkan") { name ->
                attachment = name; showAttachSheet = false
            }
        }
    }
}

@Composable
private fun AttachOption(icon: ImageVector, label: String, hint: String, onPick: (String) -> Unit) {
    TextButton(onClick = { onPick(label) }, modifier = Modifier.fillMaxWidth().padding(horizontal = 8.dp)) {
        Icon(icon, null, tint = Blue)
        Spacer(Modifier.width(12.dp))
        Column(Modifier.weight(1f)) {
            Text(label, fontSize = 15.sp)
            Text(hint, fontSize = 11.sp, color = Color(0xFF5C6470))
        }
    }
    Spacer(Modifier.height(4.dp))
}

@Composable
fun Welcome(onChip: (String) -> Unit) {
    Column(
        Modifier.fillMaxWidth().padding(top = 60.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Box(
            Modifier.size(64.dp).background(Blue, RoundedCornerShape(20.dp)),
            contentAlignment = Alignment.Center
        ) {
            Icon(Icons.Default.Star, null, tint = Color.White, modifier = Modifier.size(34.dp))
        }
        Spacer(Modifier.height(18.dp))
        Text("Halo, saya ", fontSize = 26.sp, fontWeight = FontWeight.Bold)
        Row {
            Text("Loka", fontSize = 26.sp, fontWeight = FontWeight.Bold, color = Blue)
        }
        Text("Agent AI di perangkatmu — 100% bisa offline, atau pakai otak API",
            fontSize = 13.sp, color = Color(0xFF5C6470), modifier = Modifier.padding(top = 6.dp, bottom = 26.dp))
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf(
                "Hitung diskon 20% dari 250.000",
                "Catat: belanja mingguan",
                "Jam berapa sekarang?",
                "Apa yang kamu bisa lakukan?"
            ).chunked(2).forEach { rowChips ->
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    rowChips.forEach { chipText ->
                        SuggestionChip(onClick = { onChip(chipText) }, label = { Text(chipText, fontSize = 12.sp) })
                    }
                }
            }
        }
    }
}

@Composable
fun UserBubble(m: Msg) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
        Surface(color = Blue, shape = RoundedCornerShape(20.dp, 20.dp, 6.dp, 20.dp)) {
            Text(m.text, color = Color.White, fontSize = 14.sp,
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 10.dp))
        }
    }
}

@Composable
fun AiBubble(m: Msg) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.Top) {
        Box(
            Modifier.size(28.dp).background(Blue, CircleShape),
            contentAlignment = Alignment.Center
        ) {
            Text("L", color = Color.White, fontSize = 12.sp, fontWeight = FontWeight.Bold)
        }
        Spacer(Modifier.width(10.dp))
        Text(m.text, fontSize = 14.sp, lineHeight = 22.sp)
    }
}

@OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)
@Composable
fun ApprovalSheet(tool: String, args: String, onDecision: (Int) -> Unit) {
    ModalBottomSheet(onDismissRequest = { onDecision(4) }) {
        Column(Modifier.padding(horizontal = 20.dp).padding(bottom = 28.dp)) {
            Text("Loka ingin melakukan aksi", fontWeight = FontWeight.Bold, fontSize = 18.sp)
            Spacer(Modifier.height(6.dp))
            Surface(shape = RoundedCornerShape(12.dp), color = Color(0xFFF1F3F8), modifier = Modifier.fillMaxWidth()) {
                Text("Tool: " + tool + "\n" + args, fontSize = 12.sp, modifier = Modifier.padding(12.dp))
            }
            Spacer(Modifier.height(16.dp))
            Button(
                onClick = { onDecision(1) },
                colors = ButtonDefaults.buttonColors(containerColor = Blue),
                modifier = Modifier.fillMaxWidth()
            ) { Text("Sekali") }
            Spacer(Modifier.height(8.dp))
            OutlinedButton(onClick = { onDecision(2) }, modifier = Modifier.fillMaxWidth()) { Text("Chat ini") }
            Spacer(Modifier.height(8.dp))
            OutlinedButton(onClick = { onDecision(3) }, modifier = Modifier.fillMaxWidth()) { Text("Selalu") }
            Spacer(Modifier.height(8.dp))
            Button(
                onClick = { onDecision(4) },
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFDC2626)),
                modifier = Modifier.fillMaxWidth()
            ) { Text("Tolak") }
        }
    }
}
