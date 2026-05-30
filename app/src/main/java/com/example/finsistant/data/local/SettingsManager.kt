package com.example.finsistant.data.local

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

class SettingsManager(context: Context) {

    private val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()

    private val sharedPreferences: SharedPreferences = EncryptedSharedPreferences.create(
        context,
        "finsistant_secure_prefs",
        masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )

    fun saveString(key: String, value: String) {
        sharedPreferences.edit().putString(key, value).apply()
    }

    fun getString(key: String, defaultValue: String = ""): String {
        return sharedPreferences.getString(key, defaultValue) ?: defaultValue
    }
    
    fun clearCredentials() {
        sharedPreferences.edit().clear().apply()
    }
    
    // Quick accessors
    var apiKey: String
        get() = getString("api_key", "dn5f72ctu7ey0jtr")
        set(value) = saveString("api_key", value)

    var apiSecret: String
        get() = getString("api_secret", "m7vdidtyys7gyc5h2e3ztojh21tm5akv")
        set(value) = saveString("api_secret", value)
        
    var userId: String
        get() = getString("user_id")
        set(value) = saveString("user_id", value)
        
    var password: String
        get() = getString("password")
        set(value) = saveString("password", value)
        
    var totpSecret: String
        get() = getString("totp_secret", "ZFFYLLALBPI3OPOLMATD73EORD7IBOEG")
        set(value) = saveString("totp_secret", value)
        
    var accessToken: String
        get() = getString("access_token")
        set(value) = saveString("access_token", value)

    var geminiApiKey: String
        get() = getString("gemini_api_key", "AIzaSyCVvcbz8VfxO7nSxeZkMttZ6YHpDti0NOQ")
        set(value) = saveString("gemini_api_key", value)
}
