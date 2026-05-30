package com.example.finsistant.data.network

import com.google.ai.client.generativeai.GenerativeModel
import com.google.ai.client.generativeai.type.content

class LlmClient(private val apiKey: String) {

    private val generativeModel = GenerativeModel(
        modelName = "gemini-2.5-flash",
        apiKey = apiKey
    )

    suspend fun sendMessage(message: String, portfolioContext: String): String {
        return try {
            val prompt = """
                You are Finsistant, an advanced quantitative trading AI assistant.
                The user has the following live portfolio context:
                $portfolioContext
                
                Please respond to their message accurately. 
                Keep it concise and focus on technical analysis if asked.
                
                IMPORTANT: If the user explicitly asks you to buy or sell a stock, you must append a special command to the VERY END of your response.
                Format: TRADE_COMMAND: {"tradingsymbol": "SYMBOL", "quantity": INT, "transaction_type": "BUY" or "SELL"}
                Example: TRADE_COMMAND: {"tradingsymbol": "YESBANK", "quantity": 10, "transaction_type": "BUY"}
                Do not output this command unless the user explicitly confirms a trade.
                
                User: $message
            """.trimIndent()
            
            val response = generativeModel.generateContent(prompt)
            response.text ?: "No response from Gemini."
        } catch (e: Exception) {
            "Error connecting to AI: ${e.message}"
        }
    }
}
