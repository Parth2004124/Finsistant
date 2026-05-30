package com.example.finsistant.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Send
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.unit.dp
import com.example.finsistant.data.local.SettingsManager
import com.example.finsistant.data.network.BackendClient
import com.example.finsistant.data.network.LlmClient
import kotlinx.coroutines.launch

data class ChatMessage(val text: String, val isUser: Boolean)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatbotScreen(modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val settingsManager = remember { SettingsManager(context) }
    val scope = rememberCoroutineScope()
    
    // Initialize LLM Client only if we have a key
    val llmClient = remember(settingsManager.geminiApiKey) {
        if (settingsManager.geminiApiKey.isNotBlank()) {
            LlmClient(settingsManager.geminiApiKey)
        } else null
    }

    var messages by remember { mutableStateOf(listOf(ChatMessage("Hello! Ask me about your portfolio or give me trading instructions.", false))) }
    var inputText by remember { mutableStateOf("") }
    var isLoading by remember { mutableStateOf(false) }

    Column(modifier = modifier.fillMaxSize()) {
        LazyColumn(
            modifier = Modifier
                .weight(1f)
                .padding(16.dp),
            reverseLayout = true
        ) {
            items(messages.reversed()) { message ->
                MessageBubble(message)
                Spacer(modifier = Modifier.height(8.dp))
            }
        }
        
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            OutlinedTextField(
                value = inputText,
                onValueChange = { inputText = it },
                modifier = Modifier.weight(1f),
                placeholder = { Text("Type a command...") }
            )
            IconButton(
                onClick = {
                    if (inputText.isNotBlank() && !isLoading) {
                        val userText = inputText
                        messages = messages + ChatMessage(userText, true)
                        inputText = ""
                        
                        if (llmClient == null) {
                            messages = messages + ChatMessage("Please enter your Gemini API Key in the Settings tab first!", false)
                            return@IconButton
                        }

                        isLoading = true
                        scope.launch {
                            var portfolioContext = "The user currently has no active positions."
                            
                            // Fetch live holdings from Python Backend
                            try {
                                val response = BackendClient.apiService.getHoldings()
                                val holdingsList = response.data
                                if (!holdingsList.isNullOrEmpty()) {
                                    val formatted = holdingsList.joinToString("\n") { 
                                        "${it.tradingsymbol}: ${it.quantity} shares @ Rs${it.average_price} (Current: Rs${it.last_price}, PnL: Rs${it.pnl})"
                                    }
                                    portfolioContext = "The user has the following live holdings:\n$formatted"
                                }
                            } catch (e: Exception) {
                                portfolioContext = "Failed to fetch live portfolio data from backend: ${e.message}. Assume the user has an empty portfolio."
                            }

                            // Send to Gemini
                            val rawResponse = llmClient.sendMessage(userText, portfolioContext)
                            var displayResponse = rawResponse
                            
                            val tradeCommandRegex = "TRADE_COMMAND:\\s*(\\{.*\\})".toRegex(RegexOption.DOT_MATCHES_ALL)
                            val matchResult = tradeCommandRegex.find(rawResponse)
                            
                            if (matchResult != null) {
                                val jsonString = matchResult.groupValues[1]
                                displayResponse = rawResponse.replace(tradeCommandRegex, "").trim()
                                
                                try {
                                    val jsonObject = org.json.JSONObject(jsonString)
                                    val symbol = jsonObject.getString("tradingsymbol")
                                    val qty = jsonObject.getInt("quantity")
                                    val type = jsonObject.getString("transaction_type")
                                    
                                    val orderRequest = com.example.finsistant.data.network.OrderRequest(
                                        tradingsymbol = symbol,
                                        quantity = qty,
                                        transaction_type = type
                                    )
                                    
                                    val orderResult = BackendClient.apiService.placeOrder(orderRequest)
                                    if (orderResult.status == "success") {
                                        displayResponse += "\n\n[SYSTEM]: Automatically placed $type order for $qty shares of $symbol! (ID: ${orderResult.order_id})"
                                    } else {
                                        displayResponse += "\n\n[SYSTEM]: Failed to place $type order for $symbol."
                                    }
                                } catch (e: Exception) {
                                    displayResponse += "\n\n[SYSTEM]: Failed to parse or execute trade: ${e.message}"
                                }
                            }
                            
                            messages = messages + ChatMessage(displayResponse, false)
                            isLoading = false
                        }
                    }
                },
                enabled = !isLoading
            ) {
                if (isLoading) {
                    CircularProgressIndicator(modifier = Modifier.size(24.dp), strokeWidth = 2.dp)
                } else {
                    Icon(Icons.Default.Send, contentDescription = "Send")
                }
            }
        }
    }
}

@Composable
fun MessageBubble(message: ChatMessage) {
    val backgroundColor = if (message.isUser) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.secondaryContainer
    val alignment = if (message.isUser) Alignment.CenterEnd else Alignment.CenterStart
    
    Box(
        modifier = Modifier.fillMaxWidth(),
        contentAlignment = alignment
    ) {
        Surface(
            color = backgroundColor,
            shape = MaterialTheme.shapes.medium,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
        ) {
            Text(
                text = message.text,
                modifier = Modifier.padding(12.dp)
            )
        }
    }
}
