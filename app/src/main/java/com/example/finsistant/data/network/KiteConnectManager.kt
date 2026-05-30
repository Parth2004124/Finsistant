package com.example.finsistant.data.network

import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import java.util.concurrent.TimeUnit

object KiteConnectManager {
    private const val BASE_URL = "https://api.kite.trade/"
    
    // Store credentials securely in a real app (e.g., EncryptedSharedPreferences or DataStore)
    // For now, these can be set in memory once the user logs in or provides them.
    var apiKey: String = ""
    var accessToken: String = ""

    private val authInterceptor = Interceptor { chain ->
        val originalRequest = chain.request()
        
        // Kite Connect API requires the authorization header in the format:
        // Authorization: token api_key:access_token
        val authHeader = "token $apiKey:$accessToken"
        
        val newRequest = originalRequest.newBuilder()
            .header("X-Kite-Version", "3")
            .header("Authorization", authHeader)
            .build()
            
        chain.proceed(newRequest)
    }

    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
    }

    private val okHttpClient = OkHttpClient.Builder()
        .addInterceptor(authInterceptor)
        .addInterceptor(loggingInterceptor) // For debugging API responses
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    private val moshi = Moshi.Builder()
        .add(KotlinJsonAdapterFactory())
        .build()

    private val retrofit = Retrofit.Builder()
        .baseUrl(BASE_URL)
        .client(okHttpClient)
        .addConverterFactory(MoshiConverterFactory.create(moshi))
        .build()

    val apiService: KiteApiService by lazy {
        retrofit.create(KiteApiService::class.java)
    }

    suspend fun exchangeToken(requestToken: String, apiSecret: String): Boolean {
        val checksum = ChecksumUtil.generateChecksum(apiKey, requestToken, apiSecret)
        try {
            val response = apiService.generateSession(apiKey, requestToken, checksum)
            // TODO: Parse the 'Any' response into a data class to extract 'access_token'
            // For now, we assume success if no exception is thrown, but you MUST
            // implement Moshi parsing here to actually extract and save it.
            // val token = (response as TokenResponse).data.accessToken
            // this.accessToken = token
            return true
        } catch (e: Exception) {
            e.printStackTrace()
            return false
        }
    }
}
