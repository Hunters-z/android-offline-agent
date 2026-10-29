package com.loka.agent.ui

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val Blue = Color(0xFF2563EB)
val Bg = Color(0xFFF4F6FA)
val Dim = Color(0xFF5C6470)
val Ok = Color(0xFF16A34A)
val Danger = Color(0xFFDC2626)
val AccSoft = Color(0xFFEAF0FE)
val Line = Color(0xFFE3E7EF)

private val Scheme = lightColorScheme(
    primary = Blue,
    onPrimary = Color.White,
    background = Bg,
    onBackground = Color(0xFF10131A),
    surface = Color.White,
    onSurface = Color(0xFF10131A),
    surfaceVariant = Color(0xFFF1F3F8),
    onSurfaceVariant = Dim,
    error = Danger
)

@Composable
fun LokaTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = Scheme, content = content)
}
