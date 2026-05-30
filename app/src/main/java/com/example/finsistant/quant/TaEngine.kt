package com.example.finsistant.quant

object TaEngine {

    /**
     * Calculates the Simple Moving Average (SMA)
     */
    fun calculateSMA(prices: List<Double>, period: Int): List<Double?> {
        val sma = mutableListOf<Double?>()
        for (i in prices.indices) {
            if (i < period - 1) {
                sma.add(null) // Not enough data
            } else {
                val sum = prices.subList(i - period + 1, i + 1).sum()
                sma.add(sum / period)
            }
        }
        return sma
    }

    /**
     * Calculates the Relative Strength Index (RSI)
     */
    fun calculateRSI(prices: List<Double>, period: Int = 14): List<Double?> {
        val rsi = mutableListOf<Double?>()
        if (prices.size < period + 1) {
            return List(prices.size) { null }
        }

        var avgGain = 0.0
        var avgLoss = 0.0

        // Calculate initial Average Gain and Loss
        for (i in 1..period) {
            val change = prices[i] - prices[i - 1]
            if (change > 0) {
                avgGain += change
            } else {
                avgLoss += Math.abs(change)
            }
        }
        avgGain /= period
        avgLoss /= period

        // Add nulls for the first 'period' elements
        for (i in 0 until period) {
            rsi.add(null)
        }

        // Calculate first RSI
        var rs = if (avgLoss == 0.0) 100.0 else avgGain / avgLoss
        rsi.add(100.0 - (100.0 / (1.0 + rs)))

        // Smoothed moving average for the rest
        for (i in period + 1 until prices.size) {
            val change = prices[i] - prices[i - 1]
            val gain = if (change > 0) change else 0.0
            val loss = if (change < 0) Math.abs(change) else 0.0

            avgGain = ((avgGain * (period - 1)) + gain) / period
            avgLoss = ((avgLoss * (period - 1)) + loss) / period

            rs = if (avgLoss == 0.0) 100.0 else avgGain / avgLoss
            rsi.add(100.0 - (100.0 / (1.0 + rs)))
        }

        return rsi
    }
}
