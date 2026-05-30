package com.example.finsistant.ui.auth

import android.annotation.SuppressLint
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.viewinterop.AndroidView
import dev.turingcomplete.kotlinonetimepassword.HmacAlgorithm
import dev.turingcomplete.kotlinonetimepassword.TimeBasedOneTimePasswordConfig
import dev.turingcomplete.kotlinonetimepassword.TimeBasedOneTimePasswordGenerator
import org.apache.commons.codec.binary.Base32
import java.util.concurrent.TimeUnit

@SuppressLint("SetJavaScriptEnabled")
@Composable
fun KiteWebViewAuthenticator(
    apiKey: String,
    userId: String,
    pinOrPassword: String,
    totpSecretBase32: String,
    onTokenExtracted: (String) -> Unit
) {
    // Generate TOTP using the secret
    val base32 = Base32()
    val secretBytes = base32.decode(totpSecretBase32)
    
    val config = TimeBasedOneTimePasswordConfig(
        codeDigits = 6,
        hmacAlgorithm = HmacAlgorithm.SHA1,
        timeStep = 30,
        timeStepUnit = TimeUnit.SECONDS
    )
    val totpGenerator = TimeBasedOneTimePasswordGenerator(secretBytes, config)

    val loginUrl = "https://kite.zerodha.com/connect/login?v=3&api_key=$apiKey"

    AndroidView(
        modifier = Modifier.fillMaxSize(), // Can be made invisible (size 0) if desired
        factory = { context ->
            WebView(context).apply {
                settings.javaScriptEnabled = true
                settings.domStorageEnabled = true
                
                webViewClient = object : WebViewClient() {
                    
                    override fun shouldOverrideUrlLoading(
                        view: WebView?,
                        request: WebResourceRequest?
                    ): Boolean {
                        val url = request?.url?.toString() ?: ""
                        
                        // Check if it's our redirect callback
                        if (url.startsWith("finsistant://callback") || url.startsWith("http://127.0.0.1") || url.startsWith("https://127.0.0.1")) {
                            val requestToken = request?.url?.getQueryParameter("request_token")
                            if (!requestToken.isNullOrEmpty()) {
                                onTokenExtracted(requestToken)
                            }
                            return true // We handled it, don't load the page
                        }
                        return super.shouldOverrideUrlLoading(view, request)
                    }

                    override fun onPageFinished(view: WebView?, url: String?) {
                        super.onPageFinished(view, url)
                        
                        if (url == null) return

                        // 1. Inject credentials if on the login page
                        if (url.contains("kite.zerodha.com/connect/login")) {
                            val js = """
                                javascript:(function() {
                                    var userField = document.querySelector('input[type=text]');
                                    var passField = document.querySelector('input[type=password]');
                                    var btn = document.querySelector('button[type=submit]');
                                    
                                    if (userField && passField && btn) {
                                        userField.value = '$userId';
                                        passField.value = '$pinOrPassword';
                                        
                                        // Trigger input events so React/Vue picks up the change
                                        userField.dispatchEvent(new Event('input', { bubbles: true }));
                                        passField.dispatchEvent(new Event('input', { bubbles: true }));
                                        
                                        setTimeout(function() { btn.click(); }, 500);
                                    }
                                })();
                            """.trimIndent()
                            view?.evaluateJavascript(js, null)
                        }
                        // 2. Inject TOTP if on the 2FA page
                        else if (url.contains("twofa") || url.contains("totp")) { // Adjust URL matching based on actual Kite 2FA URL
                            val currentTotp = totpGenerator.generate()
                            val js = """
                                javascript:(function() {
                                    var totpField = document.querySelector('input[type=text], input[type=number]');
                                    var btn = document.querySelector('button[type=submit]');
                                    
                                    if (totpField) {
                                        totpField.value = '$currentTotp';
                                        totpField.dispatchEvent(new Event('input', { bubbles: true }));
                                        
                                        if (btn) {
                                            setTimeout(function() { btn.click(); }, 500);
                                        }
                                    }
                                })();
                            """.trimIndent()
                            view?.evaluateJavascript(js, null)
                        }
                    }
                }
                
                loadUrl(loginUrl)
            }
        }
    )
}
