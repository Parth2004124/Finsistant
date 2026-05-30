package com.example.finsistant.data.network

import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Body
import java.util.concurrent.TimeUnit

// Connects directly to the live Ngrok tunnel
private const val BACKEND_BASE_URL = "https://semiexpositive-bruno-unrabbinical.ngrok-free.dev/"

data class OrderRequest(
    val tradingsymbol: String,
    val quantity: Int,
    val transaction_type: String
)

data class OrderResponse(
    val status: String,
    val order_id: String?
)

interface BackendApiService {
    @GET("api/holdings")
    suspend fun getHoldings(): KiteHoldingsResponse

    @POST("api/order")
    suspend fun placeOrder(@Body request: OrderRequest): OrderResponse
}

object BackendClient {
    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
    }

    private val okHttpClient = OkHttpClient.Builder()
        .addInterceptor(loggingInterceptor)
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    private val moshi = Moshi.Builder()
        .add(KotlinJsonAdapterFactory())
        .build()

    private val retrofit = Retrofit.Builder()
        .baseUrl(BACKEND_BASE_URL)
        .client(okHttpClient)
        .addConverterFactory(MoshiConverterFactory.create(moshi))
        .build()

    val apiService: BackendApiService by lazy {
        retrofit.create(BackendApiService::class.java)
    }
}
