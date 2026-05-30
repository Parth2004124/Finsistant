package com.example.finsistant.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.finsistant.data.network.BackendClient
import com.example.finsistant.data.network.Holding
import com.patrykandpatrick.vico.compose.chart.Chart
import com.patrykandpatrick.vico.compose.chart.column.columnChart
import com.patrykandpatrick.vico.core.entry.FloatEntry
import com.patrykandpatrick.vico.core.entry.entryModelOf
import kotlinx.coroutines.launch
import java.text.NumberFormat
import java.util.Locale

@Composable
fun DashboardScreen(modifier: Modifier = Modifier) {
    var holdings by remember { mutableStateOf<List<Holding>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()

    LaunchedEffect(Unit) {
        scope.launch {
            try {
                val response = BackendClient.apiService.getHoldings()
                if (response.data != null) {
                    holdings = response.data
                }
            } catch (e: Exception) {
                errorMessage = e.message
            } finally {
                isLoading = false
            }
        }
    }

    val totalValue = holdings.sumOf { it.quantity * it.last_price }
    val totalInvestment = holdings.sumOf { it.quantity * it.average_price }
    val totalPnL = totalValue - totalInvestment
    val currencyFormatter = NumberFormat.getCurrencyInstance(Locale("en", "IN"))

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .padding(horizontal = 16.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Spacer(modifier = Modifier.height(24.dp))
        
        Text(
            text = "Total Portfolio Value",
            style = MaterialTheme.typography.titleMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Text(
            text = currencyFormatter.format(totalValue),
            style = MaterialTheme.typography.displayMedium,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onBackground
        )
        
        val pnlColor = if (totalPnL >= 0) Color(0xFF4CAF50) else Color(0xFFE53935)
        val pnlSign = if (totalPnL >= 0) "+" else ""
        Text(
            text = "Total P&L: $pnlSign${currencyFormatter.format(totalPnL)}",
            style = MaterialTheme.typography.titleMedium,
            color = pnlColor,
            fontWeight = FontWeight.SemiBold
        )

        Spacer(modifier = Modifier.height(32.dp))

        if (isLoading) {
            CircularProgressIndicator(modifier = Modifier.padding(32.dp))
        } else if (errorMessage != null) {
            Text("Error: $errorMessage", color = MaterialTheme.colorScheme.error)
        } else if (holdings.isEmpty()) {
            Text("No active holdings found.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        } else {
            // Vico Chart
            Text("Capital Allocation", style = MaterialTheme.typography.titleSmall, modifier = Modifier.align(Alignment.Start))
            Spacer(modifier = Modifier.height(8.dp))
            
            val chartEntries = holdings.mapIndexed { index, holding ->
                FloatEntry(x = index.toFloat(), y = (holding.quantity * holding.last_price).toFloat())
            }
            if (chartEntries.isNotEmpty()) {
                val chartEntryModel = entryModelOf(chartEntries)
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(200.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                    shape = RoundedCornerShape(16.dp)
                ) {
                    Chart(
                        chart = columnChart(),
                        model = chartEntryModel,
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(16.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(24.dp))
            Text("Your Positions", style = MaterialTheme.typography.titleMedium, modifier = Modifier.align(Alignment.Start), fontWeight = FontWeight.Bold)
            Spacer(modifier = Modifier.height(8.dp))

            LazyColumn(
                verticalArrangement = Arrangement.spacedBy(12.dp),
                contentPadding = PaddingValues(bottom = 24.dp)
            ) {
                items(holdings) { holding ->
                    HoldingCard(holding, currencyFormatter)
                }
            }
        }
    }
}

@Composable
fun HoldingCard(holding: Holding, formatter: NumberFormat) {
    val isProfit = holding.pnl >= 0
    val pnlColor = if (isProfit) Color(0xFF4CAF50) else Color(0xFFE53935)
    val pnlSign = if (isProfit) "+" else ""

    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        shape = RoundedCornerShape(12.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(text = holding.tradingsymbol, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                Text(text = "${holding.quantity} shares • Avg: ${formatter.format(holding.average_price)}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(text = formatter.format(holding.last_price), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                Text(
                    text = "$pnlSign${formatter.format(holding.pnl)}",
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = pnlColor
                )
            }
        }
    }
}
