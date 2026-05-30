package com.example.finsistant.ui

import android.content.Intent
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import com.example.finsistant.data.local.SettingsManager
import com.example.finsistant.service.TradingBotService

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val settingsManager = remember { SettingsManager(context) }
    
    var apiKey by remember { mutableStateOf(settingsManager.apiKey) }
    var apiSecret by remember { mutableStateOf(settingsManager.apiSecret) }
    var userId by remember { mutableStateOf(settingsManager.userId) }
    var password by remember { mutableStateOf(settingsManager.password) }
    var totpSecret by remember { mutableStateOf(settingsManager.totpSecret) }
    var geminiApiKey by remember { mutableStateOf(settingsManager.geminiApiKey) }
    var accessToken by remember { mutableStateOf(settingsManager.accessToken) }
    var isBotRunning by remember { mutableStateOf(false) }

    Column(
        modifier = modifier
            .padding(16.dp)
            .fillMaxSize()
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        OutlinedTextField(
            value = apiKey,
            onValueChange = { apiKey = it },
            label = { Text("Kite API Key") },
            modifier = Modifier.fillMaxWidth()
        )
        
        OutlinedTextField(
            value = apiSecret,
            onValueChange = { apiSecret = it },
            label = { Text("Kite API Secret") },
            modifier = Modifier.fillMaxWidth()
        )

        OutlinedTextField(
            value = userId,
            onValueChange = { userId = it },
            label = { Text("Zerodha User ID") },
            modifier = Modifier.fillMaxWidth()
        )

        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            label = { Text("Zerodha Password") },
            modifier = Modifier.fillMaxWidth()
        )

        OutlinedTextField(
            value = totpSecret,
            onValueChange = { totpSecret = it },
            label = { Text("External TOTP Secret") },
            modifier = Modifier.fillMaxWidth()
        )
        
        OutlinedTextField(
            value = geminiApiKey,
            onValueChange = { geminiApiKey = it },
            label = { Text("Gemini API Key (Optional)") },
            modifier = Modifier.fillMaxWidth()
        )
        
        OutlinedTextField(
            value = accessToken,
            onValueChange = { accessToken = it },
            label = { Text("Kite Access Token (Temporary override)") },
            modifier = Modifier.fillMaxWidth()
        )
        
        Button(
            onClick = {
                settingsManager.apiKey = apiKey
                settingsManager.apiSecret = apiSecret
                settingsManager.userId = userId
                settingsManager.password = password
                settingsManager.totpSecret = totpSecret
                settingsManager.geminiApiKey = geminiApiKey
                settingsManager.accessToken = accessToken
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Save Credentials")
        }
        
        Spacer(modifier = Modifier.height(32.dp))
        
        Button(
            onClick = {
                val intent = Intent(context, TradingBotService::class.java)
                if (isBotRunning) {
                    context.stopService(intent)
                } else {
                    context.startForegroundService(intent)
                }
                isBotRunning = !isBotRunning
            },
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(
                containerColor = if (isBotRunning) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary
            )
        ) {
            Text(if (isBotRunning) "Stop Trading Bot" else "Start Trading Bot")
        }
    }
}
