package com.example.finsistant.data.network

import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.http.Query

// Basic Moshi data classes for Yahoo Finance Chart response
data class YahooChartResponse(val chart: ChartData?)
data class ChartData(val result: List<ResultData>?, val error: Any?)
data class ResultData(val timestamp: List<Long>?, val indicators: Indicators?)
data class Indicators(val quote: List<Quote>?)
data class Quote(
    val open: List<Double?>,
    val high: List<Double?>,
    val low: List<Double?>,
    val close: List<Double?>,
    val volume: List<Long?>
)

interface YahooFinanceApiService {
    @GET("v8/finance/chart/{symbol}")
    suspend fun getHistoricalData(
        @Path("symbol") symbol: String, // e.g., "RELIANCE.NS"
        @Query("interval") interval: String = "1d",
        @Query("range") range: String = "3mo"
    ): YahooChartResponse
}

object YahooFinanceClient {
    private const val BASE_URL = "https://query2.finance.yahoo.com/"

    private val retrofit = Retrofit.Builder()
        .baseUrl(BASE_URL)
        .addConverterFactory(MoshiConverterFactory.create())
        .build()

    val apiService: YahooFinanceApiService by lazy {
        retrofit.create(YahooFinanceApiService::class.java)
    }
}
