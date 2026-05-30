package com.example.finsistant.data.network

import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.FormUrlEncoded
import retrofit2.http.Field
import retrofit2.Response

interface KiteApiService {
    
    @FormUrlEncoded
    @POST("session/token")
    suspend fun generateSession(
        @Field("api_key") apiKey: String,
        @Field("request_token") requestToken: String,
        @Field("checksum") checksum: String
    ): Any // Replace 'Any' with Moshi response class
    
    // Example: Fetch user profile
    @GET("user/profile")
    suspend fun getProfile(): Any // Replace 'Any' with actual Moshi data class later

    // Example: Fetch portfolio holdings
    @GET("portfolio/holdings")
    suspend fun getHoldings(): KiteHoldingsResponse

    // Example: Fetch orders
    @GET("orders")
    suspend fun getOrders(): Any // Replace 'Any' with actual Moshi data class later
    
    // You can add more Kite Connect endpoints here (e.g., placing an order, fetching margins)
}
