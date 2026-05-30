package com.example.finsistant.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

class TradingBotService : Service() {

    private val serviceJob = Job()
    private val serviceScope = CoroutineScope(Dispatchers.IO + serviceJob)

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val notification = createNotification()
        startForeground(1, notification)

        startTradingLoop()

        return START_STICKY
    }

    private fun startTradingLoop() {
        serviceScope.launch {
            while (isActive) {
                // TODO: 
                // 1. Check if access_token is valid (from SettingsManager).
                // 2. If invalid, broadcast an intent to MainActivity to trigger KiteWebViewAuthenticator.
                // 3. If valid, fetch market data via KiteConnectManager.
                // 4. Evaluate hardcoded trading strategy.
                // 5. Execute trades if conditions are met.
                
                println("TradingBotService: Scanning markets...")
                
                // Sleep for 5 seconds before next scan
                delay(5000L)
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        serviceJob.cancel()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                "bot_channel",
                "Trading Bot Service",
                NotificationManager.IMPORTANCE_LOW
            )
            val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            manager.createNotificationChannel(channel)
        }
    }

    private fun createNotification(): Notification {
        return NotificationCompat.Builder(this, "bot_channel")
            .setContentTitle("Finsistant Trading Bot")
            .setContentText("Actively scanning markets...")
            .setSmallIcon(android.R.drawable.ic_dialog_info) // Replace with your app icon later
            .build()
    }
}
