package com.example.finsistant.data.network

import java.security.MessageDigest

object ChecksumUtil {
    fun generateChecksum(apiKey: String, requestToken: String, apiSecret: String): String {
        val input = apiKey + requestToken + apiSecret
        val bytes = MessageDigest.getInstance("SHA-256").digest(input.toByteArray())
        return bytes.joinToString("") { "%02x".format(it) }
    }
}
