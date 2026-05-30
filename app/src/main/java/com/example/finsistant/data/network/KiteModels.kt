package com.example.finsistant.data.network

import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class KiteHoldingsResponse(
    val status: String,
    val data: List<Holding>?
)

@JsonClass(generateAdapter = true)
data class Holding(
    val tradingsymbol: String = "",
    val exchange: String = "",
    val instrument_token: Long = 0,
    val isin: String = "",
    val product: String = "",
    val price: Double = 0.0,
    val quantity: Int = 0,
    val used_quantity: Int = 0,
    val t1_quantity: Int = 0,
    val realised_quantity: Int = 0,
    val authorised_quantity: Int = 0,
    val authorised_date: String? = null,
    val opening_quantity: Int = 0,
    val collateral_quantity: Int = 0,
    val collateral_type: String? = null,
    val discrepant: Boolean = false,
    val average_price: Double = 0.0,
    val last_price: Double = 0.0,
    val close_price: Double = 0.0,
    val pnl: Double = 0.0,
    val day_change: Double = 0.0,
    val day_change_percentage: Double = 0.0
)
